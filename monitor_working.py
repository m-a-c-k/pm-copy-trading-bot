#!/usr/bin/env python3
"""Working monitor for FollowMeABC123 using Data API."""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TRADER = os.getenv("USER_ADDRESSES", "").split(",")[0]
WALLET = os.getenv("PROXY_WALLET", "")
OUR_BANKROLL = float(os.getenv("BANKROLL", "433"))
TRADER_ESTIMATED = 10000.0
RATIO = OUR_BANKROLL / TRADER_ESTIMATED
MAX_POSITION = OUR_BANKROLL * 0.15

API_URL = "https://data-api.polymarket.com"

last_tx = None

def calculate_copy(trader_bet: float, avg_bet: float = 100.0) -> float:
    """Calculate proportional copy size."""
    pct = trader_bet / avg_bet if avg_bet > 0 else 1.0
    copy = trader_bet * RATIO * pct
    copy = min(copy, MAX_POSITION)
    return max(round(copy, 2), 1.0)

async def monitor():
    global last_tx
    
    print("=" * 70)
    print("FOLLOWMEABC123 COPY TRADING MONITOR")
    print("=" * 70)
    print(f"Trader: {TRADER[:20]}...")
    print(f"Our Bankroll: ${OUR_BANKROLL}")
    print(f"Ratio: {RATIO*100:.2f}%")
    print(f"Max Copy: ${MAX_POSITION:.2f}")
    print(f"API: {API_URL}/activity")
    print()
    print("Monitoring for trades... (Ctrl+C to stop)")
    print("-" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                resp = await client.get(
                    f"{API_URL}/activity",
                    params={"user": TRADER}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        # Filter for TRADE type
                        trades = [t for t in data if t.get("type") == "TRADE"]
                        
                        if trades:
                            latest = trades[0]
                            tx_hash = latest.get("transactionHash", "")
                            
                            if tx_hash and tx_hash != last_tx:
                                last_tx = tx_hash
                                
                                size = float(latest.get("usdcSize", 0))
                                side = latest.get("side", "")
                                price = float(latest.get("price", 0))
                                title = latest.get("title", "Unknown")[:40]
                                outcome = latest.get("outcome", "")
                                asset = (latest.get("asset", "") or "")[:16]
                                
                                # Calculate our copy
                                our_copy = calculate_copy(size)
                                pct_of_avg = (size / 100 * 100) if size > 0 else 100
                                
                                now = datetime.now().strftime("%H:%M:%S")
                                
                                print()
                                print(f"🚨 [{now}] NEW TRADE SIGNAL")
                                print(f"   📊 {title}")
                                print(f"   🎯 {outcome} @ ${price}")
                                print(f"   💰 Trader: {side} ${size:.2f}")
                                print(f"   📈 {pct_of_avg:.0f}% of avg bet")
                                print(f"   {'='*50}")
                                print(f"   💵 OUR COPY: ${our_copy:.2f}")
                                print(f"   {'='*50}")
                                
                                if our_copy >= 5:
                                    print(f"   ✅ Size looks good!")
                                elif our_copy >= 2:
                                    print(f"   ⚠️  Small position")
                                else:
                                    print(f"   💰 Very conservative")
                                
                                print("-" * 70)
                    else:
                        print(".", end="", flush=True)
                else:
                    print(f"API Error: {resp.status_code}")
                    
            except Exception as e:
                print(f"Error: {e}")
            
            await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\n\nStopped. Happy trading! 📈")
