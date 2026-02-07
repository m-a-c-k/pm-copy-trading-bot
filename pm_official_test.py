#!/usr/bin/env python3
"""
Polymarket Copy Trading - Using Official CLOB Client
This uses py-clob-client which handles auth properly
"""

import os
import asyncio
from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, OrderArgs, OrderType

load_dotenv()

# PM Credentials
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
PROXY_WALLET = os.getenv("PROXY_WALLET", "")
API_KEY = os.getenv("POLYMARKET_BUILDER_API_KEY", "")
API_SECRET = os.getenv("POLYMARKET_BUILDER_SECRET", "")
API_PASSPHRASE = os.getenv("POLYMARKET_BUILDER_PASSPHRASE", "")

# Settings
CLOB_HOST = "https://clob.polymarket.com"
CHAIN_ID = 137  # Polygon mainnet


class PMOfficialTrader:
    """PM trader using official CLOB client."""
    
    def __init__(self):
        self.client = None
        self.setup_client()
        
    def setup_client(self):
        """Initialize CLOB client with credentials."""
        try:
            # Create credentials
            creds = ApiCreds(
                api_key=API_KEY,
                api_secret=API_SECRET,
                api_passphrase=API_PASSPHRASE
            )
            
            # Initialize client
            self.client = ClobClient(
                host=CLOB_HOST,
                key=PRIVATE_KEY,
                chain_id=CHAIN_ID,
                creds=creds
            )
            
            print("✓ PM CLOB Client initialized")
            
        except Exception as e:
            print(f"❌ Failed to init client: {e}")
            self.client = None
    
    async def get_balance(self):
        """Get USDC balance."""
        if not self.client:
            return 0.0
        try:
            # Get balance via client
            balance = self.client.get_balance()
            return float(balance)
        except:
            return 0.0
    
    async def place_test_order(self, size: float = 1.0):
        """Place a small test order."""
        if not self.client:
            print("❌ Client not initialized")
            return False
        
        try:
            print(f"\nPlacing ${size} test order...")
            
            # Need to get market info first
            # For now, just test connectivity
            markets = self.client.get_markets()
            print(f"✓ Connected! Found {len(markets)} markets")
            
            # Placeholder - would need actual token_id
            print(f"   Would place ${size} order here")
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def main():
    """Test PM trading."""
    print("="*60)
    print("PM Official CLOB Client Test")
    print("="*60)
    
    trader = PMOfficialTrader()
    
    if not trader.client:
        print("\n❌ Failed to initialize")
        return
    
    # Test balance
    print("\n1. Checking balance...")
    balance = await trader.get_balance()
    print(f"   Balance: ${balance:.2f}")
    
    # Test order
    print("\n2. Testing order placement...")
    await trader.place_test_order(size=1.0)


if __name__ == "__main__":
    asyncio.run(main())
