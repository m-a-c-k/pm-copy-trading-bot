"""Tests for Risk Manager."""

import pytest
from src.services.risk_manager import RiskManager, RiskLevel, RiskCheckResult


class TestRiskManager:
    """Test cases for RiskManager."""
    
    def setup_method(self):
        """Set up risk manager for each test."""
        self.rm = RiskManager(bankroll=400.0)
    
    def test_normal_position_approved(self):
        """Test that normal positions are approved."""
        result = self.rm.check_position(
            trader_wallet="0xabc123",
            proposed_size=5.0,
            current_trader_pnl=100.0,
            trader_win_rate=0.62
        )
        
        assert result.approved is True
        assert result.final_position_size == 5.0
    
    def test_oversized_position_capped(self):
        """Test that oversized positions are capped."""
        result = self.rm.check_position(
            trader_wallet="0xabc123",
            proposed_size=50.0,  # 12.5% of bankroll
            current_trader_pnl=100.0,
            trader_win_rate=0.62
        )
        
        assert result.approved is True
        assert result.final_position_size == 8.0  # Max $8
        assert "exceeds max" in result.warnings[0].lower()
    
    def test_trader_exposure_limit(self):
        """Test per-trader exposure limit."""
        # Add $5 exposure to trader A (1.25%)
        self.rm.trader_exposures["0xtraderA"] = 1.25
        self.rm._update_total_exposure()
        
        # Try to add more
        result = self.rm.check_position(
            trader_wallet="0xtraderA",
            proposed_size=35.0,  # Would be 8.75%, total 10%
            current_trader_pnl=50.0,
            trader_win_rate=0.60
        )
        
        # Should be reduced to stay under 10%
        assert result.final_position_size < 35.0
        assert "exceed" in result.warnings[0].lower()
    
    def test_drawdown_reduction(self):
        """Test drawdown-based position reduction."""
        # Simulate 12% drawdown
        self.rm.update_bankroll(352.0, peak_bankroll=400.0)
        
        result = self.rm.check_position(
            trader_wallet="0xnewtrader",
            proposed_size=6.0,
            current_trader_pnl=0.0,
            trader_win_rate=0.60
        )
        
        # Position should be reduced
        assert result.final_position_size < 6.0
        assert "drawdown" in result.warnings[0].lower()
    
    def test_update_bankroll(self):
        """Test bankroll update and drawdown calculation."""
        # Initial state
        assert self.rm.bankroll == 400.0
        assert self.rm.current_drawdown == 0.0
        
        # After loss
        self.rm.update_bankroll(360.0)
        assert self.rm.bankroll == 360.0
        assert self.rm.current_drawdown == 10.0  # (400-360)/400*100
    
    def test_reset(self):
        """Test reset functionality."""
        self.rm.trader_exposures = {"0xtest": 5.0}
        self.rm.current_drawdown = 10.0
        
        self.rm.reset()
        
        assert self.rm.trader_exposures == {}
        assert self.rm.current_drawdown == 0.0
    
    def test_get_risk_summary(self):
        """Test risk summary generation."""
        self.rm.update_bankroll(380.0, peak_bankroll=400.0)
        
        summary = self.rm.get_risk_summary()
        
        assert summary["bankroll"] == 380.0
        assert summary["current_drawdown"] == 5.0
        assert abs(summary["max_trade_size"] - 7.6) < 0.01  # 2% of 380
        assert "trader_exposures" in summary
    
    def test_position_too_small_after_reduction(self):
        """Test skipping position if too small after reduction."""
        # High drawdown
        self.rm.update_bankroll(200.0, peak_bankroll=400.0)  # 50% drawdown
        
        result = self.rm.check_position(
            trader_wallet="0xtest",
            proposed_size=1.0,
            current_trader_pnl=0.0,
            trader_win_rate=0.60
        )
        
        # Should be rejected or very small
        assert result.final_position_size < 1.0 or result.approved is False
    
    def test_suggested_multiplier(self):
        """Test suggested multiplier calculation."""
        result = self.rm.check_position(
            trader_wallet="0xtest",
            proposed_size=4.0,  # Half of max $8
            trader_win_rate=0.60
        )
        
        assert result.suggested_multiplier == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
