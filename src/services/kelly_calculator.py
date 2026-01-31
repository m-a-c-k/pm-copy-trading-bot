"""
Kelly Criterion Calculator for Position Sizing

Implements fractional Kelly Criterion for smart position sizing based on:
- Win rate (probability of winning)
- Win/Loss ratio (average win / average loss)
- Kelly fraction (conservative, moderate, aggressive)
- Risk management rules (2% per trade max)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class KellyResult:
    """Result from Kelly calculation."""
    kelly_fraction: float
    optimal_size_percent: float
    recommended_position_size: float
    warnings: list[str]


class KellyCalculator:
    """Calculates optimal position sizes using Kelly Criterion."""
    
    def __init__(
        self,
        kelly_fraction: float = 0.5,
        max_trade_percent: float = 2.0,
        max_trader_exposure: float = 10.0,
        bankroll: float = 400.0
    ):
        """
        Initialize Kelly calculator.
        
        Args:
            kelly_fraction: Fraction of Kelly to use (0.25=conservative, 0.5=moderate, 0.75=aggressive)
            max_trade_percent: Maximum % of bankroll per trade (2.0 = 2%)
            max_trader_exposure: Maximum % of bankroll per trader (10.0 = 10%)
            bankroll: Total bankroll in USDC
        """
        self.kelly_fraction = kelly_fraction
        self.max_trade_percent = max_trade_percent
        self.max_trader_exposure = max_trader_exposure
        self.bankroll = bankroll
    
    def calculate_kelly(
        self,
        win_rate: float,
        win_loss_ratio: float,
        trader_size: float = 0.0,
        current_trader_exposure: float = 0.0
    ) -> KellyResult:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Formula: Kelly % = W - [(1-W)/R]
        Where:
            W = Win rate probability (e.g., 0.60)
            R = Win/Loss ratio (e.g., 1.5)
        
        Args:
            win_rate: Probability of winning (0.0 to 1.0)
            win_loss_ratio: Average win / average loss (e.g., 1.5)
            trader_size: Size of the trader's position we're copying
            current_trader_exposure: Current exposure to this trader
            
        Returns:
            KellyResult with position size recommendations
        """
        warnings = []
        
        # Validate inputs
        if win_rate < 0 or win_rate > 1:
            warnings.append(f"Invalid win rate {win_rate}, using 0.6 default")
            win_rate = 0.6
        
        if win_loss_ratio <= 0:
            warnings.append(f"Invalid win/loss ratio {win_loss_ratio}, using 1.5 default")
            win_loss_ratio = 1.5
        
        # Calculate full Kelly
        full_kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        
        # Apply Kelly fraction
        kelly_fraction_used = full_kelly * self.kelly_fraction
        
        # Calculate optimal position size
        optimal_size_percent = kelly_fraction_used * 100  # As percentage
        
        # Apply max trade limit
        if optimal_size_percent > self.max_trade_percent:
            warnings.append(
                f"Kelly size {optimal_size_percent:.1f}% exceeds max {self.max_trade_percent}%, "
                f"capping at {self.max_trade_percent}%"
            )
            optimal_size_percent = self.max_trade_percent
            kelly_fraction_used = self.max_trade_percent / 100
        
        # Apply trader exposure limit
        potential_exposure = current_trader_exposure + optimal_size_percent
        if potential_exposure > self.max_trader_exposure:
            available = self.max_trader_exposure - current_trader_exposure
            warnings.append(
                f"Would exceed max trader exposure {self.max_trader_exposure}%, "
                f"reducing to {available:.1f}%"
            )
            optimal_size_percent = available
            kelly_fraction_used = available / 100
        
        # Handle negative Kelly (don't trade)
        if kelly_fraction_used < 0:
            warnings.append("Negative Kelly -不建议交易 (Not recommended to trade)")
            kelly_fraction_used = 0
            optimal_size_percent = 0
        
        # Calculate actual position size in USDC
        recommended_size = (optimal_size_percent / 100) * self.bankroll
        
        # For copying trades, also calculate based on trader size
        if trader_size > 0:
            copy_ratio = recommended_size / trader_size
            if copy_ratio > 1.5:
                warnings.append(
                    f"Copy ratio {copy_ratio:.2f}x is high - we're sizing larger than trader"
                )
            elif copy_ratio < 0.5:
                warnings.append(
                    f"Copy ratio {copy_ratio:.2f}x is low - we're sizing much smaller than trader"
                )
        
        return KellyResult(
            kelly_fraction=kelly_fraction_used,
            optimal_size_percent=optimal_size_percent,
            recommended_position_size=round(recommended_size, 2),
            warnings=warnings
        )
    
    def calculate_for_polymarket(
        self,
        trader_pnl: float,
        trader_win_rate: float,
        trader_trade_count: int,
        your_bankroll: Optional[float] = None
    ) -> KellyResult:
        """
        Calculate position size for Polymarket copy trading.
        
        Uses trader's actual performance metrics to estimate Kelly.
        
        Args:
            trader_pnl: Trader's total PnL
            trader_win_rate: Trader's win rate (0-1)
            trader_trade_count: Total number of trades
            your_bankroll: Your bankroll (uses default if not provided)
        """
        if your_bankroll:
            self.bankroll = your_bankroll
        
        # Estimate win/loss ratio from PnL and win rate
        if trader_trade_count > 0 and trader_win_rate > 0:
            estimated_wins = trader_pnl if trader_pnl > 0 else abs(trader_pnl)
            estimated_losses = trader_pnl if trader_pnl < 0 else abs(trader_pnl)
            
            if trader_win_rate < 1 and trader_win_rate > 0:
                win_loss_ratio = (estimated_wins * trader_win_rate) / (
                    estimated_losses * (1 - trader_win_rate)
                )
                win_loss_ratio = max(win_loss_ratio, 0.5)  # Minimum 0.5
            else:
                win_loss_ratio = 1.5  # Default
        else:
            win_loss_ratio = 1.5
            trader_win_rate = 0.6  # Default to 60% if unknown
        
        return self.calculate_kelly(
            win_rate=trader_win_rate,
            win_loss_ratio=win_loss_ratio
        )
    
    def update_bankroll(self, new_bankroll: float):
        """Update the bankroll amount."""
        self.bankroll = new_bankroll
    
    def get_risk_summary(self) -> dict:
        """Get current risk settings summary."""
        return {
            "bankroll": self.bankroll,
            "kelly_fraction": self.kelly_fraction,
            "max_trade_percent": self.max_trade_percent,
            "max_trader_exposure": self.max_trader_exposure,
            "max_position_size": (self.max_trade_percent / 100) * self.bankroll,
            "max_trader_total": (self.max_trader_exposure / 100) * self.bankroll
        }


