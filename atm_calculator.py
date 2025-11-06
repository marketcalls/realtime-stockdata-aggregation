"""
ATM Calculator - Universal At-The-Money Strike Calculation
Calculates ATM for any F&O instrument based on current price and strike intervals
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ATMCalculator:
    """Calculate At-The-Money strike for any F&O instrument"""

    def __init__(self, symbol_manager):
        """
        Initialize ATM Calculator

        Args:
            symbol_manager: Symbol manager for strike interval lookup
        """
        self.symbol_manager = symbol_manager

    def calculate_atm(self, symbol: str, current_price: float,
                     exchange: str = "NFO") -> float:
        """
        Universal ATM calculation

        Rounds current price to nearest strike interval.
        For example:
        - NIFTY at 24,385 with 50-point interval → ATM = 24,400
        - BANKNIFTY at 48,250 with 100-point interval → ATM = 48,300

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            exchange: Exchange code

        Returns:
            ATM strike price
        """
        try:
            # Get strike interval for the symbol
            interval = self.symbol_manager.get_strike_interval(symbol)

            # Round to nearest interval
            atm = round(current_price / interval) * interval

            logger.info(f"Calculated ATM for {symbol}: Price={current_price:.2f}, "
                       f"Interval={interval}, ATM={atm}")

            return atm

        except Exception as e:
            logger.error(f"Error calculating ATM for {symbol}: {e}")
            # Fallback: use 50 as default interval
            return round(current_price / 50) * 50

    def calculate_atm_with_bias(self, symbol: str, current_price: float,
                                bias: str = "nearest", exchange: str = "NFO") -> float:
        """
        Calculate ATM with directional bias

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            bias: 'nearest', 'higher', or 'lower'
            exchange: Exchange code

        Returns:
            ATM strike based on bias
        """
        interval = self.symbol_manager.get_strike_interval(symbol)

        if bias == "nearest":
            return round(current_price / interval) * interval
        elif bias == "higher":
            # Round up to next strike
            import math
            return math.ceil(current_price / interval) * interval
        elif bias == "lower":
            # Round down to previous strike
            import math
            return math.floor(current_price / interval) * interval
        else:
            # Default to nearest
            return round(current_price / interval) * interval

    def get_itm_strikes(self, symbol: str, current_price: float, option_type: str,
                       count: int = 5, exchange: str = "NFO") -> list:
        """
        Get In-The-Money strikes for a given option type

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            option_type: 'CE' or 'PE'
            count: Number of ITM strikes to return
            exchange: Exchange code

        Returns:
            List of ITM strike prices
        """
        interval = self.symbol_manager.get_strike_interval(symbol)
        atm = self.calculate_atm(symbol, current_price, exchange)

        itm_strikes = []

        if option_type == "CE":
            # For calls, ITM strikes are below current price
            for i in range(count):
                strike = atm - ((i + 1) * interval)
                if strike > 0:
                    itm_strikes.append(strike)
        elif option_type == "PE":
            # For puts, ITM strikes are above current price
            for i in range(count):
                strike = atm + ((i + 1) * interval)
                itm_strikes.append(strike)

        return itm_strikes

    def get_otm_strikes(self, symbol: str, current_price: float, option_type: str,
                       count: int = 5, exchange: str = "NFO") -> list:
        """
        Get Out-of-The-Money strikes for a given option type

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            option_type: 'CE' or 'PE'
            count: Number of OTM strikes to return
            exchange: Exchange code

        Returns:
            List of OTM strike prices
        """
        interval = self.symbol_manager.get_strike_interval(symbol)
        atm = self.calculate_atm(symbol, current_price, exchange)

        otm_strikes = []

        if option_type == "CE":
            # For calls, OTM strikes are above current price
            for i in range(count):
                strike = atm + ((i + 1) * interval)
                otm_strikes.append(strike)
        elif option_type == "PE":
            # For puts, OTM strikes are below current price
            for i in range(count):
                strike = atm - ((i + 1) * interval)
                if strike > 0:
                    otm_strikes.append(strike)

        return otm_strikes

    def is_itm(self, symbol: str, current_price: float, strike: float,
              option_type: str) -> bool:
        """
        Check if option is In-The-Money

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            strike: Strike price
            option_type: 'CE' or 'PE'

        Returns:
            True if ITM, False otherwise
        """
        if option_type == "CE":
            return current_price > strike
        elif option_type == "PE":
            return current_price < strike
        return False

    def is_otm(self, symbol: str, current_price: float, strike: float,
              option_type: str) -> bool:
        """
        Check if option is Out-of-The-Money

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            strike: Strike price
            option_type: 'CE' or 'PE'

        Returns:
            True if OTM, False otherwise
        """
        if option_type == "CE":
            return current_price < strike
        elif option_type == "PE":
            return current_price > strike
        return False

    def is_atm(self, symbol: str, current_price: float, strike: float,
              tolerance_pct: float = 2.0) -> bool:
        """
        Check if strike is At-The-Money (within tolerance)

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            strike: Strike price
            tolerance_pct: Tolerance percentage (default 2%)

        Returns:
            True if ATM (within tolerance), False otherwise
        """
        atm = self.calculate_atm(symbol, current_price)
        return strike == atm

    def get_moneyness(self, symbol: str, current_price: float, strike: float,
                     option_type: str) -> str:
        """
        Get moneyness classification for an option

        Args:
            symbol: Underlying symbol
            current_price: Current market price
            strike: Strike price
            option_type: 'CE' or 'PE'

        Returns:
            'ITM', 'ATM', or 'OTM'
        """
        if self.is_atm(symbol, current_price, strike):
            return 'ATM'
        elif self.is_itm(symbol, current_price, strike, option_type):
            return 'ITM'
        else:
            return 'OTM'

    def get_intrinsic_value(self, current_price: float, strike: float,
                           option_type: str) -> float:
        """
        Calculate intrinsic value of an option

        Args:
            current_price: Current market price
            strike: Strike price
            option_type: 'CE' or 'PE'

        Returns:
            Intrinsic value (0 if OTM)
        """
        if option_type == "CE":
            return max(0, current_price - strike)
        elif option_type == "PE":
            return max(0, strike - current_price)
        return 0

    def get_time_value(self, ltp: float, intrinsic_value: float) -> float:
        """
        Calculate time value of an option

        Args:
            ltp: Last traded price (option premium)
            intrinsic_value: Intrinsic value

        Returns:
            Time value
        """
        return max(0, ltp - intrinsic_value)
