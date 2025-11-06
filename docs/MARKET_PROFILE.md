# NIFTY Options OI Market Profile

## Overview

The Market Profile feature provides a comprehensive view of Options Open Interest (OI) for F&O instruments, combining:
- **Futures price action** (5-minute candles over 7 days)
- **Current OI levels** by strike price
- **Daily OI changes** to track institutional flow

This tool helps traders identify support/resistance levels, gauge market sentiment, and track where institutional money is flowing.

## Features

### Dynamic Symbol Support
- **Indices**: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY (all expiries)
- **Stocks**: RELIANCE, TCS, INFY, etc. (monthly expiries only)
- Automatic expiry filtering based on symbol type

### Real-Time Intelligence
- **ATM Calculation**: Dynamically calculated At-The-Money strike
- **PCR (Put-Call Ratio)**: Market sentiment indicator
- **OI Buildup/Unwinding**: Track position changes
- **Auto-refresh**: Optional 5-minute automatic data refresh

### Visual Components
1. **Futures Chart** (Column 1 - 50% width)
   - 5-minute candlestick chart
   - 7 days of historical data
   - Volume overlay
   - Interactive hover details

2. **Current OI Levels** (Column 2 - 25% width)
   - Call options extend right (green)
   - Put options extend left (red)
   - ATM strike highlighted in yellow
   - Bar width proportional to OI magnitude

3. **Daily OI Changes** (Column 3 - 25% width)
   - Green bars = OI increase
   - Red bars = OI decrease
   - Shows net daily flow
   - Helps identify institutional positioning

## Getting Started

### Prerequisites

1. **QuestDB** running at `http://127.0.0.1:9000`
2. **OpenAlgo** configured with API key
3. **OpenQuest** application running

### Accessing Market Profile

1. Navigate to: `http://127.0.0.1:5001/market-profile`
2. Select a symbol (e.g., NIFTY)
3. Select an expiry date
4. Click "Fetch OI Data"

### First Time Setup

The first time you fetch data for a symbol/expiry:
1. The system will call OpenAlgo to fetch option chain data (±20 strikes from ATM)
2. Data is stored in QuestDB for future retrieval
3. Subsequent fetches are faster as data is cached

## Using Market Profile

### Step-by-Step Workflow

1. **Select Symbol**
   - Choose from indices or stocks
   - Expiries automatically load based on selection

2. **Select Expiry**
   - Indices: See all weekly + monthly expiries
   - Stocks: See only monthly expiries

3. **Fetch Data**
   - Click "Fetch OI Data" button
   - System fetches from OpenAlgo and stores in database
   - Wait for data to load (usually 10-30 seconds)

4. **Analyze Market Profile**
   - **Futures Chart**: See price action and trends
   - **OI Levels**: Identify support (high PE OI) and resistance (high CE OI)
   - **OI Changes**: Track where new money is flowing

5. **Enable Auto-Refresh** (Optional)
   - Toggle "Auto-refresh (5m)" to automatically update every 5 minutes
   - Useful during market hours for live monitoring

### Reading the Data

#### Current OI Levels
- **Large PE OI** = Potential support level (buyers protecting downside)
- **Large CE OI** = Potential resistance level (sellers capping upside)
- **ATM Strike** (yellow) = Current market equilibrium

#### Daily OI Changes
- **CE OI Increase** = Fresh call writing (bearish) or call buying (bullish)
- **PE OI Increase** = Fresh put writing (bullish) or put buying (bearish)
- **CE OI Decrease** = Call unwinding
- **PE OI Decrease** = Put unwinding

#### OI Buildup Analysis

| Scenario | OI | Price | Interpretation |
|----------|-----|-------|----------------|
| Long Buildup | ↑ | ↑ | Bullish (buyers accumulating) |
| Short Buildup | ↑ | ↓ | Bearish (sellers accumulating) |
| Short Covering | ↓ | ↑ | Bullish (shorts covering) |
| Long Unwinding | ↓ | ↓ | Bearish (longs exiting) |

#### Put-Call Ratio (PCR)
- **PCR > 1.2**: Bullish (more puts than calls)
- **PCR 0.8 - 1.2**: Neutral
- **PCR < 0.8**: Bearish (more calls than puts)

## API Endpoints

### Get F&O Symbols
```
GET /api/fo-symbols
```
Returns list of available indices and stocks

### Get Expiry Dates
```
GET /api/expiry/<symbol>
```
Returns available expiry dates for symbol

### Get ATM Strike
```
GET /api/atm/<symbol>
```
Returns current ATM strike and underlying price

