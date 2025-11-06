import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class QuestDBClient:
    def __init__(self, host='127.0.0.1', port=8812, database='qdb', user='admin', password='quest'):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            # Close existing connections if any
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection:
                self.connection.close()
                self.connection = None

            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor()
            logger.info("Connected to QuestDB")
        except Exception as e:
            logger.error(f"Failed to connect to QuestDB: {e}")
            self.connection = None
            self.cursor = None

    def is_connected(self):
        return self.connection is not None and not self.connection.closed

    def create_tables(self):
        if not self.is_connected():
            return

        tables = [
            """
            CREATE TABLE IF NOT EXISTS ticks_ltp (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                ltp DOUBLE,
                volume LONG
            ) timestamp(timestamp) PARTITION BY DAY;
            """,
            """
            CREATE TABLE IF NOT EXISTS ticks_quote (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                ltp DOUBLE,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume LONG,
                last_trade_quantity LONG,
                change DOUBLE,
                change_percent DOUBLE,
                avg_trade_price DOUBLE
            ) timestamp(timestamp) PARTITION BY DAY;
            """,
            """
            CREATE TABLE IF NOT EXISTS ticks_depth (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                level INT,
                bid DOUBLE,
                ask DOUBLE,
                bid_qty LONG,
                ask_qty LONG,
                bid_orders INT,
                ask_orders INT
            ) timestamp(timestamp) PARTITION BY DAY;
            """,
            """
            CREATE TABLE IF NOT EXISTS options_oi (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                exchange SYMBOL,
                expiry SYMBOL,
                strike DOUBLE,
                option_type SYMBOL,
                oi LONG,
                oi_change LONG,
                volume LONG,
                ltp DOUBLE,
                bid DOUBLE,
                ask DOUBLE,
                iv DOUBLE
            ) timestamp(timestamp) PARTITION BY DAY;
            """,
            """
            CREATE TABLE IF NOT EXISTS options_oi_snapshot (
                snapshot_date TIMESTAMP,
                symbol SYMBOL,
                exchange SYMBOL,
                expiry SYMBOL,
                strike DOUBLE,
                option_type SYMBOL,
                oi_start_of_day LONG,
                oi_end_of_day LONG
            ) timestamp(snapshot_date) PARTITION BY MONTH;
            """,
            """
            CREATE TABLE IF NOT EXISTS underlying_quotes (
                timestamp TIMESTAMP,
                symbol SYMBOL,
                exchange SYMBOL,
                ltp DOUBLE,
                high DOUBLE,
                low DOUBLE,
                open DOUBLE,
                close DOUBLE,
                volume LONG
            ) timestamp(timestamp) PARTITION BY DAY;
            """
        ]

        for table_query in tables:
            try:
                self.cursor.execute(table_query)
                self.connection.commit()
            except Exception as e:
                logger.warning(f"Table creation: {e}")
                self.connection.rollback()

    def insert_ltp(self, symbol, ltp, volume=0):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_ltp (timestamp, symbol, ltp, volume)
            VALUES (%s, %s, %s, %s)
            """
            timestamp = datetime.now()  # Use local time (IST)
            # Ensure volume is never NULL, default to 0
            volume = volume if volume is not None else 0
            self.cursor.execute(query, (timestamp, symbol, ltp, volume))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert LTP: {e}")
            self.connection.rollback()
            return False

    def insert_quote(self, symbol, ltp, open_price, high, low, close, volume,
                     last_trade_quantity=None, change=None, change_percent=None, avg_trade_price=None):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_quote (timestamp, symbol, ltp, open, high, low, close,
                                   volume, last_trade_quantity, change, change_percent, avg_trade_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            timestamp = datetime.now()  # Use local time (IST)
            # Ensure volume fields are never NULL, default to 0
            volume = volume if volume is not None else 0
            last_trade_quantity = last_trade_quantity if last_trade_quantity is not None else 0

            self.cursor.execute(query, (
                timestamp, symbol, ltp, open_price, high, low, close,
                volume, last_trade_quantity, change, change_percent, avg_trade_price
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert quote: {e}")
            self.connection.rollback()
            return False

    def insert_depth(self, symbol, level, bid, ask, bid_qty, ask_qty, bid_orders=None, ask_orders=None):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_depth (timestamp, symbol, level, bid, ask, bid_qty, ask_qty, bid_orders, ask_orders)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            timestamp = datetime.now()  # Use local time (IST)
            # Ensure quantities are never NULL, default to 0
            bid_qty = bid_qty if bid_qty is not None else 0
            ask_qty = ask_qty if ask_qty is not None else 0

            self.cursor.execute(query, (timestamp, symbol, level, bid, ask, bid_qty, ask_qty, bid_orders, ask_orders))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert depth: {e}")
            self.connection.rollback()
            return False

    def batch_insert_ltp(self, data):
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO ticks_ltp (timestamp, symbol, ltp)
            VALUES %s
            """
            timestamp = datetime.now()  # Use local time (IST)
            values = [(timestamp, item['symbol'], item['ltp']) for item in data]
            execute_values(self.cursor, query, values)
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to batch insert LTP: {e}")
            self.connection.rollback()
            return False

    def get_latest_ticks(self, symbol, limit=100):
        if not self.is_connected():
            return []

        try:
            query = """
            SELECT timestamp, ltp
            FROM ticks_ltp
            WHERE symbol = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """
            self.cursor.execute(query, (symbol, limit))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to fetch latest ticks: {e}")
            return []

    def get_aggregated_data(self, symbol, interval='1m', start_time=None, limit=500):
        if not self.is_connected():
            return []

        try:
            if start_time is None:
                start_time = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            # QuestDB aggregation query
            query = """
            SELECT
                timestamp as time,
                first(ltp) as open,
                max(ltp) as high,
                min(ltp) as low,
                last(ltp) as close,
                count(*) as volume
            FROM ticks_ltp
            WHERE symbol = %s AND timestamp >= %s
            SAMPLE BY %s
            ORDER BY time DESC
            LIMIT %s
            """

            self.cursor.execute(query, (symbol, start_time, interval, limit))
            results = self.cursor.fetchall()

            # Reverse to get chronological order
            return list(reversed(results))
        except Exception as e:
            logger.error(f"Failed to fetch aggregated data: {e}")
            # Fallback to simple query
            try:
                query = """
                SELECT
                    timestamp as time,
                    ltp as close,
                    ltp as open,
                    ltp as high,
                    ltp as low,
                    1 as volume
                FROM ticks_ltp
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """
                self.cursor.execute(query, (symbol, limit))
                results = self.cursor.fetchall()
                return list(reversed(results))
            except Exception as e2:
                logger.error(f"Fallback query also failed: {e2}")
                return []

    # =====================================================
    # Options OI Methods
    # =====================================================

    def insert_option_oi(self, symbol, exchange, expiry, strike, option_type,
                        oi, volume, ltp, bid=None, ask=None, oi_change=None, iv=None):
        """Insert option OI data into database"""
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO options_oi (timestamp, symbol, exchange, expiry, strike, option_type,
                                   oi, oi_change, volume, ltp, bid, ask, iv)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            timestamp = datetime.now()

            # Ensure numeric fields are not None
            oi = oi if oi is not None else 0
            volume = volume if volume is not None else 0
            oi_change = oi_change if oi_change is not None else 0

            self.cursor.execute(query, (
                timestamp, symbol, exchange, expiry, strike, option_type,
                oi, oi_change, volume, ltp, bid, ask, iv
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert option OI: {e}")
            self.connection.rollback()
            return False

    def insert_underlying_quote(self, symbol, exchange, ltp, high=None, low=None,
                               open_price=None, close=None, volume=None):
        """Insert underlying asset quote"""
        if not self.is_connected():
            return False

        try:
            query = """
            INSERT INTO underlying_quotes (timestamp, symbol, exchange, ltp, high, low, open, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            timestamp = datetime.now()
            volume = volume if volume is not None else 0

            self.cursor.execute(query, (
                timestamp, symbol, exchange, ltp, high, low, open_price, close, volume
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to insert underlying quote: {e}")
            self.connection.rollback()
            return False

    def get_latest_underlying_price(self, symbol, exchange="NSE"):
        """Get latest underlying price"""
        if not self.is_connected():
            return None

        try:
            query = """
            SELECT ltp, high, low, open, close, timestamp
            FROM underlying_quotes
            WHERE symbol = %s AND exchange = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """
            self.cursor.execute(query, (symbol, exchange))
            result = self.cursor.fetchone()

            if result:
                return {
                    'ltp': float(result[0]) if result[0] else 0,
                    'high': float(result[1]) if result[1] else 0,
                    'low': float(result[2]) if result[2] else 0,
                    'open': float(result[3]) if result[3] else 0,
                    'close': float(result[4]) if result[4] else 0,
                    'timestamp': result[5]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get underlying price: {e}")
            return None

    def get_oi_for_expiry(self, symbol, expiry, exchange="NFO", limit=100):
        """Get latest OI data for a specific expiry"""
        if not self.is_connected():
            return {}

        try:
            # Get the latest timestamp for this symbol/expiry
            query_time = """
            SELECT MAX(timestamp) as latest
            FROM options_oi
            WHERE symbol = %s AND expiry = %s AND exchange = %s
            """
            self.cursor.execute(query_time, (symbol, expiry, exchange))
            latest_time = self.cursor.fetchone()[0]

            if not latest_time:
                return {}

            # Get all strikes and option types for the latest timestamp
            query = """
            SELECT strike, option_type, oi, oi_change, volume, ltp, bid, ask, iv
            FROM options_oi
            WHERE symbol = %s AND expiry = %s AND exchange = %s
                  AND timestamp = %s
            ORDER BY strike ASC
            """
            self.cursor.execute(query, (symbol, expiry, exchange, latest_time))
            results = self.cursor.fetchall()

            # Organize data by option type
            oi_data = {'CE': {}, 'PE': {}}

            for row in results:
                strike = float(row[0])
                option_type = row[1]
                data = {
                    'oi': int(row[2]) if row[2] else 0,
                    'oi_change': int(row[3]) if row[3] else 0,
                    'volume': int(row[4]) if row[4] else 0,
                    'ltp': float(row[5]) if row[5] else 0,
                    'bid': float(row[6]) if row[6] else 0,
                    'ask': float(row[7]) if row[7] else 0,
                    'iv': float(row[8]) if row[8] else 0
                }
                oi_data[option_type][strike] = data

            return oi_data

        except Exception as e:
            logger.error(f"Failed to get OI data: {e}")
            return {}

    def save_oi_snapshot(self, symbol, expiry, exchange, oi_data, snapshot_type='start'):
        """Save OI snapshot for start or end of day"""
        if not self.is_connected():
            return False

        try:
            snapshot_date = datetime.now()

            for option_type in ['CE', 'PE']:
                for strike, data in oi_data.get(option_type, {}).items():
                    query = """
                    INSERT INTO options_oi_snapshot
                    (snapshot_date, symbol, exchange, expiry, strike, option_type,
                     oi_start_of_day, oi_end_of_day)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    oi_value = data.get('oi', 0)
                    oi_start = oi_value if snapshot_type == 'start' else 0
                    oi_end = oi_value if snapshot_type == 'end' else 0

                    self.cursor.execute(query, (
                        snapshot_date, symbol, exchange, expiry, strike, option_type,
                        oi_start, oi_end
                    ))

            self.connection.commit()
            logger.info(f"Saved OI snapshot for {symbol} {expiry}")
            return True

        except Exception as e:
            logger.error(f"Failed to save OI snapshot: {e}")
            self.connection.rollback()
            return False

    def get_oi_snapshot(self, symbol, expiry, date, exchange="NFO"):
        """Get OI snapshot for a specific date"""
        if not self.is_connected():
            return {}

        try:
            query = """
            SELECT strike, option_type, oi_start_of_day, oi_end_of_day
            FROM options_oi_snapshot
            WHERE symbol = %s AND expiry = %s AND exchange = %s
                  AND DATE(snapshot_date) = %s
            ORDER BY strike ASC
            """
            self.cursor.execute(query, (symbol, expiry, exchange, date))
            results = self.cursor.fetchall()

            snapshot_data = {'CE': {}, 'PE': {}}

            for row in results:
                strike = float(row[0])
                option_type = row[1]
                snapshot_data[option_type][strike] = {
                    'oi_start': int(row[2]) if row[2] else 0,
                    'oi_end': int(row[3]) if row[3] else 0
                }

            return snapshot_data

        except Exception as e:
            logger.error(f"Failed to get OI snapshot: {e}")
            return {}

    def calculate_oi_changes(self, symbol, expiry, exchange="NFO"):
        """Calculate OI changes from previous day's snapshot"""
        if not self.is_connected():
            return {}

        try:
            # Get yesterday's snapshot
            from datetime import date, timedelta
            yesterday = date.today() - timedelta(days=1)
            yesterday_snapshot = self.get_oi_snapshot(symbol, expiry, yesterday, exchange)

            # Get current OI
            current_oi = self.get_oi_for_expiry(symbol, expiry, exchange)

            # Calculate changes
            oi_changes = {'CE': {}, 'PE': {}}

            for option_type in ['CE', 'PE']:
                current_strikes = current_oi.get(option_type, {})
                yesterday_strikes = yesterday_snapshot.get(option_type, {})

                for strike, current_data in current_strikes.items():
                    yesterday_oi = yesterday_strikes.get(strike, {}).get('oi_end', 0)
                    current_oi_val = current_data.get('oi', 0)
                    change = current_oi_val - yesterday_oi

                    oi_changes[option_type][strike] = {
                        'change': change,
                        'change_percent': (change / yesterday_oi * 100) if yesterday_oi > 0 else 0,
                        'current_oi': current_oi_val,
                        'previous_oi': yesterday_oi
                    }

            return oi_changes

        except Exception as e:
            logger.error(f"Failed to calculate OI changes: {e}")
            return {}

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Disconnected from QuestDB")