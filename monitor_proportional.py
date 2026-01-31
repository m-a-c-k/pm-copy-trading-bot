#!/usr/bin/env python3
"""
Monitor FollowMeABC123 with proportional position sizing.

Strategy:
- Estimate trader's average bet (default $100 if no API data)
- If he bets 50% of avg → we bet 50% of our proportional share
- If he bets 200% of avg → we bet 200% of our proportional share
- Proportional share = (Our Bankroll / Trader Bankroll) × His Bet
"""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Config
OUR_BANKROLL = 433.0
TRADER_ADDRESS = os.getenv("USER_ADDRESSES", "").split(",")[0]
TRADER_ESTIMATED_BANKROLL = 10000.0  # Assume trader has ~$10k
DEFAULT_AVG_BET = 100.0  # Default if API fails

# Calculate bankroll ratio
BANKROLL_RATIO = OUR_BANKROLL / TRADER_ESTIMATED_BANKROLL  # 4.33%
MAX_POSITION = OUR_BANKROLL * 0.15  # Max 15% of bankroll per trade

last_trade = None
trader_avg_bet = DEFAULT_AVG_BET


async def get_trader_avg():
    """Try to get trader's average bet from API."""
    global trader_avg_bet
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"https://api.polymarket.com/api/core/users/{TRADER_ADDRESS}/activity",
                params={"limit": 20, "type": "TRADE"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    sizes = [float(t.get('usdcSize', 0)) for t in data if float(t.get('usdcSize', 0)) > 0]
                    if sizes:
                        trader_avg_bet = sum(sizes) / len(sizes)
                        return True
    except:
        pass
    return False


def calculate_position(trader_bet: float) -> float:
    """Calculate our position proportionally."""
    # What % of average is this bet?
    pct_of_avg = trader_bet / trader_avg_bet
    
    # Our proportional share of this bet
    proportional = trader_bet * BANKROLL_RATIO
    
    # Scale by how aggressive the trader is being
    our_position = proportional * pct_of_avg
    
    # Cap at max
    our_position = min(our_position, MAX_POSITION)
    
    # Min threshold
    if our_position < 1.0:
        our_position = 1.0
    
    return round(our_position, 2)


async def monitor():
    global last_trade, trader_avg_bet
    
    print("=" * 70)
    print("PROPORTIONAL COPY TRADING - FollowMeABC123")
    print("=" * 70)
    print()
    print(f"Our Bankroll: ${OUR_BANKROLL}")
    print(f"Trader Est: ${TRADER_ESTIMATED_BANKROLL}")
    print(f"Ratio: {BANKROLL_RATIO*100:.2f}%")
    print(f"Max Position: ${MAX_POSITION:.2f}")
    print()
    
    # Try to get actual average
    print("Fetching trader statistics...")
    if await get_trader_avg():
        print(f"✓ Trader's avg bet: ${trader_avg_bet:.2f}")
    else:
        print(f"✗ Using default avg: ${trader_avg_bet} (API unavailable)")
    print()
    
    print("Monitoring for trades... (Ctrl+C to stop)")
    print("-" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                resp = await client.get(
                    f"https://api.polymarket.com/api/core/users/{TRADER_ADDRESS}/activity",
                    params={"limit": 5, "type": "TRADE"}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        latest = data[0]
                        tx_hash = latest.get('transactionHash', '')
                        
                        if tx_hash and tx_hash != last_trade:
                            last_trade = tx_hash
                            size = float(latest.get('usdcSize', 0))
                            side = latest.get('side', '')
                            price = float(latest.get('price', 0))
                            asset = (latest.get('asset', '') or '')[:16]
                            
                            # Calculate our position
                            our_size = calculate_position(size)
                            pct_of_avg = (size / trader_avg_bet * 100) if trader_avg_bet > 0 else 100
                            
                            now = datetime.now().strftime('%H:%M:%S')
                            print()
                            print(f"[{now}] 🚨 NEW TRADE SIGNAL")
                            print(f"    Trader: {side} ${size:.2f} @ ${price}")
                            print(f"    This is {pct_of_avg:.0f}% of their avg bet (${trader_avg_bet:.2f})")
                            print(f"    ─────────────────────────────────")
                            print(f"    📊 OUR COPY: ${our_size:.2f}")
                            print(f"    (Proportional to {BANKROLL_RATIO*100:.2f}% bankroll ratio)")
                            print()
                            
                            if our_size >= 5:
                                print(f"    ✅ Size looks good! (${our_size:.2f})")
                            elif our_size >= 2:
                                print(f"    ⚠️  Small position (${our_size:.2f})")
                            else:
                                print(f"    💰 Very conservative (${our_size:.2f})")
                            
                            print("-" * 70)
                    else:
                        print(".", end="", flush=True)
                else:
                    print("?", end="", flush=True)
                    
            except Exception as e:
                print(f"Error: {e}")
                
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\n\nStopped. Happy trading! 📈")
