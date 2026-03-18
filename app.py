from flask import Flask, render_template, request, jsonify, session, Response
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import os
import sys
import io
import queue
from datetime import datetime
from time import time as monotime
import threading
import logging
from config_manager import ConfigManager
from questdb_client import QuestDBClient
from openalgo_client import OpenAlgoStreamClient
from candle_aggregator import CandleAggregator

# Suppress stdout from OpenAlgo SDK
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = io.StringIO()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set base level to INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set specific loggers
logging.getLogger('openalgo_client').setLevel(logging.WARNING)  # Only warnings and errors
logging.getLogger('candle_aggregator').setLevel(logging.INFO)
logging.getLogger('questdb_client').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logs
logging.getLogger('openalgo').setLevel(logging.ERROR)  # Suppress OpenAlgo SDK debug output
logging.getLogger('urllib3').setLevel(logging.WARNING)  # Suppress urllib3 debug
logging.getLogger('engineio').setLevel(logging.WARNING)  # Suppress engineio debug
logging.getLogger('socketio').setLevel(logging.WARNING)  # Suppress socketio debug

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=False)

# Initialize managers
config_manager = ConfigManager()
questdb_client = QuestDBClient()
stream_client = None
candle_aggregator = CandleAggregator(questdb_client)

# SSE subscriber management
sse_subscribers = {}  # {room: {client_id: queue.Queue}}
sse_lock = threading.Lock()
sse_last_emit = {}  # {room: timestamp} for throttling


def sse_subscribe(room, client_id):
    """Add an SSE subscriber to a room"""
    q = queue.Queue(maxsize=50)
    with sse_lock:
        if room not in sse_subscribers:
            sse_subscribers[room] = {}
        sse_subscribers[room][client_id] = q
    return q


def sse_unsubscribe(room, client_id):
    """Remove an SSE subscriber from a room"""
    with sse_lock:
        if room in sse_subscribers:
            sse_subscribers[room].pop(client_id, None)
            if not sse_subscribers[room]:
                del sse_subscribers[room]


def sse_broadcast(room, data):
    """Broadcast data to all SSE subscribers in a room (throttled to 2/sec)"""
    now = monotime()
    if now - sse_last_emit.get(room, 0) < 0.5:
        return  # Throttle: max 2 updates per second per room
    sse_last_emit[room] = now

    with sse_lock:
        clients = sse_subscribers.get(room, {})
        for client_id, q in list(clients.items()):
            try:
                # Non-blocking put, drop if queue full (slow client)
                q.put_nowait(data)
            except queue.Full:
                pass


# Store real-time metrics
metrics = {
    'tick_rate': {},
    'last_update': {},
    'spreads': {},
    'imbalance': {},
    'total_ticks': 0,
    'active_symbols': 0,
    'connection_status': 'disconnected'
}

# Load symbols from symbols/symbols.txt
def load_symbols():
    symbols_file = os.path.join(os.path.dirname(__file__), 'symbols', 'symbols.txt')
    if os.path.exists(symbols_file):
        with open(symbols_file, 'r') as f:
            return json.load(f)
    return []

SYMBOLS = load_symbols()

@app.route('/')
def index():
    config = config_manager.get_config()
    return render_template('index.html',
                         config=config,
                         metrics=metrics,
                         symbols=SYMBOLS)

@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'POST':
        data = request.json
        config_manager.update_config(data)

        # Restart WebSocket connection with new config
        global stream_client
        if stream_client:
            stream_client.stop()

        if data.get('enabled'):
            start_websocket_client(data)

        return jsonify({'status': 'success', 'message': 'Configuration updated'})

    return jsonify(config_manager.get_config())

@app.route('/metrics')
def get_metrics():
    return jsonify(metrics)

