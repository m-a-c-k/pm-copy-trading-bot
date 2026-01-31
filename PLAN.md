# Polymarket Copy Trading Bot - Session Plan

## What Was Built

### Core Architecture
- **Bot Location:** `/Users/alexandrastarnes/Documents/mack/github/pm-copy-trading-bot/`
- **Purpose:** Monitor trader `FollowMeABC123` and copy trades proportionally

### Key Files
```
pm-copy-trading-bot/
├── src/
│   ├── config/config.py              # Environment config loader
│   └── services/
│       ├── kelly_calculator.py       # Kelly Criterion sizing
│       ├── perfect_money_bridge.py   # PM integration (unused)
│       ├── trader_discovery.py       # Find/copy traders
│       ├── risk_manager.py           # Risk limits (2% per trade, 10% per trader)
│       ├── trade_monitor.py          # Monitor trader wallets
│       ├── trade_executor.py         # CLOB order placement ⭐ FIXED
│       ├── clob_client.py            # Polymarket CLOB API client
│       ├── position_scaler.py        # Proportional sizing
│       └── whale_scaler.py           # Whale-aware scaling
├── monitor_whale.py                  # Active whale monitoring script ⭐ RUN THIS
├── test_clob.py                      # Test CLOB order placement
├── .env                              # Credentials
└── requirements.txt
```

### Credentials (in .env)
```
PROXY_WALLET=0x3854c129cd856ee518bf0661792e01ef1f2f586a
PRIVATE_KEY=911b44fec3bb4360e2288db5810a2cbceb4725465c438802083cb1ebf01b6d73
ALCHEMY_API_KEY=5K6CVc1EkJsLj9TLjktjs
POLYMARKET_API_KEY=019c1644-035a-78fe-9e0b-d7781eada06c
POLYMARKET_SECRET_KEY=xOsBVtdl11EfwMa3yTa3V2uQ2IPLX3dY5u0MVGiY_Z8=
POLYMARKET_PASSPHRASE=c462b805e329736e1c6677d3c87bca95c4fee903839bdfe652b54fcfb26d5293
BANKROLL=433
```

### The Whale (FollowMeABC123)
- **Address:** `0xc257ea7e3a81ca8e16df8935d44d513959fa358e`
- **Positions Value:** $1,500,000
- **All-time Profit:** $1,181,829
- **Avg Bet:** ~$100
- **Strategy:** Small bets, high frequency

### Position Sizing (Proportional)
| Their Bet | Our Copy | % of Bank |
|-----------|----------|-----------|
| $25 | $2.17 | 0.5% |
| $100 | $8.66 | 2% |
| $500 | $43.30 | 10% |
| $1,000+ | $64.95 | 15% cap |

## What Was Fixed

### trade_executor.py
- ✅ Proper EIP-712 signing implementation
- ✅ Alchemy RPC connection (Connected: `True`)
- ✅ Nonce retrieval from CLOB API
- ✅ Order signing with domain separator
- ✅ Cloudflare headers (User-Agent, Origin, Referer)

## Current Status

| Item | Status |
|------|--------|
| Monitoring | ✅ Ready |
| Position Sizing | ✅ Working |
| Order Signing | ✅ Fixed |
| Actual Order Placement | ⚠️ Needs non-US VPN |

## Next Steps (Priority)

### 1. Test Order Placement (HIGH)
Connect through non-US VPN and run:
```bash
cd /Users/alexandrastarnes/Documents/mack/github/pm-copy-trading-bot
python3 test_clob.py
```

Expected output:
```
✅ Order placed successfully!
```

### 2. Start Monitoring (MEDIUM)
```bash
cd /Users/alexandrastarnes/Documents/mack/github/pm-copy-trading-bot
python3 monitor_whale.py
```

This will:
- Show current bankroll and sizing table
- Poll FollowMeABC123's trades every 3 seconds
- Alert when they trade with copy recommendation

### 3. Manual Testing (Optional)
Place a small $1-5 trade on polymarket.com manually to:
- Verify wallet works
- Check USDC balance
- Test the full flow

## Commands Reference

```bash
# Test CLOB order placement
python3 test_clob.py

# Start monitoring FollowMeABC123
python3 monitor_whale.py

# Check dependencies
pip install -r requirements.txt

# View recent trades from whale
curl "https://data-api.polymarket.com/activity?user=0xc257ea7e3a81ca8e16df8935d44d513959fa358e"
```

## If Issues Arise

### "Module not found: services"
Run from project root with PYTHONPATH:
```bash
PYTHONPATH=/Users/alexandrastarnes/Documents/mack/github/pm-copy-trading-bot python3 test_clob.py
```

### "Cloudflare blocked" or 403
VPN is not connected or using US IP. Connect non-US VPN.

### "Connection refused" or "API error"
Check API key in `.env` is correct.

## GitHub
- **Repo:** https://github.com/m-a-c-k/pm-copy-trading-bot
- **Commits:** 8 (all pushed)
