"""
Recommended Traders to Copy

Based on Polymarket leaderboard analysis. These traders show:
- Consistent profitability (monthly/weekly)
- Active trading frequency
- Sports-focused trading

To add a trader:
1. Get their wallet address from Polymarket profile
2. Add to config Traders: ["0x...", "0x..."]
3. Restart the bot

Traders are evaluated on:
- Profit consistency
- Trading frequency (not too high, not too low)
- Sports specialization
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TraderConfig:
    address: str
    name: Optional[str] = None
    max_trades_per_day: Optional[int] = None
    min_trade_size: Optional[float] = None
    disabled: bool = False
    reason: Optional[str] = None


# Recommended traders - ADD YOUR WHALE HERE
# Format: "0x..." address
# Selected from Sports Leaderboard: Moderate volume, consistent profitability
TRADERS = [
    TraderConfig(
        address="0xc257ea7e3a81ca8e16df8935d44d513959fa358e",
        name="FollowMeABC123",
        reason="Your identified whale - frequent sports trader"
    ),
    TraderConfig(
        address="0xaa075924e1dc7cff3b9fab67401126338c4d2125",
        name="rustin",
        reason="Sports: +$207K profit, $313K vol - top consistent performer"
    ),
    TraderConfig(
        address="0x3b5c629f114098b0dee345fb78b7a3a013c7126e",
        name="SMCAOMCRL",
        reason="Sports: +$86K profit, $1.8M vol - high activity trader"
    ),
    TraderConfig(
        address="0xafbacaeeda63f31202759eff7f8126e49adfe61b",
        name="NewTrader",
        reason="Added from leaderboard - sports trader"
    ),
]

# Traders to monitor (not yet approved)
PENDING_TRADERS = [
    # Add traders you want to evaluate here
    # Example:
    # TraderConfig(
    #     address="0x...",
    #     name="TraderName",
    #     reason="Found on leaderboard - needs evaluation"
    # ),
]


def get_active_traders() -> List[str]:
    """Get list of active trader addresses."""
    return [t.address for t in TRADERS if not t.disabled]


def get_trader_info(address: str) -> Optional[TraderConfig]:
    """Get config for a specific trader."""
    for t in TRADERS:
        if t.address.lower() == address.lower():
            return t
    return None


def is_trader_approved(address: str) -> bool:
    """Check if a trader is in the approved list."""
    return any(
        t.address.lower() == address.lower() and not t.disabled
        for t in TRADERS
    )


if __name__ == "__main__":
    print("=== Recommended Traders to Copy ===")
    print(f"Active traders: {len(get_active_traders())}")
    for t in TRADERS:
        status = "✓" if not t.disabled else "✗"
        print(f"{status} {t.name or t.address[:16]}... - {t.reason}")

    print(f"\nPending evaluation: {len(PENDING_TRADERS)}")