# Quick test when run directly
if __name__ == "__main__":
    calc = KellyCalculator(
        kelly_fraction=0.5,  # Moderate
        max_trade_percent=2.0,  # 2% max per trade
        bankroll=400.0  # $400 bankroll
    )
    
    print("Kelly Calculator Test")
    print("=" * 50)
    print(f"Bankroll: ${calc.bankroll}")
    print(f"Kelly Fraction: {calc.kelly_fraction}x")
    print(f"Max Trade: {calc.max_trade_percent}%")
    print()
    
    # Test case 1: 60% win rate, 1.5 win/loss ratio
    result = calc.calculate_kelly(win_rate=0.60, win_loss_ratio=1.5)
    print(f"Test 1: 60% WR, 1.5 W/L ratio")
    print(f"  Kelly: {result.kelly_fraction:.3f} ({result.kelly_fraction * 100:.1f}%)")
    print(f"  Position Size: ${result.recommended_position_size:.2f}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    print()
    
    # Test case 2: 55% win rate, 1.2 win/loss ratio
    result = calc.calculate_kelly(win_rate=0.55, win_loss_ratio=1.2)
    print(f"Test 2: 55% WR, 1.2 W/L ratio")
    print(f"  Kelly: {result.kelly_fraction:.3f} ({result.kelly_fraction * 100:.1f}%)")
    print(f"  Position Size: ${result.recommended_position_size:.2f}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    print()
    
    # Test case 3: 70% win rate, 2.0 win/loss ratio (excellent trader)
    result = calc.calculate_kelly(win_rate=0.70, win_loss_ratio=2.0)
    print(f"Test 3: 70% WR, 2.0 W/L ratio (excellent)")
    print(f"  Kelly: {result.kelly_fraction:.3f} ({result.kelly_fraction * 100:.1f}%)")
    print(f"  Position Size: ${result.recommended_position_size:.2f}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    print()
    
    print("Risk Summary:")
    print(calc.get_risk_summary())
