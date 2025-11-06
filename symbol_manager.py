"""
Symbol Manager - Dynamic F&O Symbol and Expiry Management
Handles symbol discovery, expiry fetching, and symbol categorization
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import os

logger = logging.getLogger(__name__)


class SymbolManager:
    """Manages dynamic symbol discovery and expiry fetching for F&O instruments"""

    def __init__(self, openalgo_client):
        """
        Initialize Symbol Manager

        Args:
            openalgo_client: OpenAlgo API client instance
        """
        self.client = openalgo_client
        self.symbol_cache = {}  # Cache symbols and expiries
        self.cache_ttl = 3600  # 1 hour cache in seconds
        self.last_cache_update = {}

        # Load F&O symbols configuration
        self.fo_symbols = self._load_fo_symbols()

    def _load_fo_symbols(self) -> Dict:
        """Load F&O symbols from configuration or use defaults"""
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'fo_symbols.json')

        # Default F&O symbols
        default_symbols = {
            "indices": [
                "NIFTY",
                "BANKNIFTY",
                "FINNIFTY",
                "MIDCPNIFTY"
            ],
            "stocks": [
                "RELIANCE",
                "TCS",
                "INFY",
                "HDFCBANK",
                "ICICIBANK",
                "HINDUNILVR",
                "ITC",
                "SBIN",
                "BHARTIARTL",
                "KOTAKBANK",
                "LT",
                "AXISBANK",
                "BAJFINANCE",
                "ASIANPAINT",
                "MARUTI",
                "TITAN",
                "SUNPHARMA",
                "ULTRACEMCO",
                "NESTLEIND",
                "WIPRO"
            ]
        }

        # Try to load from config file
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load F&O symbols config: {e}")

        return default_symbols

    def get_fo_symbols(self) -> Dict[str, List[str]]:
        """
        Get list of all F&O symbols (indices and stocks)

        Returns:
            Dict with 'indices' and 'stocks' lists
        """
        return self.fo_symbols

    def get_all_symbols(self) -> List[str]:
        """Get flat list of all F&O symbols"""
        return self.fo_symbols['indices'] + self.fo_symbols['stocks']

    def is_index(self, symbol: str) -> bool:
        """Check if symbol is an index"""
        return symbol in self.fo_symbols['indices']

    def is_stock(self, symbol: str) -> bool:
        """Check if symbol is a stock"""
        return symbol in self.fo_symbols['stocks']

    def get_expiry_dates(self, symbol: str, exchange: str = "NFO",
                        force_refresh: bool = False) -> List[str]:
        """
        Fetch all available expiry dates for a symbol from OpenAlgo

        Args:
            symbol: Underlying symbol (e.g., NIFTY, RELIANCE)
            exchange: Exchange code (NFO, BFO, etc.)
            force_refresh: Force refresh cache

        Returns:
            List of expiry dates in DD-MMM-YY format (e.g., ['28-NOV-25', '05-DEC-25'])
        """
        cache_key = f"{symbol}_{exchange}"

        # Check cache
        if not force_refresh and cache_key in self.symbol_cache:
            cache_time = self.last_cache_update.get(cache_key, 0)
            if datetime.now().timestamp() - cache_time < self.cache_ttl:
                logger.info(f"Returning cached expiries for {symbol}")
                return self.symbol_cache[cache_key]

        # Fetch from OpenAlgo
        try:
            logger.info(f"Fetching expiry dates for {symbol} from OpenAlgo")
            result = self.client.expiry(
                symbol=symbol,
                exchange=exchange,
                instrumenttype="options"
            )

            # Result should be a list of expiry dates
            if isinstance(result, dict) and 'data' in result:
                expiries = result['data']
            elif isinstance(result, list):
                expiries = result
            else:
                logger.error(f"Unexpected expiry response format: {result}")
                return []

            # Cache the result
            self.symbol_cache[cache_key] = expiries
            self.last_cache_update[cache_key] = datetime.now().timestamp()

            logger.info(f"Fetched {len(expiries)} expiries for {symbol}: {expiries[:3]}...")
            return expiries

        except Exception as e:
            logger.error(f"Error fetching expiry dates for {symbol}: {e}")
            # Return cached data if available
            return self.symbol_cache.get(cache_key, [])

    def get_next_expiry(self, symbol: str, exchange: str = "NFO") -> Optional[str]:
        """
        Get the nearest upcoming expiry (default selection)

        Args:
            symbol: Underlying symbol
            exchange: Exchange code

        Returns:
            Nearest expiry date or None
        """
        expiries = self.get_expiry_dates(symbol, exchange)

        if not expiries:
            return None

        # Expiries are already sorted chronologically from OpenAlgo
        # Return the first one (nearest expiry)
        return expiries[0]

    def get_monthly_expiry(self, symbol: str, exchange: str = "NFO") -> Optional[str]:
        """
        Get the current month's expiry (monthly expiry)

        Args:
            symbol: Underlying symbol
            exchange: Exchange code

        Returns:
            Monthly expiry date or None
        """
        expiries = self.get_expiry_dates(symbol, exchange)

        if not expiries:
            return None

        # For indices, monthly expiry is typically the last Thursday
        # For stocks, monthly expiry is also the last Thursday
        # We can identify monthly expiry by checking if it's the last expiry of the month

        monthly_expiries = self.filter_monthly_expiries(expiries)
        return monthly_expiries[0] if monthly_expiries else expiries[0]

    def is_monthly_expiry(self, expiry_date: str) -> bool:
        """
        Determine if expiry is monthly (last Thursday) vs weekly

        Args:
            expiry_date: Expiry date in DD-MMM-YY format

        Returns:
            True if monthly expiry, False otherwise
        """
        try:
            # Parse the date
            date_obj = datetime.strptime(expiry_date, "%d-%b-%y")

            # Check if it's the last Thursday of the month
            # Get the last day of the month
            if date_obj.month == 12:
                next_month = date_obj.replace(year=date_obj.year + 1, month=1, day=1)
            else:
                next_month = date_obj.replace(month=date_obj.month + 1, day=1)

            last_day = next_month - timedelta(days=1)

            # Find the last Thursday
            # Thursday is weekday 3 (Monday is 0)
            last_thursday = last_day
            while last_thursday.weekday() != 3:  # 3 = Thursday
                last_thursday -= timedelta(days=1)

            # Check if the expiry date is the last Thursday
            return date_obj.date() == last_thursday.date()

        except Exception as e:
            logger.error(f"Error parsing expiry date {expiry_date}: {e}")
            return False

    def filter_monthly_expiries(self, expiries: List[str]) -> List[str]:
        """
        Filter to show only monthly expiries (last Thursday of each month)

        Args:
            expiries: List of all expiry dates

        Returns:
            List of monthly expiry dates only
        """
        monthly_expiries = []
        seen_months = set()

        for expiry in expiries:
            try:
                date_obj = datetime.strptime(expiry, "%d-%b-%y")
                month_key = (date_obj.year, date_obj.month)

                # If we haven't seen this month yet, check if it's monthly expiry
                if month_key not in seen_months:
                    if self.is_monthly_expiry(expiry):
                        monthly_expiries.append(expiry)
                        seen_months.add(month_key)
            except Exception as e:
                logger.warning(f"Error processing expiry {expiry}: {e}")
                continue

        return monthly_expiries

    def filter_expiries_for_stocks(self, expiries: List[str]) -> List[str]:
        """
        Filter expiries for stocks (show only monthly expiries)

        Args:
            expiries: List of all expiry dates

        Returns:
            List of monthly expiry dates for stocks
        """
        return self.filter_monthly_expiries(expiries)

    def get_expiries_for_symbol(self, symbol: str, exchange: str = "NFO") -> List[str]:
        """
        Get expiries for a symbol with automatic filtering based on symbol type

        Args:
            symbol: Underlying symbol
            exchange: Exchange code

        Returns:
            List of expiry dates (all for indices, monthly only for stocks)
        """
        expiries = self.get_expiry_dates(symbol, exchange)

        # For stocks, filter to show only monthly expiries
        if self.is_stock(symbol):
            logger.info(f"{symbol} is a stock, filtering to monthly expiries only")
            return self.filter_expiries_for_stocks(expiries)

        # For indices, show all expiries (weekly + monthly)
        return expiries

    def get_strike_interval(self, symbol: str) -> int:
        """
        Get the strike price interval for a symbol

        Args:
            symbol: Underlying symbol

        Returns:
            Strike interval in points (e.g., 100 for NIFTY)
        """
        # Standard intervals for indices
        intervals = {
            'NIFTY': 50,  # NIFTY has 50 point intervals
            'BANKNIFTY': 100,
            'FINNIFTY': 50,
            'MIDCPNIFTY': 25,
            'SENSEX': 100,
            'BANKEX': 100
        }

        # Check if symbol is in the predefined list
        if symbol in intervals:
            return intervals[symbol]

        # For stocks, return a default interval
        # This could be made more sophisticated based on stock price
        return 50

    def clear_cache(self, symbol: Optional[str] = None):
        """
        Clear the expiry cache

        Args:
            symbol: Specific symbol to clear, or None to clear all
        """
        if symbol:
            cache_keys = [k for k in self.symbol_cache.keys() if k.startswith(symbol)]
            for key in cache_keys:
                del self.symbol_cache[key]
                if key in self.last_cache_update:
                    del self.last_cache_update[key]
            logger.info(f"Cleared cache for {symbol}")
        else:
            self.symbol_cache.clear()
            self.last_cache_update.clear()
            logger.info("Cleared all symbol cache")

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol is supported for F&O

        Args:
            symbol: Symbol to validate

        Returns:
            True if symbol is valid F&O instrument
        """
        all_symbols = self.get_all_symbols()
        return symbol in all_symbols

    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Get comprehensive information about a symbol

        Args:
            symbol: Symbol to get info for

        Returns:
            Dict with symbol metadata
        """
        return {
            'symbol': symbol,
            'is_index': self.is_index(symbol),
            'is_stock': self.is_stock(symbol),
            'strike_interval': self.get_strike_interval(symbol),
            'exchange': 'NFO',  # Default exchange
            'valid': self.validate_symbol(symbol)
        }