@app.route('/start_stream', methods=['POST'])
def start_stream():
    data = request.json
    stream_type = data.get('stream_type', 'ltp')
    symbols = data.get('symbols', SYMBOLS)

    config = config_manager.get_config()
    if not config.get('api_key'):
        return jsonify({'status': 'error', 'message': 'API key not configured'})

    global stream_client

    try:
        if not stream_client:
            stream_client = OpenAlgoStreamClient(
                api_key=config['api_key'],
                rest_host=config.get('rest_host', 'http://127.0.0.1:5000'),
                ws_url=config.get('ws_url', 'ws://127.0.0.1:8765'),
                on_data_callback=handle_websocket_data
            )
            stream_client.start()

        # Subscribe to streams based on type
        success = False
        if stream_type == 'ltp':
            success = stream_client.subscribe_ltp(symbols)
        elif stream_type == 'quote':
            success = stream_client.subscribe_quote(symbols)
        elif stream_type == 'depth':
            success = stream_client.subscribe_depth(symbols)

        if success:
            metrics['connection_status'] = 'connected'
            metrics['active_symbols'] = len(symbols)
            return jsonify({'status': 'success', 'message': f'Started {stream_type} stream for {len(symbols)} symbols'})
        else:
            metrics['connection_status'] = 'disconnected'
            return jsonify({'status': 'error', 'message': f'Failed to start {stream_type} stream'})

    except Exception as e:
        app.logger.error(f"Error starting stream: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    global stream_client
    if stream_client:
        stream_client.stop()
        stream_client = None
        metrics['connection_status'] = 'disconnected'
        return jsonify({'status': 'success', 'message': 'Stream stopped'})

    return jsonify({'status': 'error', 'message': 'No active stream'})

def handle_websocket_data(data):
    """Handle incoming WebSocket data"""
    try:
        # Update metrics
        symbol = data.get('symbol')
        if symbol:

            metrics['last_update'][symbol] = datetime.now().isoformat()

            # Update tick rate
            if symbol not in metrics['tick_rate']:
                metrics['tick_rate'][symbol] = 0
            metrics['tick_rate'][symbol] += 1
            metrics['total_ticks'] += 1

            # Calculate spread if bid/ask available
            if 'bid' in data and 'ask' in data and data['bid'] is not None and data['ask'] is not None:
                spread = data['ask'] - data['bid']
                metrics['spreads'][symbol] = spread

            # Store in QuestDB with last_trade_quantity (NOT total volume)
            if 'ltp' in data and data['ltp'] is not None:
                # Store last_trade_quantity ONLY, not the day's total volume
                # This will be aggregated for candle volumes
                trade_qty = data.get('last_trade_quantity') or 0
                success = questdb_client.insert_ltp(symbol, data['ltp'], trade_qty)
                if not success:
                    app.logger.warning(f"Failed to store LTP for {symbol}")

                # Broadcast candle updates via SSE to subscribed clients
                with sse_lock:
                    active_rooms = set(sse_subscribers.keys())
                for tf in ['1m', '3m', '5m', '15m', '30m', '1h', '1d']:
                    room = f"{symbol}_{tf}"
                    if room in active_rooms:
                        candle = candle_aggregator._get_current_candle(symbol, tf)
                        if candle:
                            sse_broadcast(room, candle)

            # Store quote data with OHLC information
            if data.get('type') == 'quote':
                # Log the received quote data for debugging
                app.logger.debug(f"Quote data received for {symbol}: volume={data.get('volume')}, ltp={data.get('ltp')}")

                # Calculate change if not provided
                ltp = data.get('ltp')
                open_price = data.get('open')
                change = data.get('change')
                change_percent = data.get('change_percent')

                # Calculate change if not provided but we have ltp and open
                if change is None and ltp is not None and open_price is not None:
                    change = ltp - open_price
                    change_percent = (change / open_price * 100) if open_price != 0 else None

                questdb_client.insert_quote(
                    symbol=symbol,
                    ltp=ltp,
                    open_price=open_price,
                    high=data.get('high'),
                    low=data.get('low'),
                    close=data.get('close') or ltp,  # Use LTP as close if not provided
                    volume=data.get('volume') or 0,  # This is day's total volume - for reference only
                    last_trade_quantity=data.get('last_trade_quantity') or 0,  # This is what we aggregate
                    change=change,
                    change_percent=change_percent,
                    avg_trade_price=data.get('avg_trade_price')
                )

            # Store depth data if available
            if data.get('type') == 'depth' and 'depth' in data:
                depth_info = data.get('depth', {})

                # Process buy side (bids)
                buy_orders = depth_info.get('buy', [])
                for level, order in enumerate(buy_orders[:5]):  # Store top 5 levels
                    questdb_client.insert_depth(
                        symbol=symbol,
                        level=level,
                        bid=order.get('price', 0),
                        ask=None,  # No ask at this level for buy side
                        bid_qty=order.get('quantity', 0),
                        ask_qty=0,  # Use 0 instead of None
                        bid_orders=order.get('orders'),
                        ask_orders=None
                    )

                # Process sell side (asks)
                sell_orders = depth_info.get('sell', [])
                for level, order in enumerate(sell_orders[:5]):  # Store top 5 levels
                    # Update the same level with ask data
                    questdb_client.insert_depth(
                        symbol=symbol,
                        level=level,
                        bid=buy_orders[level].get('price', 0) if level < len(buy_orders) else None,
                        ask=order.get('price', 0),
                        bid_qty=buy_orders[level].get('quantity', 0) if level < len(buy_orders) else 0,
                        ask_qty=order.get('quantity', 0),
                        bid_orders=buy_orders[level].get('orders') if level < len(buy_orders) else None,
                        ask_orders=order.get('orders')
                    )
    except Exception as e:
        app.logger.error(f"Error handling WebSocket data: {e}")

def start_websocket_client(config):
    """Start WebSocket client in background thread"""
    def run_ws():
        global stream_client
        stream_client = OpenAlgoStreamClient(
            api_key=config['api_key'],
            rest_host=config.get('rest_host', 'http://127.0.0.1:5000'),
            ws_url=config.get('ws_url', 'ws://127.0.0.1:8765'),
            on_data_callback=handle_websocket_data
        )
        stream_client.start()

        # Subscribe to all enabled streams for all symbols
        if config.get('ltp_enabled'):
            stream_client.subscribe_ltp(SYMBOLS)
        if config.get('quote_enabled'):
            stream_client.subscribe_quote(SYMBOLS)
        if config.get('depth_enabled'):
            stream_client.subscribe_depth(SYMBOLS)

    thread = threading.Thread(target=run_ws, daemon=True)
    thread.start()

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'questdb_connected': questdb_client.is_connected(),
        'websocket_connected': metrics['connection_status'] == 'connected',
        'total_ticks': metrics['total_ticks']
    })

