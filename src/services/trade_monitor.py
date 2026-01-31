"""
Trade Monitor Module for PM Copy Trading Bot

Monitors trader wallets for new trades on Polymarket and triggers copy actions.
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable
import httpx
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TradeEvent:
    """Detected trade event."""
    trader_wallet: str
    condition_id: str
    token_id: str
    side: str  # "BUY" or "SELL"
    size: float
    price: float
    timestamp: datetime
    raw_data: dict
    
    def to_dict(self) -> dict:
        return {
            "trader_wallet": self.trader_wallet,
            "condition_id": self.condition_id,
            "token_id": self.token_id,
            "side": self.side,
            "size": self.size,
            "price": self.price,
            "timestamp": self.timestamp.isoformat(),
            "raw_data": self.raw_data
        }


@dataclass
class MonitorConfig:
    """Trade monitor configuration."""
    user_addresses: list[str]
    fetch_interval: int = 1
    copy_delay_seconds: float = 2.0
    api_url: str = "https://api.polymarket.com"


class TradeMonitor:
    """Monitors trader wallets for new trades."""
    
    def __init__(self, config: MonitorConfig, on_trade: Optional[Callable[[TradeEvent], None]] = None):
        """
        Initialize trade monitor.
        
        Args:
            config: Monitor configuration
            on_trade: Callback function when trade is detected
        """
        self.config = config
        self.on_trade = on_trade
        self.session = httpx.AsyncClient(timeout=30.0)
        self.running = False
        self.last_trades: dict[str, dict] = {}  # wallet -> last trade hash
        self._task: Optional[asyncio.Task] = None
    
    async def close(self):
        """Close HTTP session."""
        self.running = False
        if self._task:
            self._task.cancel()
        await self.session.aclose()
    
    async def fetch_user_activity(self, wallet_address: str) -> list[dict]:
        """Fetch recent activity for a wallet."""
        try:
            response = await self.session.get(
                f"{self.config.api_url}/api/core/users/{wallet_address}/activity",
                params={"limit": 20, "type": "TRADE"}
            )
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    def is_new_trade(self, wallet: str, trade: dict) -> bool:
        """Check if this is a new trade we haven't seen."""
        tx_hash = trade.get("transactionHash", "")
        if not tx_hash:
            return False
        
        last_hash = self.last_trades.get(wallet, {}).get(tx_hash)
        if last_hash:
            return False
        
        self.last_trades[wallet] = {"latest": tx_hash}
        return True
    
    def parse_trade(self, wallet: str, data: dict) -> Optional[TradeEvent]:
        """Parse raw trade data into TradeEvent."""
        try:
            return TradeEvent(
                trader_wallet=wallet,
                condition_id=data.get("conditionId", ""),
                token_id=data.get("asset", ""),
                side=data.get("side", "").upper(),
                size=float(data.get("size", 0)),
                price=float(data.get("price", 0)),
                timestamp=datetime.fromtimestamp(data.get("timestamp", time.time())),
                raw_data=data
            )
        except Exception:
            return None
    
    async def check_wallet(self, wallet: str) -> list[TradeEvent]:
        """Check a single wallet for new trades."""
        new_trades = []
        activities = await self.fetch_user_activity(wallet)
        
        for activity in activities:
            if self.is_new_trade(wallet, activity):
                trade = self.parse_trade(wallet, activity)
                if trade:
                    new_trades.append(trade)
        
        return new_trades
    
    async def scan_all_wallets(self) -> dict[str, list[TradeEvent]]:
        """Scan all monitored wallets for new trades."""
        all_new_trades = {}
        
        for wallet in self.config.user_addresses:
            trades = await self.check_wallet(wallet)
            if trades:
                all_new_trades[wallet] = trades
        
        return all_new_trades
    
    async def run_once(self) -> dict[str, list[TradeEvent]]:
        """Run one scan cycle."""
        return await self.scan_all_wallets()
    
    async def run_loop(self, callback: Optional[Callable[[str, list[TradeEvent]], None]] = None):
        """
        Run continuous monitoring loop.
        
        Args:
            callback: Optional callback(wallet, trades) for each wallet with new trades
        """
        self.running = True
        print(f"🔍 Starting trade monitor for {len(self.config.user_addresses)} wallets...")
        
        while self.running:
            try:
                new_trades = await self.scan_all_wallets()
                
                for wallet, trades in new_trades.items():
                    print(f"📊 Detected {len(trades)} new trade(s) from {wallet[:8]}...")
                    
                    for trade in trades:
                        print(f"   {trade.side} {trade.size} @ ${trade.price}")
                        if self.on_trade:
                            self.on_trade(trade)
                    
                    if callback:
                        callback(wallet, trades)
                
                await asyncio.sleep(self.config.fetch_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(5)
    
    def start(self, callback: Optional[Callable[[str, list[TradeEvent]], None]] = None):
        """Start monitoring in background task."""
        self._task = asyncio.create_task(self.run_loop(callback))
        return self._task
    
    def stop(self):
        """Stop monitoring."""
        self.running = False


# Quick test when run directly
if __name__ == "__main__":
    async def test():
        print("Trade Monitor Test")
        print("=" * 50)
        
        config = MonitorConfig(
            user_addresses=[
                "0x3854c129cd856ee518bf0661792e01ef1f2f586a",  # Your wallet
            ],
            fetch_interval=1
        )
        
        monitor = TradeMonitor(config)
        
        # Run single scan
        print("\nScanning for trades...")
        trades = await monitor.run_once()
        
        if trades:
            for wallet, wallet_trades in trades.items():
                print(f"\nWallet {wallet[:8]}:")
                for t in wallet_trades:
                    print(f"  {t.side} {t.size} @ ${t.price}")
        else:
            print("No new trades detected (or API not accessible)")
        
        await monitor.close()
    
    asyncio.run(test())
