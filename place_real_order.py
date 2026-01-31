#!/usr/bin/env python3
"""Place a real test order on Polymarket."""

import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()

# Get a real market token
async def get_active_market():
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "limit": 3}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                m = data[0]
                return m.get("clobTokenId") or m.get("tokenId"), m.get("question", "Unknown")[:40]
        return None, None

# Place order via CLOB
async def place_order(token_id, side, size, price):
    import hashlib
    import time
    import hmac
    
    api_key = os.getenv("POLYMARKET_API_KEY")
    secret = os.getenv("POLYMARKET_SECRET_KEY")
    passphrase = os.getenv("POLYMARKET_PASSPHRASE")
    wallet = os.getenv("PROXY_WALLET")
    private_key = os.getenv("PRIVATE_KEY")
    
    base_url = "https://clob.polymarket.com"
    
    order_payload = {
        "tokenId": token_id,
        "side": side.lower(),
        "amount": str(size),
        "price": str(price),
        "orderType": "limit",
        "timeInForce": "GTC",
        "nonce": str(int(time.time() * 1000)),
    }
    
    # Sign the order
    timestamp = str(int(time.time()))
    message = f"{timestamp}POST/order{json.dumps(order_payload)}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "POLY-API-KEY": api_key,
        "POLY-API-TIMESTAMP": timestamp,
        "POLY-API-SIGNATURE": signature,
        "POLY-API-PASSPHRASE": passphrase,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{base_url}/order",
            json=order_payload,
            headers=headers
        )
        
        return resp.status_code, resp.text[:500]

async def main():
    print("=" * 70)
    print("PLACING REAL TEST ORDER")
    print("=" * 70)
    print()
    
    # Check credentials
    api_key = os.getenv("POLYMARKET_API_KEY")
    print(f"API Key: {api_key[:20]}...")
    
    # Get a market
    token, title = await get_active_market()
    if not token:
        print("Could not find active market")
        return
    
    print(f"Market: {title}")
    print(f"Token: {token}")
    print()
    
    # Try to place small order
    print("Attempting to place $1 test order...")
    status, response = await place_order(token, "buy", 1.0, 0.50)
    
    print(f"Status: {status}")
    print(f"Response: {response}")
    
    if status in [200, 201]:
        print("\n✅ ORDER PLACED SUCCESSFULLY!")
    elif status == 401:
        print("\n⚠️  Authentication failed - check API credentials")
    elif status == 404:
        print("\n⚠️  Endpoint not found - CLOB API may have changed")
    else:
        print(f"\n❌ Order failed: {status}")

import json
asyncio.run(main())
