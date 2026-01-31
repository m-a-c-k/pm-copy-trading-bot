#!/usr/bin/env python3
"""Monitor FollowMeABC123 for new trades."""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WALLET = os.getenv("PROXY_WALLET", "")
TRADER = os.getenv("USER_ADDRESSES", "").split(",")[0]
BANKROLL = float(os.getenv("BANKROLL", "433"))
MAX_TRADE = BANKROLL * 0.02  # 2% cap

print('=' * 60)
print('MONITORING: FollowMeABC123')
print('=' * 60)
print(f'Trader: {TRADER[:16]}...')
print(f'Your Bankroll: ${BANKROLL}')
print(f'Max Copy Size: ${MAX_TRADE:.2f}')
print()

last_trade = None

async def check_trades():
    global last_trade
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                resp = await client.get(
                    f"https://api.polymarket.com/api/core/users/{TRADER}/activity",
                    params={"limit": 5, "type": "TRADE"}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        latest = data[0]
                        tx_hash = latest.get('transactionHash', '')
                        
                        if tx_hash and tx_hash != last_trade:
                            last_trade = tx_hash
                            size = latest.get('usdcSize', 0)
                            side = latest.get('side', '')
                            price = latest.get('price', 0)
                            asset = latest.get('asset', '')[:16]
                            
                            now = datetime.now().strftime('%H:%M:%S')
                            print(f'[{now}] 🚨 NEW TRADE!')
                            print(f'    {side} ${size:.2f} @ ${price}')
                            print(f'    Asset: {asset}...')
                            
                            # Calculate copy size
                            copy_size = min(size * 0.5, MAX_TRADE)  # Scale to our bankroll
                            print(f'    📊 Copy: ${copy_size:.2f}')
                            print()
                    else:
                        print('.', end='', flush=True)
                else:
                    print('?', end='', flush=True)
                    
            except Exception as e:
                print(f'Error: {e}')
                
            await asyncio.sleep(3)  # Check every 3 seconds

print('Monitoring for trades... (Ctrl+C to stop)')
print()
try:
    asyncio.run(check_trades())
except KeyboardInterrupt:
    print('\n\nStopped.')
