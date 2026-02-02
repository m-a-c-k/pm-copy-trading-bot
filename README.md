# PM Copy Trading Bot

Automated copy trading bot for Polymarket with Kalshi copy mode.

## Two Copy Modes

| Mode | Copy From → Copy To | Status |
|------|-------------------|--------|
| **PM Copy Mode** | Whale → Polymarket | Needs VPN |
| **Kalshi Copy Mode** | Whale → Kalshi | Works now! ✅ |

## Kalshi Copy Mode (Recommended)

Copy Polymarket whale trades to Kalshi prediction markets.

### Features

- 📊 **Kelly Criterion Sizing** - Match whale's % of bankroll
- 🎯 **Market Matching** - PM ↔ Kalshi with fuzzy team matching
- 📈 **All Market Types** - Moneyline, Spreads, Totals
- 🛡️ **Position Limits** - Max 1 position per market
- 👥 **Multi-Trader Support** - Monitor and copy 4 top traders
- 💰 **Dynamic Bankroll** - Auto-fetches from Kalshi balance

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install --user kalshi_python py_clob_client --break-system-packages

# Configure (add to .env)
KALSHI_API_KEY_ID=your_key
KALSHI_PRIVATE_KEY_PEM=/path/to/kalshi_private_key.pem
COPY_TO_KALSHI=true
KALSHI_BANKROLL=100

# Test
python3 run_kalshi_copy.py --test

# Run (dry-run)
python3 run_kalshi_copy.py --dry-run

# Run (live)
python3 run_kalshi_copy.py --live
```

### Commands

| Command | Description |
|---------|-------------|
| `--status` | Show balance, whale stats |
| `--test` | Run integration test |
| `--dry-run` | Monitor & log, no trades |
| `--live` | Execute real trades |

### Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `KALSHI_API_KEY_ID` | Kalshi API key | required |
| `KALSHI_PRIVATE_KEY_PEM` | Path to RSA key | required |
| `COPY_TO_KALSHI` | Enable copy mode | false |
| `KALSHI_KELLY_FRACTION` | Kelly multiplier | 0.5 |
| `KALSHI_MAX_TRADE_PERCENT` | Max % per trade | 2.0 |
| `MAX_POSITIONS_PER_MARKET` | Max bets/game | 1 |
| `MAX_SAME_SIDE_PER_MARKET` | Max same-side bets | 1 |

> **Note:** Bankroll is automatically fetched from your Kalshi balance.

## PM Copy Mode (Original)

Copy whale trades to Polymarket. Requires VPN for Polygon access.

```bash
python3 monitor_whale.py
```

## Architecture

```
src/services/
├── kalshi_client.py      # Kalshi API wrapper
├── market_matcher.py     # PM → Kalshi market matching
├── kalshi_executor.py    # Trade execution with position limits
├── team_mappings.py      # Team name aliases (100+ teams)
├── kelly_calculator.py   # Kelly Criterion sizing
├── risk_manager.py       # Exposure limits
└── trade_executor.py     # Polymarket execution
```

## Coverage

| Sport | Kalshi Games | Market Types |
|-------|-------------|--------------|
| CBB | 36+ | ML, Spread, Totals |
| NBA | 16+ | ML, Spread, Totals |
| NFL | 1+ | Totals (more during season) |

## Risk Settings

- Max per trade: 2% of bankroll
- Max per market: 1 position
- Max same-side: 1 bet
- Kelly fraction: 0.5x (moderate)

For $100 bankroll: max $2 per trade

## Testing

```bash
# Core tests
python3 -m pytest tests/test_kelly_calculator.py tests/test_risk_manager.py -v

# Integration test
python3 run_kalshi_copy.py --test
```

## License

MIT
