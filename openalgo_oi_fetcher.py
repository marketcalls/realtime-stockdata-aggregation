"""
OpenAlgo OI Fetcher - Dynamic Options Open Interest Data Fetcher
Fetches OI data from OpenAlgo for any F&O symbol/expiry combination
"""

import logging
import time
import threading
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to ensure we don't exceed API limits"""

    def __init__(self, requests_per_second: int = 10):
        """
        Initialize rate limiter

        Args:
            requests_per_second: Maximum requests per second (OpenAlgo default: 10)
        """
        self.min_interval = 1.0 / requests_per_second
        self.last_request = 0

    def wait_if_needed(self):
        """Wait if needed to maintain rate limit"""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()


class OpenAlgoOIFetcher:
    """Fetches Options OI data from OpenAlgo for any F&O symbol"""

    def __init__(self, openalgo_client, questdb_client, symbol_manager):
        """
        Initialize OI Fetcher

        Args:
            openalgo_client: OpenAlgo API client instance
            questdb_client: QuestDB client for data storage
            symbol_manager: Symbol manager for expiry and symbol info
        """
        self.openalgo = openalgo_client
        self.questdb = questdb_client
        self.symbol_manager = symbol_manager
        self.rate_limiter = RateLimiter(requests_per_second=8)  # Conservative limit
        self.running_fetchers = {}  # Track active fetchers
        self.ist_tz = pytz.timezone('Asia/Kolkata')

    def fetch_underlying_price(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """
        Get current spot/index price for ATM calculation

        Args:
            symbol: Underlying symbol (e.g., NIFTY, RELIANCE)
            exchange: Exchange (NSE for cash, NFO for futures)

        Returns:
            Current LTP or None
        """
        try:
            logger.info(f"Fetching underlying price for {symbol}")
            result = self.openalgo.quotes(symbol=symbol, exchange=exchange)

            if isinstance(result, dict):
                ltp = result.get('ltp') or result.get('data', {}).get('ltp')
                if ltp:
                    # Store in database
                    self.questdb.insert_underlying_quote(
                        symbol=symbol,
                        exchange=exchange,
                        ltp=float(ltp),
                        high=result.get('high'),
                        low=result.get('low'),
                        open_price=result.get('open'),
                        close=result.get('close'),
                        volume=result.get('volume')
                    )
                    return float(ltp)

            logger.warning(f"No LTP found for {symbol}: {result}")
            return None

        except Exception as e:
            logger.error(f"Error fetching underlying price for {symbol}: {e}")
            return None

    def get_option_symbol(self, underlying: str, expiry: str, strike: float,
                         option_type: str) -> str:
        """
        Construct option symbol using OpenAlgo convention

        Format: {SYMBOL}{DDMMMYY}{STRIKE}{CE/PE}
        Example: NIFTY28NOV2524000CE

        Args:
            underlying: Underlying symbol
            expiry: Expiry date in DD-MMM-YY format
            strike: Strike price
            option_type: CE or PE

        Returns:
            Formatted option symbol
        """
        try:
            # Parse expiry date
            expiry_date = datetime.strptime(expiry, "%d-%b-%y")

            # Format: DDMMMYY (e.g., 28NOV25)
            expiry_formatted = expiry_date.strftime("%d%b%y").upper()

            # Construct symbol
            option_symbol = f"{underlying}{expiry_formatted}{int(strike)}{option_type}"

            return option_symbol

        except Exception as e:
            logger.error(f"Error constructing option symbol: {e}")
            return None

    def fetch_option_quote(self, option_symbol: str, exchange: str = "NFO") -> Optional[Dict]:
        """
        Fetch single option quote from OpenAlgo

        Args:
            option_symbol: Option symbol (e.g., NIFTY28NOV2524000CE)
            exchange: Exchange code

        Returns:
            Dict with {ltp, oi, volume, bid, ask, iv} or None
        """
        try:
            self.rate_limiter.wait_if_needed()

            result = self.openalgo.quotes(symbol=option_symbol, exchange=exchange)

            if isinstance(result, dict):
                # Handle nested data structure
                data = result.get('data', result)

                return {
                    'ltp': data.get('ltp'),
                    'oi': data.get('oi') or data.get('open_interest') or data.get('openInterest'),
                    'volume': data.get('volume'),
                    'bid': data.get('bid') or data.get('bidprice'),
                    'ask': data.get('ask') or data.get('askprice'),
                    'iv': data.get('iv') or data.get('impliedVolatility')
                }

            return None

        except Exception as e:
            logger.debug(f"Failed to fetch {option_symbol}: {e}")
            return None

    def generate_strikes(self, atm_strike: float, range_count: int,
                        symbol: str) -> List[float]:
        """
        Generate strike list based on symbol's interval

        Args:
            atm_strike: At-the-money strike
            range_count: Number of strikes above and below ATM
            symbol: Underlying symbol

        Returns:
            List of strike prices
        """
        interval = self.symbol_manager.get_strike_interval(symbol)
        strikes = []

        for i in range(-range_count, range_count + 1):
            strikes.append(atm_strike + (i * interval))

        return sorted(strikes)

    def fetch_option_chain(self, symbol: str, expiry: str, atm_strike: float,
                          strike_range: int = 20, exchange: str = "NFO") -> Dict:
        """
        Fetch complete option chain for given parameters

        Args:
            symbol: Underlying symbol
            expiry: Expiry date (DD-MMM-YY)
            atm_strike: At-the-money strike
            strike_range: Number of strikes above/below ATM
            exchange: Exchange code

        Returns:
            Dict with CE and PE data by strike
        """
        logger.info(f"Fetching option chain for {symbol} {expiry} ATM={atm_strike}")

        strikes = self.generate_strikes(atm_strike, strike_range, symbol)
        option_chain = {'CE': {}, 'PE': {}}
        fetch_count = 0
        success_count = 0

        for strike in strikes:
            # Fetch CE data
            ce_symbol = self.get_option_symbol(symbol, expiry, strike, "CE")
            if ce_symbol:
                ce_data = self.fetch_option_quote(ce_symbol, exchange)
                if ce_data and ce_data.get('ltp'):
                    option_chain['CE'][strike] = ce_data
                    self._store_option_data(symbol, exchange, expiry, strike, "CE", ce_data)
                    success_count += 1
                fetch_count += 1

            # Fetch PE data
            pe_symbol = self.get_option_symbol(symbol, expiry, strike, "PE")
            if pe_symbol:
                pe_data = self.fetch_option_quote(pe_symbol, exchange)
                if pe_data and pe_data.get('ltp'):
                    option_chain['PE'][strike] = pe_data
                    self._store_option_data(symbol, exchange, expiry, strike, "PE", pe_data)
                    success_count += 1
                fetch_count += 1

        logger.info(f"Fetched {success_count}/{fetch_count} option quotes for {symbol} {expiry}")
        return option_chain

    def _store_option_data(self, symbol: str, exchange: str, expiry: str,
                          strike: float, option_type: str, data: Dict):
        """
        Store option data in QuestDB

        Args:
            symbol: Underlying symbol
            exchange: Exchange code
            expiry: Expiry date
            strike: Strike price
            option_type: CE or PE
            data: Option data dict
        """
        try:
            self.questdb.insert_option_oi(
                symbol=symbol,
                exchange=exchange,
                expiry=expiry,
                strike=strike,
                option_type=option_type,
                oi=data.get('oi'),
                volume=data.get('volume'),
                ltp=data.get('ltp'),
                bid=data.get('bid'),
                ask=data.get('ask'),
                iv=data.get('iv')
            )
        except Exception as e:
            logger.error(f"Error storing option data: {e}")

    def calculate_daily_changes(self, symbol: str, expiry: str,
                               exchange: str = "NFO") -> Dict:
        """
        Calculate OI changes from previous day using database snapshots

        Args:
            symbol: Underlying symbol
            expiry: Expiry date
            exchange: Exchange code

        Returns:
            Dict with OI changes by strike and option type
        """
        return self.questdb.calculate_oi_changes(symbol, expiry, exchange)

    def is_market_hours(self) -> bool:
        """
        Check if current time is within market hours (9:15 AM - 3:30 PM IST)

        Returns:
            True if within market hours
        """
        try:
            now = datetime.now(self.ist_tz)

            # Check if it's a weekday (Monday=0, Sunday=6)
            if now.weekday() > 4:  # Saturday or Sunday
                return False

            # Market hours: 9:15 AM to 3:30 PM IST
            market_start = now.replace(hour=9, minute=15, second=0, microsecond=0)
            market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)

            return market_start <= now <= market_end

        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
            return False

    def start_periodic_fetch(self, symbol: str, expiry: str, atm_strike: float,
                           interval_seconds: int = 300, exchange: str = "NFO"):
        """
        Background task to fetch OI data periodically

        Args:
            symbol: Underlying symbol
            expiry: Expiry date
            atm_strike: At-the-money strike
            interval_seconds: Fetch interval (default: 5 minutes)
            exchange: Exchange code
        """
        fetch_key = f"{symbol}_{expiry}"

        # Stop existing fetcher for this symbol/expiry
        if fetch_key in self.running_fetchers:
            logger.info(f"Stopping existing fetcher for {fetch_key}")
            self.running_fetchers[fetch_key]['stop'] = True

        # Create stop flag
        stop_flag = {'stop': False}
        self.running_fetchers[fetch_key] = stop_flag

        def fetch_loop():
            logger.info(f"Started periodic OI fetch for {symbol} {expiry}")
            last_snapshot_date = None

            while not stop_flag['stop']:
                try:
                    if self.is_market_hours():
                        # Fetch underlying price and update ATM
                        underlying_price = self.fetch_underlying_price(symbol)
                        if underlying_price:
                            # Calculate new ATM (could have changed)
                            from atm_calculator import ATMCalculator
                            atm_calc = ATMCalculator(self.symbol_manager)
                            current_atm = atm_calc.calculate_atm(symbol, underlying_price)

                            # Fetch option chain
                            oi_data = self.fetch_option_chain(
                                symbol, expiry, current_atm, strike_range=20, exchange=exchange
                            )

                            logger.info(f"Successfully fetched OI for {symbol} {expiry}")

                            # Save snapshot at market open and close
                            now = datetime.now(self.ist_tz)
                            today = now.date()

                            # Start of day snapshot (9:15 AM)
                            if (now.hour == 9 and now.minute >= 15 and now.minute < 20 and
                                last_snapshot_date != today):
                                current_oi = self.questdb.get_oi_for_expiry(symbol, expiry, exchange)
                                self.questdb.save_oi_snapshot(
                                    symbol, expiry, exchange, current_oi, snapshot_type='start'
                                )
                                last_snapshot_date = today
                                logger.info(f"Saved start-of-day snapshot for {symbol} {expiry}")

                            # End of day snapshot (3:25 PM)
                            if now.hour == 15 and now.minute >= 25:
                                current_oi = self.questdb.get_oi_for_expiry(symbol, expiry, exchange)
                                self.questdb.save_oi_snapshot(
                                    symbol, expiry, exchange, current_oi, snapshot_type='end'
                                )
                                logger.info(f"Saved end-of-day snapshot for {symbol} {expiry}")

                    else:
                        logger.debug(f"Outside market hours, skipping fetch for {symbol}")

                except Exception as e:
                    logger.error(f"Error in periodic fetch for {symbol} {expiry}: {e}")

                # Wait for next interval
                time.sleep(interval_seconds)

            logger.info(f"Stopped periodic OI fetch for {symbol} {expiry}")

        # Start fetch thread
        thread = threading.Thread(target=fetch_loop, daemon=True)
        thread.start()

        return fetch_key

    def stop_periodic_fetch(self, symbol: str, expiry: str):
        """
        Stop periodic fetch for a symbol/expiry

        Args:
            symbol: Underlying symbol
            expiry: Expiry date
        """
        fetch_key = f"{symbol}_{expiry}"

        if fetch_key in self.running_fetchers:
            self.running_fetchers[fetch_key]['stop'] = True
            del self.running_fetchers[fetch_key]
            logger.info(f"Stopped fetcher for {fetch_key}")
            return True

        return False

    def stop_all_fetchers(self):
        """Stop all periodic fetchers"""
        for fetch_key in list(self.running_fetchers.keys()):
            self.running_fetchers[fetch_key]['stop'] = True

        self.running_fetchers.clear()
        logger.info("Stopped all OI fetchers")

    def get_active_fetchers(self) -> List[str]:
        """Get list of active fetchers"""
        return list(self.running_fetchers.keys())
