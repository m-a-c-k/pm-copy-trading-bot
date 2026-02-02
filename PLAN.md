# Kalshi Copy Trading Bot - Session Plan

## What Was Built

### Core Architecture
- **Bot Location:** `/home/mck/Desktop/projects/pm-copy-trading-bot`
- **Purpose:** Monitor Polymarket whales and copy trades to Kalshi

### Key Files
```
pm-copy-trading-bot/
├── run_kalshi_copy.py            # Main bot entry point ⭐ RUN THIS
├── src/
│   ├── config/
│   │   ├── config.py             # Environment config loader
│   │   └── traders.py            # Trader configurations
│   └── services/
│       ├── kalshi_client.py      # Kalshi API wrapper
│       ├── kalshi_executor.py    # Trade execution
│       ├── market_matcher.py     # PM → Kalshi market matching
│       ├── kelly_calculator.py   # Kelly Criterion sizing
│       └── risk_manager.py       # Risk limits
├── kalshi_key.pem                # RSA private key for Kalshi
└── .env                          # Credentials
```

### Monitored Traders
| Address | Name | Notes |
|---------|------|-------|
| 0xc257... | FollowMeABC123 | Original whale |
| 0xaa07... | rustin | +$207K profit |
| 0x3b5c... | SMCAOMCRL | +$86K profit, high volume |
| 0xafba... | NewTrader | Sports trader |

## Position Sizing (Kelly Criterion)
- Bankroll: Dynamically fetched from Kalshi balance
- Kelly Fraction: 0.5x (conservative)
- Max per trade: 2% of bankroll
- Max per market: 1 position

## Current Status

| Item | Status |
|------|--------|
| Multi-trader monitoring | ✅ Working |
| Dynamic bankroll fetch | ✅ Working |
| Market matching | ✅ Working |
| Live trading | ✅ Running |

## Commands Reference

```bash
# Run in live mode (recommended)
python3 run_kalshi_copy.py --live

# Run in dry-run mode (testing)
python3 run_kalshi_copy.py --dry-run

# Check status
python3 run_kalshi_copy.py --status

# Run in screen session
screen -S kalshi_copy_bot
python3 run_kalshi_copy.py --live
# Ctrl+A D to detach

# Attach to running session
screen -r kalshi_copy_bot
```

## Configuration (.env)

```bash
KALSHI_API_KEY_ID=your_key
KALSHI_PRIVATE_KEY_PEM=/path/to/kalshi_key.pem
COPY_TO_KALSHI=true
KALSHI_KELLY_FRACTION=0.5
KALSHI_MAX_TRADE_PERCENT=2.0
```

## GitHub
- **Repo:** https://github.com/m-a-c-k/pm-copy-trading-bot
