#!/usr/bin/env python3
"""Whale copy trading monitor for FollowMeABC123."""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TRADER = os.getenv("USER_ADDRESSES", "").split(",")[0]
OUR_BANKROLL = float(os.getenv("BANKROLL", "433"))
THEIR_AVG_BET = 100.0
MAX_PCT = 0.15
MAX_POSITION = OUR_BANKROLL * MAX_PCT

API_URL = "https://data-api.polymarket.com"
last_tx = None


def calculate_copy(trader_bet: float) -> dict:
    pct_of_avg = trader_bet / THEIR_AVG_BET
    base_pct = pct_of_avg * 2.0  # 2% per 100% of avg
    our_copy = (OUR_BANKROLL * base_pct) / 100
    our_copy = min(our_copy, MAX_POSITION)
    our_copy = max(round(our_copy, 2), 1.0)
    return {"size": our_copy, "pct": our_copy / OUR_BANKROLL * 100}


async def show_status():
    print("=" * 70)
    print("🐋 WHALE COPY TRADING - FollowMeABC123")
    print("=" * 70)
    print(f"Our Bankroll:   ${OUR_BANKROLL}")
    print(f"Their Avg Bet:  ${THEIR_AVG_BET}")
    print(f"Max Position:   ${MAX_POSITION:.2f} ({MAX_PCT*100:.0f}%)")
    print()
    print("Sizing (proportional to their avg bet):")
    print("-" * 70)
    
    for bet in [25, 100, 500, 1000, 5000, 10000]:
        c = calculate_copy(bet)
        print(f"  ${bet:<6} → ${c['size']:.2f} ({c['pct']:.1f}%)")
    
    print("-" * 70)


async def monitor():
    await show_status()
    global last_tx
    
    print()
    print("Monitoring for trades... (Ctrl+C to stop)")
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
                            print(f"🚨 [{now}] WHALE TRADE")
                            print(f"   📊 {title}")
                            print(f"   🎯 {outcome} @ ${price}")
                            print(f"   💰 Whale: {side} ${size:,.2f} ({size/THEIR_AVG_BET*100:.0f}% of avg)")
                            print(f"   {'='*50}")
                            print(f"   💵 COPY: ${copy['size']:.2f} ({copy['pct']:.1f}% of bank)")
                            print(f"   {'='*50}")
                            
                            print("-" * 70)
                
                await asyncio.sleep(3)
                
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("\n\nStopped.")
