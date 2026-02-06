#!/usr/bin/env python3
"""
Polymarket Copy Executor - Copy whale trades directly on PM
No sports filter - copies ALL markets (politics, crypto, sports, etc.)
Uses Builder API for gasless trading
"""

import asyncio
import os
import json
import time
import hmac
import hashlib
import base64
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import httpx

load_dotenv()


@dataclass
class PMCopyConfig:
    """Config for PM copy trading."""
    enabled: bool = False
    wallet_address: str = ""
    private_key: str = ""
    builder_api_key: str = ""
    builder_secret: str = ""
    builder_passphrase: str = ""
    max_position_size: float = 50.0
    max_total_exposure: float = 300.0
    dry_run: bool = True
    
    @classmethod
    def from_env(cls) -> "PMCopyConfig":
        """Load from environment."""
        return cls(
            enabled=os.getenv("COPY_TO_POLYMARKET", "").lower() == "true",
            wallet_address=os.getenv("PROXY_WALLET", ""),
            private_key=os.getenv("PRIVATE_KEY", ""),
            builder_api_key=os.getenv("POLYMARKET_BUILDER_API_KEY", ""),
            builder_secret=os.getenv("POLYMARKET_BUILDER_SECRET", ""),
            builder_passphrase=os.getenv("POLYMARKET_BUILDER_PASSPHRASE", ""),
            max_position_size=float(os.getenv("PM_MAX_POSITION_SIZE", "50.0")),
            max_total_exposure=float(os.getenv("PM_MAX_TOTAL_EXPOSURE", "300.0")),
            dry_run=os.getenv("PM_DRY_RUN", "true").lower() == "true"
        )


