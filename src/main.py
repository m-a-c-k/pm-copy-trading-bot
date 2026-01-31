"""
PM Copy Trading Bot - Main Entry Point

A copy trading bot for Polymarket prediction markets with:
- Kelly Criterion position sizing
- Perfect Money integration
- Smart trader discovery
- Risk management
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

from src.config.config import Config
from src.services.kelly_calculator import KellyCalculator
from src.services.perfect_money_bridge import PerfectMoneyBridge
from src.services.trader_discovery import TraderDiscovery
from src.services.risk_manager import RiskManager
from src.services.trade_monitor import TradeMonitor, MonitorConfig
from src.services.trade_executor import TradeExecutor, ExecutorConfig


async def main():
    """Main entry point."""
    print("=" * 60)
    print("PM Copy Trading Bot")
    print("=" * 60)
    
    # Load configuration
    load_dotenv()
    config = Config.load()
    
    # Validate configuration
    valid, errors = config.validate()
    if not valid:
        print("❌ Configuration Errors:")
        for e in errors:
            print(f"   - {e}")
        print("\nPlease copy .env.example to .env and fill in your values.")
        sys.exit(1)
    
    print(f"\n✅ Configuration loaded")
    print(f"   Wallet: {config.blockchain.proxy_wallet[:8]}...")
    print(f"   Bankroll: ${config.kelly.bankroll}")
    print(f"   Kelly: {config.kelly.kelly_fraction}x")
    print(f"   Traders: {len(config.copy_trading.user_addresses)}")
    
    # Initialize services
    print("\n🔧 Initializing services...")
    
    kelly = KellyCalculator(
        kelly_fraction=config.kelly.kelly_fraction,
        max_trade_percent=config.kelly.max_trade_percent,
        max_trader_exposure=config.kelly.max_trader_exposure,
        bankroll=config.kelly.bankroll
    )
    print("   ✅ Kelly Calculator")
    
    risk = RiskManager(
        max_trade_percent=config.kelly.max_trade_percent,
        max_trader_exposure=config.kelly.max_trader_exposure,
        bankroll=config.kelly.bankroll
    )
    print("   ✅ Risk Manager")
    
    pm = PerfectMoneyBridge()
    print("   ✅ Perfect Money Bridge")
    
    discovery = TraderDiscovery()
    print("   ✅ Trader Discovery")
    
    executor = TradeExecutor(
        config=ExecutorConfig(
            rpc_url=config.blockchain.rpc_url,
            wallet_address=config.blockchain.proxy_wallet,
            private_key=config.blockchain.private_key
        )
    )
    print("   ✅ Trade Executor")
    
    # Trade callback
    async def on_trade(trade):
        print(f"\n📊 New Trade from {trade.trader_wallet[:8]}...")
        print(f"   {trade.side} {trade.size} @ ${trade.price}")
        
        # Calculate position size
        kelly_result = kelly.calculate_kelly(
            win_rate=0.60,  # Would get from trader stats
            win_loss_ratio=1.5,
            trader_size=trade.size
        )
        
        # Check risk
        risk_result = risk.check_position(
            trader_wallet=trade.trader_wallet,
            proposed_size=kelly_result.recommended_position_size
        )
        
        if risk_result.approved:
            print(f"   ✅ Approved: ${risk_result.final_position_size:.2f}")
            
            result = await executor.execute_copy_trade(
                trader_wallet=trade.trader_wallet,
                token_id=trade.token_id,
                side=trade.side,
                trader_size=trade.size,
                trader_price=trade.price,
                my_position_size=risk_result.final_position_size,
                kelly_fraction=config.kelly.kelly_fraction
            )
            
            if result.success:
                print(f"   ✅ Executed: {result.order_id}")
                risk.add_trader_exposure(trade.trader_wallet, result.size)
            else:
                print(f"   ❌ Error: {result.error}")
        else:
            print(f"   ❌ Rejected: {risk_result.warnings}")
    
    monitor = TradeMonitor(
        config=MonitorConfig(
            user_addresses=config.copy_trading.user_addresses,
            fetch_interval=config.copy_trading.fetch_interval,
            copy_delay_seconds=config.copy_trading.copy_delay_seconds
        ),
        on_trade=on_trade
    )
    print("   ✅ Trade Monitor")
    
    print("\n" + "=" * 60)
    print("🚀 Bot Started - Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        await monitor.run_loop()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping bot...")
    finally:
        await monitor.close()
        await discovery.close()
        print("✅ Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
