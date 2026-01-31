"""
Whale-Aware Copy Trading Scaler

FollowMeABC123 is a $1.5M whale but we size proportionally.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScalerConfig:
    our_bankroll: float = 433.0
    trader_avg_bet: float = 100.0
    max_position_pct: float = 0.15  # 15%


class WhaleScaler:
    def __init__(self, config: ScalerConfig):
        self.config = config
        self.max_position = config.our_bankroll * config.max_position_pct
    
    def calculate(self, trader_bet: float) -> dict:
        """Scale proportionally to their bet vs their average."""
        pct_of_avg = trader_bet / self.config.trader_avg_bet
        
        # Base: we match their % of average
        # If they bet 100% of avg, we use 2% of our bankroll
        # If they bet 200% of avg, we use 4% of our bankroll
        base_pct = pct_of_avg * 2.0  # 2% per 100% of avg
        
        our_copy = (self.config.our_bankroll * base_pct) / 100
        
        # Cap
        our_copy = min(our_copy, self.max_position)
        our_copy = max(round(our_copy, 2), 1.0)
        
        return {
            "trader_bet": round(trader_bet, 2),
            "pct_of_avg": round(pct_of_avg * 100, 1),
            "our_copy": our_copy,
            "pct_of_bank": round(our_copy / self.config.our_bankroll * 100, 1)
        }
    
    def show(self):
        print("=" * 70)
        print("🐋 WHALE COPY TRADING - FollowMeABC123")
        print("=" * 70)
        print()
        print(f"Our Bankroll:   ${self.config.our_bankroll}")
        print(f"Their Avg Bet:  ${self.config.trader_avg_bet}")
        print(f"Max Position:   ${self.max_position:.2f} ({self.config.max_position_pct*100:.0f}%)")
        print()
        print("Position Sizing:")
        print("-" * 70)
        print(f"{'Trader Bet':<15} {'% of Avg':<12} {'Our Copy':<12} {'% of Bank'}")
        print("-" * 70)
        
        for bet in [25, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 50000, 100000]:
            r = self.calculate(bet)
            print(f"${bet:<14,} {r['pct_of_avg']:>6.0f}%{'':<5} ${r['our_copy']:<11.2f} {r['pct_of_bank']:>5.1f}%")
        
        print("-" * 70)
        print()
        print("Examples:")
        r = self.calculate(100)
        print(f"  Trader $100 (avg bet) → Copy ${r['our_copy']:.2f} ({r['pct_of_bank']:.1f}%)")
        r = self.calculate(500)
        print(f"  Trader $500 (5x avg)  → Copy ${r['our_copy']:.2f} ({r['pct_of_bank']:.1f}%)")
        r = self.calculate(5000)
        print(f"  Trader $5000 (50x)    → Copy ${r['our_copy']:.2f} ({r['pct_of_bank']:.1f}%)")
        print()
        print("=" * 70)


def main():
    config = ScalerConfig(
        our_bankroll=433.0,
        trader_avg_bet=100.0,
        max_position_pct=0.15
    )
    
    scaler = WhaleScaler(config)
    scaler.show()


if __name__ == "__main__":
    main()