class PMClient:
    """Polymarket CLOB client with Builder authentication."""
    
    CLOB_URL = "https://clob.polymarket.com"
    
    def __init__(self, config: PMCopyConfig):
        self.config = config
        self.session = httpx.AsyncClient(timeout=30.0)
        
    def _get_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Generate Builder authentication headers."""
        timestamp = str(int(time.time()))
        message = timestamp + method.upper() + path + body
        
        # Create signature using Builder secret
        signature = hmac.new(
            self.config.builder_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "POLY-API-KEY": self.config.builder_api_key,
            "POLY-SIGNATURE": signature,
            "POLY-TIMESTAMP": timestamp,
            "POLY-PASSPHRASE": self.config.builder_passphrase
        }
    
    async def get_markets(self) -> list:
        """Get available markets."""
        try:
            headers = self._get_headers("GET", "/markets")
            resp = await self.session.get(
                f"{self.CLOB_URL}/markets",
                headers=headers
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
        except Exception as e:
            print(f"Error getting markets: {e}")
        return []
    
    async def get_balance(self) -> float:
        """Get USDC balance."""
        try:
            path = f"/balance/{self.config.wallet_address}"
            headers = self._get_headers("GET", path)
            resp = await self.session.get(
                f"{self.CLOB_URL}{path}",
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get("balance", 0))
        except Exception as e:
            print(f"Error getting balance: {e}")
        return 0.0
    
    async def place_order(
        self, 
        token_id: str, 
        side: str, 
        size: float, 
        price: float
    ) -> Dict[str, Any]:
        """Place an order on PM CLOB."""
        # TODO: Implement actual order signing and placement
        # This requires EIP-712 signing with private key
        return {
            "success": True,
            "order_id": f"test_{int(time.time())}",
            "status": "DRY_RUN"
        }
    
    async def close(self):
        await self.session.aclose()


class PolymarketCopyExecutor:
    """Execute copy trades on Polymarket."""
    
    def __init__(self, config: PMCopyConfig):
        self.config = config
        self.client = PMClient(config) if config.enabled else None
        self.positions = {}
        self.total_exposure = 0.0
        
        if not config.enabled:
            print("⚠️  PM Copy Trading disabled")
            return
            
        if not all([config.wallet_address, config.builder_api_key, config.builder_secret]):
            print("❌ Missing PM credentials!")
            self.config.enabled = False
            return
            
        print("✓ PM Copy Executor initialized")
        print(f"  Wallet: {config.wallet_address[:10]}...")
        print(f"  Mode: {'DRY RUN' if config.dry_run else 'LIVE'}")
        print(f"  Max per trade: ${config.max_position_size}")
        print(f"  Copies ALL markets (no sports filter)")
        
    async def execute_copy_trade(self, trade_data: dict) -> Dict[str, Any]:
        """Execute a copy trade on PM - NO sports filter!"""
        
        if not self.config.enabled or not self.client:
            return {"success": False, "error": "PM trading disabled"}
            
        # Extract trade info
        market = trade_data.get("market", {})
        title = market.get("title", "Unknown")
        token_id = trade_data.get("tokenId") or trade_data.get("clobTokenId", "")
        side = trade_data.get("side", "buy").lower()
        outcome = trade_data.get("outcome", "yes").lower()
        whale_size = float(trade_data.get("amount") or trade_data.get("size", 0))
        
        # Get trader attribution
        trader = trade_data.get("_trader_address", "unknown")[:10]
        
        print(f"\n🎯 PM Copy Trade from {trader}:")
        print(f"   Market: {title[:50]}...")
        print(f"   Whale: ${whale_size:.2f}")
        print(f"   Side: {side} {outcome}")
        
        # Calculate position size (10% of whale, max $50)
        our_size = min(whale_size * 0.1, self.config.max_position_size)
        
        if our_size < 1.0:
            print(f"   ⚠️  Too small (${our_size:.2f}), skipping")
            return {"success": False, "error": "Size too small"}
            
        # Check exposure limits
        if self.total_exposure + our_size > self.config.max_total_exposure:
            print(f"   ⚠️  Max exposure reached (${self.total_exposure:.2f})")
            return {"success": False, "error": "Max exposure"}
        
        if self.config.dry_run:
            print(f"   🧪 DRY RUN - Would buy ${our_size:.2f} of {outcome}")
            return {
                "success": True,
                "dry_run": True,
                "size": our_size,
                "side": side,
                "outcome": outcome,
                "trader": trader
            }
        
        # Place actual order
        print(f"   📤 Placing order: ${our_size:.2f} {outcome}")
        
        # Get market price (would need token_id mapping)
        price = 0.50  # Default to 50% for now
        
        result = await self.client.place_order(
            token_id=token_id,
            side=side,
            size=our_size,
            price=price
        )
        
        if result.get("success"):
            self.total_exposure += our_size
            self.positions[token_id] = self.positions.get(token_id, 0) + our_size
            print(f"   ✅ Order placed: {result.get('order_id')}")
        else:
            print(f"   ❌ Failed: {result.get('error')}")
        
        return result
        
    async def get_balance(self) -> float:
        """Get current USDC balance."""
        if self.client:
            return await self.client.get_balance()
        return 0.0
        
    def get_status(self) -> Dict[str, Any]:
        """Get executor status."""
        return {
            "enabled": self.config.enabled,
            "dry_run": self.config.dry_run,
            "total_exposure": self.total_exposure,
            "positions": len(self.positions),
            "wallet": self.config.wallet_address[:10] + "..." if self.config.wallet_address else None
        }
    
    async def close(self):
        if self.client:
            await self.client.close()


async def test_pm_executor():
    """Test the PM executor with Builder API."""
    print("="*60)
    print("Testing PM Copy Executor with Builder API")
    print("="*60)
    
    config = PMCopyConfig.from_env()
    executor = PolymarketCopyExecutor(config)
    
    if not config.enabled:
        print("\n❌ PM trading not enabled. Check .env:")
        print("  COPY_TO_POLYMARKET=true")
        return
    
    # Test 1: Get balance
    print("\n1. Testing balance check...")
    balance = await executor.get_balance()
    print(f"   USDC Balance: ${balance:.2f}")
    
    # Test 2: Copy trade
    print("\n2. Testing copy trade...")
    test_trade = {
        "market": {
            "title": "Will ETH hit $5000 this month?",
            "id": "test-market-123"
        },
        "tokenId": "0x1234567890abcdef",
        "side": "buy",
        "outcome": "yes",
        "amount": 500.0,
        "_trader_address": "0xwhale123456789"
    }
    
    result = await executor.execute_copy_trade(test_trade)
    print(f"\n   Result: {'✅ Success' if result.get('success') else '❌ Failed'}")
    if result.get('dry_run'):
        print(f"   (Dry run - no actual trade)")
    
    # Test 3: Status
    print("\n3. Executor status:")
    status = executor.get_status()
    for k, v in status.items():
        print(f"   {k}: {v}")
    
    await executor.close()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_pm_executor())
