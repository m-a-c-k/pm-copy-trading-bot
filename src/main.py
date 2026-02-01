"""
PM Copy Trading Bot - Configuration Check

Quick validation that all services load correctly.
"""

import sys
from dotenv import load_dotenv

load_dotenv()

try:
    from src.config.config import Config
    from src.services.kelly_calculator import KellyCalculator
    from src.services.risk_manager import RiskManager
    from src.services.trade_executor import TradeExecutor, ExecutorConfig

    config = Config.load()
    valid, errors = config.validate()

    if not valid:
        print("❌ Configuration Errors:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)

    print("=" * 60)
    print("PM COPY TRADING BOT")
    print("=" * 60)
    print()
    print(f"✅ All services loaded successfully")
    print(f"   Wallet: {config.blockchain.proxy_wallet[:16]}...")
    print(f"   Bankroll: ${config.kelly.bankroll}")
    print(f"   Kelly: {config.kelly.kelly_fraction}x")
    print(f"   Traders: {len(config.copy_trading.user_addresses)}")
    print()
    print("🚀 Ready to trade!")
    print()
    print("Commands:")
    print("   python3 monitor_whale.py    # Monitor FollowMeABC123")
    print("   python3 test_clob.py        # Test order placement")
    print("=" * 60)

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