### Get Market Profile
```
GET /api/market-profile/<symbol>?expiry=<expiry>
```
Returns complete market profile data:
- Futures candles
- OI levels
- OI changes
- PCR and other metrics

### Fetch OI Data
```
GET /api/fetch-oi/<symbol>?expiry=<expiry>
```
Triggers fresh OI data fetch from OpenAlgo

### Start/Stop Periodic Fetch
```
POST /api/start-oi-fetch/<symbol>
Body: { "expiry": "28-NOV-25", "interval": 300 }

POST /api/stop-oi-fetch/<symbol>
Body: { "expiry": "28-NOV-25" }
```
Start or stop background OI fetching

## Data Storage

### QuestDB Tables

#### options_oi
Stores current OI levels:
- timestamp, symbol, exchange, expiry, strike, option_type
- oi, oi_change, volume, ltp, bid, ask, iv

#### options_oi_snapshot
Stores daily snapshots (start and end of day):
- snapshot_date, symbol, expiry, strike, option_type
- oi_start_of_day, oi_end_of_day

#### underlying_quotes
Stores spot/index prices:
- timestamp, symbol, exchange, ltp, high, low, open, close

### Data Retention
- OI data: Partitioned by day
- Snapshots: Partitioned by month
- Automatic cleanup can be configured

## Troubleshooting

### No Data Showing
1. **Check OpenAlgo connection**: Ensure API key is valid
2. **Verify market hours**: Data fetches only work during trading hours (9:15 AM - 3:30 PM IST)
3. **Check symbol**: Ensure symbol has active options contracts
4. **Wait for fetch**: First fetch takes 10-30 seconds

### Expiry Dates Not Loading
1. **Check OpenAlgo API**: Verify `/api/v1/expiry` endpoint works
2. **Network issues**: Check connectivity to OpenAlgo
3. **Symbol format**: Ensure using correct symbol format

### Rate Limiting
OpenAlgo has a default rate limit of **10 requests/second**:
- The system automatically throttles to 8 req/sec
- For ±20 strikes, fetching ~40 options takes about 5 seconds
- If rate limited, the system will automatically slow down

### Chart Not Rendering
1. **Check futures data**: Ensure LTP stream is enabled in main dashboard
2. **Database connection**: Verify QuestDB is running
3. **Browser console**: Check for JavaScript errors

## Advanced Usage

### Batch Processing
Fetch multiple symbols/expiries:
```python
from openalgo_oi_fetcher import OpenAlgoOIFetcher

symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
for symbol in symbols:
    expiry = symbol_manager.get_next_expiry(symbol)
    oi_fetcher.fetch_option_chain(symbol, expiry, atm)
```

### Custom Analysis
Query OI data directly from QuestDB:
```sql
-- Get strikes with highest CE OI
SELECT strike, oi, volume
FROM options_oi
WHERE symbol = 'NIFTY'
  AND expiry = '28-NOV-25'
  AND option_type = 'CE'
ORDER BY oi DESC
LIMIT 10;

-- Calculate OI buildup
SELECT strike,
       SUM(oi) as total_oi,
       COUNT(*) as records
FROM options_oi
WHERE symbol = 'NIFTY'
  AND timestamp >= dateadd('d', -1, now())
GROUP BY strike
ORDER BY total_oi DESC;
```

### Export Data
Export to CSV for external analysis:
```python
import pandas as pd

# Get OI data
oi_data = questdb_client.get_oi_for_expiry('NIFTY', '28-NOV-25')

# Convert to DataFrame
df = pd.DataFrame(oi_data)
df.to_csv('nifty_oi.csv', index=False)
```

## Performance Tips

1. **Enable Auto-refresh** only when needed
2. **Limit strike range** for faster fetches (modify in config)
3. **Use caching** - fetch data once, analyze multiple times
4. **Schedule fetches** outside peak trading times for historical analysis

## Configuration

Edit `/home/user/openquest/config/fo_symbols.json` to add/remove symbols:
```json
{
  "indices": ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"],
  "stocks": ["RELIANCE", "TCS", "INFY", ...]
}
```

Modify strike intervals in `symbol_manager.py`:
```python
def get_strike_interval(self, symbol: str) -> int:
    intervals = {
        'NIFTY': 50,  # Change from 50 to 100 for wider range
        'BANKNIFTY': 100,
        ...
    }
```

## Support & Contributing

- **Issues**: Report at https://github.com/marketcalls/openquest/issues
- **Documentation**: https://docs.openalgo.in
- **Community**: Join the OpenAlgo community for discussions

---

**Built with ❤️ for traders who want to understand market structure**
