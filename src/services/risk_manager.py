"""
Risk Management Module for PM Copy Trading Bot

Enforces position limits, drawdown protection, and exposure management:
- 2% max per trade
- 10% max per trader
- 30% max total exposure
- Drawdown-based position reduction
- Automatic stop-loss triggers
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """Risk level classification."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskCheckResult:
    """Result of a risk check."""
    approved: bool
    risk_level: RiskLevel
    position_size: float
    warnings: list[str]
    final_position_size: float
    suggested_multiplier: float


class RiskManager:
    """Manages risk for copy trading operations."""
    
    def __init__(
        self,
        max_trade_percent: float = 2.0,
        max_trader_exposure: float = 10.0,
        max_total_exposure: float = 30.0,
        max_drawdown_percent: float = 15.0,
        drawdown_reduction_factor: float = 0.5,
        bankroll: float = 400.0
    ):
        """
        Initialize risk manager.
        
        Args:
            max_trade_percent: Max % of bankroll per trade (2.0 = 2%)
            max_trader_exposure: Max % per trader (10.0 = 10%)
            max_total_exposure: Max total % exposed (30.0 = 30%)
            max_drawdown_percent: Max drawdown before reducing positions
            drawdown_reduction_factor: Factor to reduce positions during drawdown
            bankroll: Total bankroll in USDC
        """
        self.max_trade_percent = max_trade_percent
        self.max_trader_exposure = max_trader_exposure
        self.max_total_exposure = max_total_exposure
        self.max_drawdown_percent = max_drawdown_percent
        self.drawdown_reduction_factor = drawdown_reduction_factor
        self.bankroll = bankroll
        
        # Track current state
        self.trader_exposures: dict[str, float] = {}  # wallet -> % exposure
        self.current_drawdown: float = 0.0
        self.peak_bankroll: float = bankroll
        self.current_exposure_percent: float = 0.0
    
    def check_position(
        self,
        trader_wallet: str,
        proposed_size: float,
        current_trader_pnl: float = 0.0,
        trader_win_rate: float = 0.6
    ) -> RiskCheckResult:
        """
        Check if a position is within risk limits.
        
        Args:
            trader_wallet: Trader's wallet address
            proposed_size: Proposed position size in USDC
            current_trader_pnl: Current PnL from this trader
            trader_win_rate: Trader's win rate
            
        Returns:
            RiskCheckResult with approval and modifications
        """
        warnings = []
        max_size = (self.max_trade_percent / 100) * self.bankroll
        
        # Check 1: Max per trade
        if proposed_size > max_size:
            warnings.append(
                f"Proposed ${proposed_size:.2f} exceeds max ${max_size:.2f} per trade"
            )
            proposed_size = max_size
        
        # Check 2: Per-trader exposure
        current_exposure = self.trader_exposures.get(trader_wallet, 0.0)
        potential_exposure = current_exposure + (proposed_size / self.bankroll * 100)
        
        if potential_exposure > self.max_trader_exposure:
            available = self.max_trader_exposure - current_exposure
            available_size = (available / 100) * self.bankroll
            warnings.append(
                f"Would exceed max {self.max_trader_exposure}% per trader, "
                f"reducing to ${available_size:.2f}"
            )
            proposed_size = available_size
            potential_exposure = self.max_trader_exposure
        
        # Check 3: Total exposure
        total_exposure = self.current_exposure_percent + (proposed_size / self.bankroll * 100)
        if total_exposure > self.max_total_exposure:
            available = self.max_total_exposure - self.current_exposure_percent
            available_size = (available / 100) * self.bankroll
            warnings.append(
                f"Would exceed max {self.max_total_exposure}% total exposure, "
                f"reducing to ${available_size:.2f}"
            )
            proposed_size = available_size
            total_exposure = self.max_total_exposure
        
        # Check 4: Drawdown-based reduction
        if self.current_drawdown > 0:
            drawdown_ratio = self.current_drawdown / self.max_drawdown_percent
            if drawdown_ratio > 0.5:  # More than 50% of max drawdown
                reduction = 1.0 - (self.drawdown_reduction_factor * drawdown_ratio)
                original_size = proposed_size
                proposed_size = proposed_size * reduction
                warnings.append(
                    f"Drawdown {self.current_drawdown:.1f}% - reducing position by {(1-reduction)*100:.0f}%"
                )
                if proposed_size < 1.0:
                    warnings.append("Position too small after reduction - skipping trade")
                    return RiskCheckResult(
                        approved=False,
                        risk_level=RiskLevel.CRITICAL,
                        position_size=0.0,
                        warnings=warnings,
                        final_position_size=0.0,
                        suggested_multiplier=0.0
                    )
        
        # Determine risk level
        risk_level = self._calculate_risk_level(
            proposed_size, trader_win_rate, current_trader_pnl
        )
        
        # Calculate suggested multiplier for position sizing
        suggested_multiplier = proposed_size / max_size
        
        return RiskCheckResult(
            approved=True,
            risk_level=risk_level,
            position_size=proposed_size,
            warnings=warnings,
            final_position_size=proposed_size,
            suggested_multiplier=suggested_multiplier
        )
    
    def _calculate_risk_level(
        self,
        position_size: float,
        win_rate: float,
        pnl: float
    ) -> RiskLevel:
        """Calculate risk level for a position."""
        size_percent = (position_size / self.bankroll) * 100
        
        # Size-based risk
        if size_percent > 1.5:
            size_risk = RiskLevel.HIGH
        elif size_percent > 1.0:
            size_risk = RiskLevel.MEDIUM
        else:
            size_risk = RiskLevel.LOW
        
        # Win rate risk
        if win_rate < 0.45:
            win_risk = RiskLevel.HIGH
        elif win_rate > 0.70:
            win_risk = RiskLevel.MEDIUM  # Suspiciously high
        else:
            win_risk = RiskLevel.LOW
        
        # PnL risk
        if pnl < -100:
            pnl_risk = RiskLevel.HIGH
        elif pnl < 0:
            pnl_risk = RiskLevel.MEDIUM
        else:
            pnl_risk = RiskLevel.LOW
        
        # Return highest risk
        risks = [size_risk, win_risk, pnl_risk]
        if RiskLevel.CRITICAL in risks:
            return RiskLevel.CRITICAL
        elif RiskLevel.HIGH in risks:
            return RiskLevel.HIGH
        elif RiskLevel.MEDIUM in risks:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def update_bankroll(self, new_bankroll: float, peak_bankroll: Optional[float] = None):
        """Update bankroll and calculate drawdown."""
        self.bankroll = new_bankroll
        
        if peak_bankroll:
            self.peak_bankroll = peak_bankroll
        else:
            self.peak_bankroll = max(self.peak_bankroll, new_bankroll)
        
        if self.peak_bankroll > 0:
            self.current_drawdown = (
                (self.peak_bankroll - new_bankroll) / self.peak_bankroll * 100
            )
    
    def add_trader_exposure(self, trader_wallet: str, amount: float):
        """Add exposure for a trader."""
        current = self.trader_exposures.get(trader_wallet, 0.0)
        self.trader_exposures[trader_wallet] = current + (amount / self.bankroll * 100)
        self._update_total_exposure()
    
    def remove_trader_exposure(self, trader_wallet: str, amount: float):
        """Remove exposure for a trader."""
        current = self.trader_exposures.get(trader_wallet, 0.0)
        self.trader_exposures[trader_wallet] = max(0.0, current - (amount / self.bankroll * 100))
        self._update_total_exposure()
    
    def _update_total_exposure(self):
        """Update total exposure percentage."""
        self.current_exposure_percent = sum(self.trader_exposures.values())
    
    def get_risk_summary(self) -> dict:
        """Get complete risk summary."""
        return {
            "bankroll": self.bankroll,
            "current_drawdown": self.current_drawdown,
            "peak_bankroll": self.peak_bankroll,
            "max_trade_percent": self.max_trade_percent,
            "max_trade_size": (self.max_trade_percent / 100) * self.bankroll,
            "max_trader_exposure": self.max_trader_exposure,
            "max_total_exposure": self.max_total_exposure,
            "current_total_exposure": self.current_exposure_percent,
            "trader_exposures": dict(self.trader_exposures),
            "risk_level": self._get_overall_risk_level().value
        }
    
    def _get_overall_risk_level(self) -> RiskLevel:
        """Get overall portfolio risk level."""
        if self.current_drawdown > self.max_drawdown_percent * 0.8:
            return RiskLevel.CRITICAL
        elif self.current_drawdown > self.max_drawdown_percent * 0.5:
            return RiskLevel.HIGH
        elif self.current_exposure_percent > self.max_total_exposure * 0.8:
            return RiskLevel.HIGH
        elif self.current_exposure_percent > self.max_total_exposure * 0.5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW
    
    def reset(self):
        """Reset all risk tracking."""
        self.trader_exposures = {}
        self.current_drawdown = 0.0
        self.peak_bankroll = self.bankroll
        self.current_exposure_percent = 0.0


