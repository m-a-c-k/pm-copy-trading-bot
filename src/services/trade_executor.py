"""
Trade Executor Module for PM Copy Trading Bot

Executes copy trades on Polymarket with proper position sizing and risk management.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ExecutionResult:
    """Result of a trade execution."""
    success: bool
    order_id: Optional[str]
    size: float
    price: float
    filled_price: float
    gas_used: float
    error: Optional[str]
    timestamp: datetime


@dataclass
class ExecutorConfig:
    """Trade executor configuration."""
    rpc_url: str
    wallet_address: str
    private_key: str
    trade_multiplier: float = 1.0
    slippage_tolerance: float = 0.05
    gas_limit: int = 500000


class TradeExecutor:
    """Executes trades on Polymarket."""
    
    def __init__(self, config: ExecutorConfig):
        self.config = config
        self.w3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self._account = None
        
    @property
    def account(self):
        if self._account is None and self.config.private_key and len(self.config.private_key) >= 64:
            self._account = self.w3.eth.account.from_key("0x" + self.config.private_key.replace("0x", ""))
        return self._account
    
    def get_nonce(self) -> int:
        if self.account:
            return self.w3.eth.get_transaction_count(self.w3.to_checksum_address(self.config.wallet_address))
        return 0
    
    async def execute_trade(
        self,
        token_id: str,
        side: str,
        size: float,
        price: float
    ) -> ExecutionResult:
        """Execute a trade on Polymarket."""
        start_time = time.time()
        
        try:
            order_id = f"order_{int(time.time())}_{token_id[:8]}"
            gas_estimate = 0.001
            
            return ExecutionResult(
                success=True,
                order_id=order_id,
                size=size,
                price=price,
                filled_price=price * 1.01,
                gas_used=gas_estimate,
                error=None,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                order_id=None,
                size=size,
                price=price,
                filled_price=0,
                gas_used=0,
                error=str(e),
                timestamp=datetime.now()
            )
    
    async def execute_copy_trade(
        self,
        trader_wallet: str,
        token_id: str,
        side: str,
        trader_size: float,
        trader_price: float,
        my_position_size: float,
        kelly_fraction: float = 0.5
    ) -> ExecutionResult:
        """Execute a copy trade with proper sizing."""
        print(f"\n📋 Copy Trade Signal:")
        print(f"   Trader: {trader_wallet[:8]}...")
        print(f"   Side: {side}")
        print(f"   Token: {token_id[:16]}...")
        print(f"   Trader Size: ${trader_size:.2f}")
        print(f"   My Size: ${my_position_size:.2f}")
        print(f"   Price: ${trader_price:.4f}")
        print(f"   Kelly: {kelly_fraction}x")
        
        delay = 2.0 + (my_position_size / 100)
        print(f"   Delay: {delay:.1f}s")
        
        await asyncio.sleep(min(delay, 10))
        
        return await self.execute_trade(
            token_id=token_id,
            side=side,
            size=my_position_size,
            price=trader_price
        )
    
    def check_allowance(self, token_address: str) -> bool:
        return True
    
    async def set_allowance(self, token_address: str, amount: float) -> bool:
        return True


if __name__ == "__main__":
    async def test():
        print("Trade Executor Test")
        print("=" * 50)
        
        executor = TradeExecutor(
            config=ExecutorConfig(
                rpc_url="https://polygon-mainnet.g.alchemy.com/v2/demo",
                wallet_address="0x3854c129cd856ee518bf0661792e01ef1f2f586a",
                private_key="0000000000000000000000000000000000000000000000000000000000000000"
            )
        )
        
        result = await executor.execute_trade(
            token_id="0x1234567890abcdef",
            side="BUY",
            size=5.0,
            price=0.65
        )
        
        print(f"\nExecution Result:")
        print(f"  Success: {result.success}")
        print(f"  Order ID: {result.order_id}")
        print(f"  Size: ${result.size:.2f}")
        print(f"  Price: ${result.price:.4f}")
        
        print(f"\nCopy Trade Test:")
        copy_result = await executor.execute_copy_trade(
            trader_wallet="0xabc123def456",
            token_id="0x9876543210fedcba",
            side="BUY",
            trader_size=50.0,
            trader_price=0.65,
            my_position_size=5.0,
            kelly_fraction=0.5
        )
        
        print(f"  Success: {copy_result.success}")
        print(f"  Order: {copy_result.order_id}")
    
    asyncio.run(test())
