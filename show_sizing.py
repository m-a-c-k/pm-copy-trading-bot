#!/usr/bin/env python3
"""
Proportional Copy Trading Calculator - FollowMeABC123

Strategy:
- Trader's estimated bankroll: $10,000
- Our bankroll: $433
- Ratio: 4.33%

If trader bets $100 and his avg is $100 (100%):
  Our copy = $100 × 4.33% = $4.33

If trader bets $200 (200% of avg):
  Our copy = $200 × 4.33% × 2 = $17.32

If trader bets $25 (25% of avg):
  Our copy = $25 × 4.33% × 0.25 = $0.27 → minimum $1.00
"""

OUR_BANKROLL = 433.0
TRADER_BANKROLL = 10000.0
RATIO = OUR_BANKROLL / TRADER_BANKROLL  # 4.33%
MAX_TRADE = OUR_BANKROLL * 0.15  # 15% max

print("=" * 60)
print("PROPORTIONAL COPY TRADING - FollowMeABC123")
print("=" * 60)
print()
print(f"Our Bankroll:       ${OUR_BANKROLL:.2f}")
print(f"Trader Bankroll:     ${TRADER_BANKROLL:.2f}")
print(f"Proportional Ratio:  {RATIO*100:.2f}%")
print(f"Max Position:        ${MAX_TRADE:.2f}")
print()

print("Position Sizing Examples:")
print("-" * 60)
print(f"{'Trader Bet':<15} {'% of Avg':<12} {'Our Copy':<12} {'Notes'}")
print("-" * 60)

examples = [
    (25, 0.25),
    (50, 0.50),
    (100, 1.00),
    (150, 1.50),
    (200, 2.00),
    (500, 5.00),
]

for bet, pct in examples:
    # Calculate copy
    copy = bet * RATIO * pct
    copy = min(copy, MAX_TRADE)
    if copy < 1:
        copy = 1.0
    
    notes = ""
    if pct == 1.0:
        notes = "Average bet"
    elif pct > 1.5:
        notes = "Aggressive! 🔥"
    elif pct < 0.5:
        notes = "Small bet"
    
    print(f"${bet:<14} {pct*100:.0f}%{'':<8} ${copy:<11.2f} {notes}")

print("-" * 60)
print()
print("Formula: Our Copy = TraderBet × 4.33% × (% of Avg)")
print()
print("Example:")
print("  Trader bets $100 (100% of avg)")
print("  Our Copy = $100 × 4.33% = $4.33")
print()
print("  Trader bets $200 (200% of avg)")
print("  Our Copy = $200 × 4.33% × 2 = $17.32")
print()
print("=" * 60)
print("Ready to copy FollowMeABC123!")
print("=" * 60)
