#!/usr/bin/env python3
"""
Whale-Aware Copy Trading Monitor for FollowMeABC123

FollowMeABC123 is a $1.5M whale with $1.18M in profits!
Position sizing scales based on their bet size.
"""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TRADER = os.getenv("USER_ADDRESSES", "").split(",")[0]
OUR_BANKROLL = float(os.getenv("BANKROLL", "433"))
MAX_POSITION = OUR_BANKROLL * 0.15  # $65

API_URL = "https://data-api.polymarket.com"
last_tx = None


def calculate_copy(trader_bet: float) -> dict:
    """Calculate copy based on bet size tiers."""
    if trader_bet < 100:
        our_copy = 5.0
    elif trader_bet < 500:
        our_copy = 10.0
    elif trader_bet < 2000:
        our_copy = 20.0
    elif trader_bet < 10000:
        our_copy = 30.0
    else:
        our_copy = min(trader_bet * 0.0065, MAX_POSITION)  # 0.65% of very large bets
    
    our_copy = max(round(our_copy, 2), 1.0)
    
    return {
        "size": our_copy,
        "pct_of_bank": our_copy / OUR_BANKROLL * 100,
        "tier": "small" if trader_bet < 100 else "medium" if trader_bet < 500 else "large" if trader_bet < 5000 else "whale"
    }


async def show_summary():
    """Show whale info and sizing."""
    print("=" * 70)
    print("🐋 WHALE COPY TRADING - FollowMeABC123")
    print("=" * 70)
    print()
    print("WHALE STATS:")
    print("  Positions Value: $1,500,000")
    print("  All-time Profit: $1,181,829")
    print("  Biggest Win: $142,000")
    print()
    print(f"OUR BANKROLL: ${OUR_BANKROLL}")
    print(f"MAX COPY: ${MAX_POSITION} (15%)")
    print()
    print("SIZING TIERS:")
    print("-" * 70)
    print(f"{'Trader Bet':<15} {'Our Copy':<12} {'% of Bank':<10} {'Tier'}")
    print("-" * 70)
    
    for bet, copy, tier in [
        (25, 5, "small"),
        (100, 10, "small"),
        (500, 20, "medium"),
        (1000, 30, "large"),
        (5000, 50, "very large"),
        (10000, 65, "whale"),
        (50000, 65, "whale (cap)"),
        (100000, 65, "whale (cap)"),
    ]:
        pct = copy / OUR_BANKROLL * 100
        print(f"${bet:<14,} ${copy:<11} {pct:>7.1f}%   {tier}")
    
    print("-" * 70)


async def monitor():
    global last_tx
    
    await show_summary()
    
    print()
    print("MONITORING FOR NEW TRADES...")
    print("-" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            try:
                resp = await client.get(f"{API_URL}/activity", params={"user": TRADER})
                
                if resp.status_code == 200:
                    data = resp.json()
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
                            
                            copy = calculate_copy(size)
                            
                            now = datetime.now().strftime("%H:%M:%S")
                            
                            print()
                            print(f"🚨 [{now}] WHALE TRADE SIGNAL")
                            print(f"   📊 {title}")
                            print(f"   🎯 {outcome} @ ${price}")
                            print(f"   💰 Whale bets: ${size:,.2f} ({copy['tier'].upper()})")
                            print(f"   {'='*50}")
                            print(f"   💵 OUR COPY: ${copy['size']:.2f} ({copy['pct_of_bank']:.1f}% of bankroll)")
                            print(f"   {'='*50}")
                            
                            if copy["size"] >= 50:
                                print(f"   🔥 BIG COPY! ${copy['size']:.2f}")
                            elif copy["size"] >= 20:
                                print(f"   ✅ Solid copy: ${copy['size']:.2f}")
                            else:
                                print(f"   📊 Small copy: ${copy['size']:.2f}")
                            
                            print("-" * 70)
                
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\n\nStopped. Happy trading! 🐋")
