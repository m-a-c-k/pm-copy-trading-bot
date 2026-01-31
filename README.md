# PM Copy Trading Bot

Automated copy trading bot for Polymarket prediction markets with Perfect Money integration.

## Features

- 📊 **Kelly Criterion Position Sizing** - Smart position sizing based on win rate and risk
- 💰 **Perfect Money Integration** - Bridge between PM and Polymarket wallet
- 🔍 **Trader Discovery** - Find and evaluate top traders to copy
- 🛡️ **Risk Management** - 2% per trade, 10% per trader, 30% total exposure limits
- ⚡ **Real-time Monitoring** - Watch trader wallets and copy trades automatically

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run
```bash
python -m src.main
```

## Configuration

| Variable | Description |
|----------|-------------|
| `ALCHEMY_API_KEY` | Alchemy API key for Polygon RPC |
| `PROXY_WALLET` | Your Polygon wallet address |
| `PRIVATE_KEY` | Wallet private key (without 0x) |
| `BANKROLL` | Initial bankroll (default: 400) |
| `KELLY_FRACTION` | Kelly fraction (0.5 = moderate) |
| `USER_ADDRESSES` | Traders to copy (comma-separated) |

## Architecture

```
src/
├── config/
│   └── config.py          # Configuration loader
├── services/
│   ├── kelly_calculator.py    # Position sizing
│   ├── perfect_money_bridge.py # PM integration
│   ├── trader_discovery.py    # Trader evaluation
│   ├── risk_manager.py        # Risk controls
│   ├── trade_monitor.py       # Wallet watching
│   └── trade_executor.py      # Order execution
└── main.py                 # Entry point
```

## Risk Settings

- Max per trade: 2% of bankroll
- Max per trader: 10% of bankroll
- Max total exposure: 30% of bankroll
- Kelly fraction: 0.5x (moderate)

For $400 bankroll: max $8 per trade, $40 per trader

## Testing

```bash
python -m pytest tests/ -v
```

All 30 unit tests passing.

## License

MIT
