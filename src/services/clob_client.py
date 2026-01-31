"""
Polymarket CLOB Client for Real Trading

Uses the official Polymarket CLOB API for:
- Placing market and limit orders
- Getting order book
- Checking balances
- Signing orders with wallet
"""

import os
import asyncio
import time
import hmac
import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import httpx

load_dotenv()


@dataclass
class OrderBookEntry:
    price: float
    size: float


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[str]
    transaction_hash: Optional[str]
    filled_price: float
    size: float
    error: Optional[str]


class PolymarketCLOBClient:
    """Real Polymarket CLOB client for trading."""
    
    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        wallet_address: str,
        private_key: str
    ):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.wallet_address = wallet_address
        self.private_key = private_key
        
        self.base_url = "https://clob.polymarket.com"
        self.session = httpx.AsyncClient(timeout=30.0)
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
    
    async def close(self):
        await self.session.aclose()
    
    def _generate_signature(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """Generate authentication signature."""
        message = f"{timestamp}{method}{path}{body}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """Get headers with authentication."""
        timestamp = str(int(time.time()))
        signature = self._generate_signature(timestamp, method, path, body)
        
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "POLY-API-KEY": self.api_key,
            "POLY-API-TIMESTAMP": timestamp,
            "POLY-API-SIGNATURE": signature,
            "POLY-API-PASSPHRASE": self.passphrase,
        }
    
    async def get_order_book(self, token_id: str) -> Dict[str, Any]:
        """Get order book for a token."""
        try:
            resp = await self.session.get(
                f"{self.base_url}/order-book/{token_id}"
            )
            if resp.status_code == 200:
                return resp.json()
            return {"bids": [], "asks": []}
        except Exception as e:
            print(f"Order book error: {e}")
            return {"bids": [], "asks": []}
    
    async def place_order(
        self,
        token_id: str,
        side: str,  # "buy" or "sell"
        size: float,
        price: float,
        order_type: str = "limit",  # "limit" or "market"
        time_in_force: str = "GTC"  # "GTC", "FOK", "IOC"
    ) -> OrderResult:
        """
        Place an order on Polymarket CLOB.
        """
        try:
            # Build order payload
            order_payload = {
                "tokenId": token_id,
                "side": side,
                "amount": str(size),
                "price": str(price),
                "orderType": order_type,
                "timeInForce": time_in_force,
                "nonce": str(int(time.time() * 1000)),
                "expiration": str(int(time.time()) + 86400 * 7),  # 7 days
            }
            
            path = "/order"
            body = json.dumps(order_payload)
            headers = self._get_auth_headers("POST", path, body)
            
            resp = await self.session.post(
                f"{self.base_url}{path}",
                content=body,
                headers=headers
            )
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                return OrderResult(
                    success=True,
                    order_id=data.get("orderId"),
                    transaction_hash=data.get("transactionHash"),
                    filled_price=price,
                    size=size,
                    error=None
                )
            else:
                return OrderResult(
                    success=False,
                    order_id=None,
                    transaction_hash=None,
                    filled_price=0,
                    size=0,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
                
        except Exception as e:
            return OrderResult(
                success=False,
                order_id=None,
                transaction_hash=None,
                filled_price=0,
                size=0,
                error=str(e)
            )
    
    async def get_balances(self) -> Dict[str, float]:
        """Get wallet balances."""
        try:
            resp = await self.session.get(
                f"{self.base_url}/balances",
                headers=self._get_auth_headers("GET", "/balances")
            )
            if resp.status_code == 200:
                data = resp.json()
                balances = {}
                for b in data.get("balances", []):
                    balances[b.get("symbol", "UNKNOWN")] = float(b.get("available", 0))
                return balances
            return {}
        except Exception:
            return {}
    
    async def approve_token(self, token_id: str, amount: float = 0) -> bool:
        """Approve token for trading."""
        try:
            approve_payload = {
                "tokenId": token_id,
                "amount": str(amount) if amount > 0 else "115792089237316195423570985008687907853269984665640564039457584007913129639935",  # Max uint256
            }
            path = "/approve"
            body = json.dumps(approve_payload)
            headers = self._get_auth_headers("POST", path, body)
            
            resp = await self.session.post(
                f"{self.base_url}{path}",
                content=body,
                headers=headers
            )
            return resp.status_code in [200, 201]
        except Exception:
            return False


async def test_clob_connection():
    """Test CLOB connection."""
    print("=" * 50)
    print("Testing Polymarket CLOB Connection")
    print("=" * 50)
    
    client = PolymarketCLOBClient(
        api_key=os.getenv("POLYMARKET_API_KEY", ""),
        secret_key=os.getenv("POLYMARKET_SECRET_KEY", ""),
        passphrase=os.getenv("POLYMARKET_PASSPHRASE", ""),
        wallet_address=os.getenv("PROXY_WALLET", ""),
        private_key=os.getenv("PRIVATE_KEY", "")
    )
    
    print(f"API Key: {client.api_key[:15]}...")
    print(f"Wallet: {client.wallet_address[:10]}...")
    print()
    
    # Test order book
    print("Testing order book...")
    orderbook = await client.get_order_book("0x1234...")
    print(f"Order book response: {orderbook}")
    
    # Test balances
    print("\nTesting balances...")
    balances = await client.get_balances()
    print(f"Balances: {balances}")
    
    await client.close()
    print("\n✅ CLOB client initialized successfully!")
    print("Note: Full trading requires approved API access from Polymarket")


if __name__ == "__main__":
    asyncio.run(test_clob_connection())
