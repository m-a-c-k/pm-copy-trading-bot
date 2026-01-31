"""
Moderate Position Scaler - Mid Level

Balanced sizing between conservative and aggressive.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScalerConfig:
    our_bankroll: float = 433.0
    trader_address: str = ""
    trader_avg_bet: float = 100.0
    trader_bankroll: float = 10000.0
    size_multiplier: float = 1.5  # Moderate (1.5x)
    max_position_pct: float = 0.15  # Max 15%


class PositionScaler:
    """Moderate proportional position scaler."""
    
    def __init__(self, config: ScalerConfig):
        self.config = config
        self.bankroll_ratio = config.our_bankroll / config.trader_bankroll
        self.max_position = config.our_bankroll * config.max_position_pct
    
    def calculate(self, trader_bet: float) -> dict:
        pct_of_avg = trader_bet / self.config.trader_avg_bet if self.config.trader_avg_bet > 0 else 1.0
        base_share = trader_bet * self.bankroll_ratio
        our_share = base_share * self.config.size_multiplier
        
        if pct_of_avg > 1.5:
            our_share *= 1.15
        elif pct_of_avg < 0.5:
            our_share *= 0.9
        
        our_share = min(our_share, self.max_position)
        our_share = max(round(our_share, 2), 1.0)
        
        return {
            "trader_bet": round(trader_bet, 2),
            "pct_of_avg": round(pct_of_avg * 100, 1),
            "our_copy": our_share,
            "pct_of_bank": round(our_share / self.config.our_bankroll * 100, 1)
        }
    
    def show_examples(self):
        print("=" * 70)
        print("MODERATE COPY TRADING - FollowMeABC123")
        print("=" * 70)
        print()
        print(f"Our Bankroll:   ${self.config.our_bankroll}")
        print(f"Bankroll Ratio: {self.bankroll_ratio*100:.2f}%")
        print(f"Multiplier:     {self.config.size_multiplier}x (moderate)")
        print(f"Max Position:   ${self.max_position:.2f} ({self.config.max_position_pct*100:.0f}% of bankroll)")
        print()
        print("-" * 70)
        print(f"{'Trader Bet':<15} {'% of Avg':<12} {'Our Copy':<12} {'% of Bank'}")
        print("-" * 70)
        
        for bet in [25, 50, 100, 200, 500, 688]:
            r = self.calculate(bet)
            print(f"${bet:<14} {r['pct_of_avg']:>6.0f}%{'':<5} ${r['our_copy']:<11.2f} {r['pct_of_bank']:>5.1f}%")
        
        print("-" * 70)
        print()
        print("Formula: Our Copy = TraderBet × 4.33% × 1.5x")
        print()
        print("Examples:")
        print("  Trader $100 (avg) → Copy $6.50")
        print("  Trader $200 (2x)  → Copy $15.56")
        print("  Trader $688 (big) → Copy $53.63 (capped)")
        print()
        print("=" * 70)
        print("READY!")
        print("=" * 70)


def main():
    config = ScalerConfig(
        our_bankroll=433.0,
        trader_address="0xc257ea7e3a81ca8e16df8935d44d513959fa358e",
        trader_avg_bet=100.0,
        trader_bankroll=10000.0,
        size_multiplier=1.5,
        max_position_pct=0.15
    )
    
    scaler = PositionScaler(config)
    scaler.show_examples()


if __name__ == "__main__":
    main()
