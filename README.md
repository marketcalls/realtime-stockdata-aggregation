# OpenQuest - Real-Time Stock Data Aggregation Platform

[![GitHub](https://img.shields.io/badge/GitHub-OpenQuest-blue)](https://github.com/marketcalls/openquest)
[![License](https://img.shields.io/badge/License-AGPL--3.0-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![QuestDB](https://img.shields.io/badge/QuestDB-Time--Series-orange)](https://questdb.io/)
[![OpenAlgo](https://img.shields.io/badge/OpenAlgo-Compatible-purple)](https://github.com/marketcalls/openalgo)

OpenQuest is a high-performance, zero-configuration real-time data aggregation tool designed for OpenAlgo. It seamlessly streams tick data from all OpenAlgo-supported exchanges (NSE, BSE, NFO, BFO, BCD, MCX) into QuestDB and provides professional-grade TradingView charts with proper IST timezone support.

## 🚀 Features

- **Zero Configuration**: Configure everything through the intuitive web UI
- **Real-Time Streaming**: High-frequency LTP, Quote, and Depth data streams
- **Multi-Exchange Support**: Automatic aggregation for NSE, BSE, NFO, BFO, BCD, and MCX symbols
- **Professional Charts**: TradingView Lightweight Charts with IST timezone display and day stats (OHLC, Volume, Change %)
- **📊 Options Market Profile** *(NEW)*: Advanced OI analysis for F&O instruments
  - Dynamic symbol/expiry selection for NIFTY, BANKNIFTY, FINNIFTY, and F&O stocks
  - Real-time Open Interest tracking with ±20 strikes from ATM
  - Daily OI changes to identify institutional flow
  - Three-column layout: Futures Chart + Current OI + OI Changes
  - Support/Resistance levels from OI concentrations
  - Put-Call Ratio (PCR) calculation
  - Auto-refresh every 5 minutes during market hours
- **Time-Series Database**: QuestDB for ultra-fast tick data storage and retrieval
- **Modern UI**: Supabase green/black theme with TailwindCSS and DaisyUI
- **Live Metrics**: Real-time monitoring of tick rates, spreads, and connection status
- **Multi-Timeframe**: Support for 1m, 5m, 15m, 30m, 1h, and 1d candle aggregation
- **Efficient Storage**: Optimized database schema for tick-level and aggregated data

## 📋 Prerequisites

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **QuestDB** - Running at `http://127.0.0.1:9000`
- **OpenAlgo** - Running at:
  - REST API: `http://127.0.0.1:5000`
  - WebSocket: `ws://127.0.0.1:8765`

## 🛠️ Installation

### Quick Install (Recommended)

**Linux / macOS:**
```bash
git clone https://github.com/marketcalls/openquest.git
cd openquest
chmod +x install.sh
./install.sh
```

**Windows:**
```batch
git clone https://github.com/marketcalls/openquest.git
cd openquest
install.bat
```

The installation script will:
- Create a Python virtual environment
- Install all dependencies
- Set up necessary directories
- Verify QuestDB connection

📖 **Detailed Guide**: See [INSTALLATION.md](INSTALLATION.md) for complete installation instructions and troubleshooting.

### Manual Installation

If you prefer manual installation:

#### 1. Clone the Repository

```bash
git clone https://github.com/marketcalls/openquest.git
cd openquest
```

#### 2. Create Virtual Environment

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Start QuestDB

If you don't have QuestDB running, start it using Docker:

```bash
docker run -d \
  -p 9000:9000 \
  -p 9009:9009 \
  -p 8812:8812 \
  -p 9003:9003 \
  --name questdb \
  questdb/questdb
```

Or download and run QuestDB directly from [questdb.io](https://questdb.io/get-questdb/).

### 4. Verify OpenAlgo is Running

Ensure OpenAlgo is running and accessible:
- REST API should respond at `http://127.0.0.1:5000/api/v1`
- WebSocket should be available at `ws://127.0.0.1:8765`

## 🚀 Quick Start

### 1. Run the Application

**Using start scripts (recommended):**

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

**Or manually:**

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Start application
python app.py
```

### 2. Access the Dashboard

Open your browser and navigate to:
```
http://127.0.0.1:5001
```

The start script will automatically:
- Activate the virtual environment
- Check if QuestDB is running
- Start OpenQuest
- Display access URLs

### 3. Configure OpenAlgo Connection

1. Enter your **OpenAlgo API Key**
2. Verify the REST API URL (default: `http://127.0.0.1:5000`)
3. Verify the WebSocket URL (default: `ws://127.0.0.1:8765`)
4. Select data streams to enable:
   - **LTP** (Last Traded Price) - Essential for charts
   - **Quote** - Bid/Ask prices and spreads
   - **Depth** - Order book depth (5 levels)
5. Click **"Save Configuration"**

### 4. Start Streaming

Click **"Start Streaming"** to begin real-time data aggregation.

### 5. View Charts

Navigate to the **Charts** tab to view real-time TradingView charts with:
- Multiple timeframes (1m, 5m, 15m, 30m, 1h, 1d)
- IST timezone display
- Symbol selection dropdown
- Professional trading indicators

### 6. Access Market Profile (Options OI Analysis)

Navigate to: `http://127.0.0.1:5001/market-profile`

The Market Profile provides comprehensive Options Open Interest analysis:
1. **Select Symbol**: Choose from NIFTY, BANKNIFTY, FINNIFTY, or F&O stocks
2. **Select Expiry**: Pick from available expiry dates (weekly for indices, monthly for stocks)
3. **Fetch OI Data**: Click to fetch real-time Open Interest from OpenAlgo
4. **Analyze**: View three synchronized panels:
   - **Futures Chart** (5m, 7 days) - Price action context
   - **Current OI Levels** - Support/Resistance from OI clusters
   - **Daily OI Changes** - Institutional flow tracking

📖 **Detailed Guide**: See [Market Profile Documentation](docs/MARKET_PROFILE.md) for complete usage instructions.

## 📊 Database Schema

OpenQuest uses QuestDB with the following optimized schema:

### ticks_ltp
| Column | Type | Description |
|--------|------|-------------|
| timestamp | TIMESTAMP | Time of tick (IST) |
| symbol | SYMBOL | Trading symbol |
| ltp | DOUBLE | Last traded price |
| volume | LONG | Last trade quantity (aggregated for candles) |

### ticks_quote
| Column | Type | Description |
|--------|------|-------------|
| timestamp | TIMESTAMP | Time of quote (IST) |
| symbol | SYMBOL | Trading symbol |
| ltp | DOUBLE | Last traded price |
| open | DOUBLE | Day's opening price |
| high | DOUBLE | Day's highest price |
| low | DOUBLE | Day's lowest price |
| close | DOUBLE | Current/closing price |
| volume | LONG | Total traded volume |
| last_trade_quantity | LONG | Quantity of last trade |
| change | DOUBLE | Price change from open |
| change_percent | DOUBLE | Price change percentage |
| avg_trade_price | DOUBLE | Average trade price |

### ticks_depth
| Column | Type | Description |
|--------|------|-------------|
| timestamp | TIMESTAMP | Time of depth update (IST) |
| symbol | SYMBOL | Trading symbol |
| level | INT | Orderbook level (0-4) |
| bid | DOUBLE | Bid price at level |
| ask | DOUBLE | Ask price at level |
| bid_qty | LONG | Bid quantity |
| ask_qty | LONG | Ask quantity |
| bid_orders | INT | Number of bid orders |
| ask_orders | INT | Number of ask orders |

## 🔌 API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard UI |
| `/chart` | GET | TradingView charts interface |
| `/config` | GET/POST | Configuration management |
| `/metrics` | GET | Real-time streaming metrics |
| `/health` | GET | Application health check |

### Control Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/start_stream` | POST | Start data streaming |
| `/stop_stream` | POST | Stop data streaming |
| `/api/symbols` | GET | Get list of active symbols |
| `/api/candles/<symbol>` | GET | Get historical candles |

### Candles API Parameters

```
GET /api/candles/RELIANCE?timeframe=1m&limit=500
```

- **symbol**: Trading symbol (required) - supports all OpenAlgo exchanges
- **timeframe**: 1m, 5m, 15m, 30m, 1h, 1d (default: 1m)
- **limit**: Number of candles to return (default: 500, max: 1000)

## 🧪 Testing

### Run Test Suite

```bash
cd test
python test_connection.py
```

This will verify:
- QuestDB connection and data storage
- API endpoints availability
- WebSocket streaming status
- Configuration validity

### Manual Testing

1. **Check QuestDB Data**:
```sql
-- Connect to QuestDB at http://127.0.0.1:9000
SELECT * FROM ticks_ltp ORDER BY timestamp DESC LIMIT 10;
```

2. **Verify Streaming**:
```bash
curl http://127.0.0.1:5001/metrics
```

3. **Test Chart Data**:
```bash
curl http://127.0.0.1:5001/api/candles/RELIANCE?timeframe=1m&limit=10
```

## 🎨 UI Features

### Dashboard
- Real-time connection status
- Live tick counter
- Active symbols display
- Streaming control panel
- Configuration interface

### Charts
- TradingView Lightweight Charts v4.1
- IST timezone with proper display
- Multiple timeframe support
- Symbol selection dropdown
- Real-time day statistics (Open, High, Low, Close, LTP, Change, Change %, Volume)
- Volume indicators with actual traded volumes
- Crosshair with price/time display

### Metrics Panel
- Ticks per second
- Total tick count
- Active symbols count
- Spread analysis
- Connection health

## ⚙️ Configuration

### config.json Structure

```json
{
  "api_key": "your-openalgo-api-key",
  "rest_url": "http://127.0.0.1:5000",
  "ws_url": "ws://127.0.0.1:8765",
  "ltp_enabled": true,
  "quote_enabled": true,
  "depth_enabled": false
}
```

### Environment Variables (Optional)

```bash
export QUESTDB_HOST=127.0.0.1
export QUESTDB_PORT=8812
export FLASK_PORT=5001
```

## 🐛 Troubleshooting

### QuestDB Connection Issues

1. **Verify QuestDB is running**:
```bash
curl http://127.0.0.1:9000
```

2. **Check PostgreSQL wire protocol**:
```bash
telnet 127.0.0.1 8812
```

3. **Reset tables if needed**:
```sql
DROP TABLE IF EXISTS ticks_ltp;
DROP TABLE IF EXISTS ticks_quote;
DROP TABLE IF EXISTS ticks_depth;
```

### No Data Flowing

1. **Verify OpenAlgo WebSocket**:
   - Check if OpenAlgo is running
   - Verify API key is correct
   - Ensure market hours (MCX: 9:00 AM - 11:30 PM IST)

2. **Check logs**:
```bash
python app.py  # Check console output for detailed logs
```

3. **Test WebSocket connection**:
```python
import websocket
ws = websocket.WebSocket()
ws.connect("ws://127.0.0.1:8765")
# Should connect without error
```

### Chart Display Issues

1. **Timezone problems**:
   - Charts display in IST automatically
   - Hover tooltip shows correct IST time
   - X-axis labels are formatted for IST

2. **No candles showing**:
   - Ensure LTP stream is enabled
   - Wait for sufficient tick data
   - Check browser console for errors

## 📈 Performance

- **Tick Processing**: ~10,000 ticks/second capability
- **Database Write**: Batch inserts for efficiency
- **Memory Usage**: < 100MB typical
- **CPU Usage**: < 5% during normal operation
- **Latency**: < 10ms from tick to storage
- **Volume Aggregation**: Uses actual `last_trade_quantity` from WebSocket data
- **Price Aggregation**: Based on LTP (Last Traded Price) for accurate OHLC candles

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [OpenAlgo](https://github.com/marketcalls/openalgo) - Algorithmic trading platform
- [QuestDB](https://questdb.io/) - High-performance time-series database
- [TradingView Lightweight Charts](https://www.tradingview.com/lightweight-charts/) - Professional charting library
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [TailwindCSS](https://tailwindcss.com/) & [DaisyUI](https://daisyui.com/) - UI styling

## 📞 Support

For issues and feature requests, please [open an issue](https://github.com/marketcalls/openquest/issues) on GitHub.

For more information about OpenAlgo integration, visit [OpenAlgo Documentation](https://docs.openalgo.in/).

---

**Made with ❤️ by [MarketCalls](https://github.com/marketcalls)**