# Quick test when run directly
if __name__ == "__main__":
    print("Risk Manager Test")
    print("=" * 50)
    
    rm = RiskManager(bankroll=400.0)
    
    print(f"Bankroll: ${rm.bankroll}")
    print(f"Max per trade: ${(rm.max_trade_percent/100)*rm.bankroll:.2f}")
    print(f"Max per trader: ${(rm.max_trader_exposure/100)*rm.bankroll:.2f}")
    print(f"Max total exposure: ${(rm.max_total_exposure/100)*rm.bankroll:.2f}")
    print()
    
    # Test 1: Normal position
    result = rm.check_position(
        trader_wallet="0xabc123",
        proposed_size=5.0,
        current_trader_pnl=100.0,
        trader_win_rate=0.62
    )
    print(f"Test 1: Normal $5 position")
    print(f"  Approved: {result.approved}")
    print(f"  Risk Level: {result.risk_level.value}")
    print(f"  Final Size: ${result.final_position_size:.2f}")
    print(f"  Multiplier: {result.suggested_multiplier:.2f}x")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    print()
    
    # Test 2: Oversized position
    result = rm.check_position(
        trader_wallet="0xabc123",
        proposed_size=50.0,  # 12.5% of bankroll
        current_trader_pnl=100.0,
        trader_win_rate=0.62
    )
    print(f"Test 2: Oversized $50 position")
    print(f"  Approved: {result.approved}")
    print(f"  Final Size: ${result.final_position_size:.2f}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    print()
    
    # Test 3: High drawdown
    rm.update_bankroll(350.0, peak_bankroll=400.0)  # 12.5% drawdown
    print(f"Drawdown: {rm.current_drawdown:.1f}%")
    result = rm.check_position(
        trader_wallet="0xdef456",
        proposed_size=10.0,
        current_trader_pnl=50.0,
        trader_win_rate=0.60
    )
    print(f"Test 3: $10 position during 12.5% drawdown")
    print(f"  Final Size: ${result.final_position_size:.2f}")
    if result.warnings:
        print(f"  Warnings: {result.warnings}")
    print()
    
    print("Risk Summary:")
    print(rm.get_risk_summary())