@app.route('/chart')
def chart():
    return render_template('chart.html')

@app.route('/api/symbols')
def get_symbols():
    """API endpoint to get symbols list"""
    return jsonify(SYMBOLS)

@app.route('/api/quote/<symbol>')
def get_latest_quote(symbol):
    """Get latest OHLCV data from ticks_quote table"""
    try:
        # Always reconnect to avoid stale connections
        questdb_client.connect()

        # Get the latest quote data from ticks_quote table
        query = """
        SELECT timestamp, ltp, open, high, low, close, volume, change, change_percent
        FROM ticks_quote
        WHERE symbol = %s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        questdb_client.cursor.execute(query, (symbol,))
        result = questdb_client.cursor.fetchone()

        if result:
            return jsonify({
                'status': 'success',
                'symbol': symbol,
                'timestamp': result[0].isoformat() if result[0] else None,
                'ltp': float(result[1]) if result[1] else 0,
                'open': float(result[2]) if result[2] else 0,
                'high': float(result[3]) if result[3] else 0,
                'low': float(result[4]) if result[4] else 0,
                'close': float(result[5]) if result[5] else 0,
                'volume': int(result[6]) if result[6] else 0,
                'change': float(result[7]) if result[7] else 0,
                'change_percent': float(result[8]) if result[8] else 0
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'No quote data available for {symbol}'
            }), 404

    except Exception as e:
        app.logger.error(f"Error fetching quote for {symbol}: {e}")
        # Try to reconnect and retry once
        try:
            questdb_client.connect()
            questdb_client.cursor.execute(query, (symbol,))
            result = questdb_client.cursor.fetchone()
            if result:
                return jsonify({
                    'status': 'success',
                    'symbol': symbol,
                    'timestamp': result[0].isoformat() if result[0] else None,
                    'ltp': float(result[1]) if result[1] else 0,
                    'open': float(result[2]) if result[2] else 0,
                    'high': float(result[3]) if result[3] else 0,
                    'low': float(result[4]) if result[4] else 0,
                    'close': float(result[5]) if result[5] else 0,
                    'volume': int(result[6]) if result[6] else 0,
                    'change': float(result[7]) if result[7] else 0,
                    'change_percent': float(result[8]) if result[8] else 0
                })
        except Exception as retry_error:
            app.logger.error(f"Retry also failed: {retry_error}")

        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/candles/<symbol>')
def get_candles(symbol):
    """Get aggregated candle data for a symbol from QuestDB"""
    timeframe = request.args.get('timeframe', '1m')
    limit = int(request.args.get('limit', 500))

    try:
        # Get properly aggregated candles
        candles = candle_aggregator.get_historical_candles(symbol, timeframe, limit)

        if not candles:
            app.logger.info(f"No data available for {symbol} with timeframe {timeframe}")

        return jsonify({
            'status': 'success',
            'symbol': symbol,
            'timeframe': timeframe,
            'candles': candles,
            'count': len(candles)
        })

    except Exception as e:
        app.logger.error(f"Error fetching candles for {symbol}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'symbol': symbol
        }), 500

# SSE endpoint for real-time candle streaming
@app.route('/api/stream/<symbol>/<timeframe>')
def sse_stream(symbol, timeframe):
    """SSE endpoint - streams candle updates for a symbol/timeframe"""
    room = f"{symbol}_{timeframe}"
    client_id = f"{request.remote_addr}_{id(request)}"
    q = sse_subscribe(room, client_id)

    # Send current candle immediately
    candle = candle_aggregator._get_current_candle(symbol, timeframe)
    if candle:
        try:
            q.put_nowait(candle)
        except queue.Full:
            pass

    def event_stream():
        try:
            while True:
                try:
                    data = q.get(timeout=30)  # 30s timeout for keepalive
                    yield f"data: {json.dumps(data)}\n\n"
                except queue.Empty:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        except GeneratorExit:
            pass
        finally:
            sse_unsubscribe(room, client_id)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


# WebSocket events for real-time candle streaming
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    app.logger.info(f"Client connected: {request.sid}")
    emit('connected', {'message': 'Connected to candle stream'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    app.logger.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe')
def handle_subscribe(data):
    """Subscribe to candle updates for a symbol"""
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1m')

    if symbol:
        # Join room for this symbol-timeframe combination
        room = f"{symbol}_{timeframe}"
        join_room(room)

        app.logger.info(f"Client {request.sid} subscribed to {room}")

        # Send current candle immediately
        candle = candle_aggregator._get_current_candle(symbol, timeframe)
        if candle:
            emit('candle_update', {
                'symbol': symbol,
                'timeframe': timeframe,
                'candle': candle
            })

@socketio.on('unsubscribe')
def handle_unsubscribe(data):
    """Unsubscribe from candle updates"""
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', '1m')

    if symbol:
        room = f"{symbol}_{timeframe}"
        leave_room(room)
        app.logger.info(f"Client {request.sid} unsubscribed from {room}")

def broadcast_candle_update(symbol, timeframe, candle):
    """Broadcast candle update to subscribed clients"""
    room = f"{symbol}_{timeframe}"
    socketio.emit('candle_update', {
        'symbol': symbol,
        'timeframe': timeframe,
        'candle': candle
    }, room=room)

if __name__ == '__main__':
    # Start candle aggregator
    candle_aggregator.start()
    app.logger.info("=" * 60)
    app.logger.info("OpenQuest Started - Real-Time Data Aggregation")
    app.logger.info("Dashboard: http://127.0.0.1:5001")
    app.logger.info("Charts: http://127.0.0.1:5001/chart")
    app.logger.info("=" * 60)

    # Run with SocketIO in production mode with logging
    socketio.run(
        app,
        debug=False,  # Disable debug mode for production
        port=5001,
        host='127.0.0.1',
        use_reloader=False,  # Disable auto-reloader
        log_output=True  # Enable logging output
    )