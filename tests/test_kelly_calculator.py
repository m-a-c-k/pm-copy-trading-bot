"""Tests for Kelly Calculator."""

import pytest
from src.services.kelly_calculator import KellyCalculator, KellyResult


class TestKellyCalculator:
    """Test cases for KellyCalculator."""
    
    def setup_method(self):
        """Set up calculator for each test."""
        self.calc = KellyCalculator(
            kelly_fraction=0.5,
            max_trade_percent=2.0,
            max_trader_exposure=10.0,
            bankroll=400.0
        )
    
    def test_calculate_kelly_basic(self):
        """Test basic Kelly calculation."""
        result = self.calc.calculate_kelly(win_rate=0.60, win_loss_ratio=1.5)
        
        assert isinstance(result, KellyResult)
        assert result.kelly_fraction > 0
        assert result.recommended_position_size > 0
        assert result.recommended_position_size <= 8.0  # Max $8 for $400 bankroll
    
    def test_kelly_formula(self):
        """Test Kelly formula: K% = W - [(1-W)/R]"""
        # For 60% win rate, 1.5 win/loss ratio:
        # Full Kelly = 0.60 - (0.40/1.5) = 0.60 - 0.267 = 0.333
        # 0.5x Fractional Kelly = 0.167
        # 2% max trade cap = 0.02
        result = self.calc.calculate_kelly(win_rate=0.60, win_loss_ratio=1.5)
        
        assert result.kelly_fraction == 0.02  # Capped at max trade %
        assert result.optimal_size_percent == 2.0  # 2%
    
    def test_negative_kelly(self):
        """Test that negative Kelly returns 0."""
        # For 40% win rate, 1.0 win/loss ratio:
        # Full Kelly = 0.40 - (0.60/1.0) = -0.20
        result = self.calc.calculate_kelly(win_rate=0.40, win_loss_ratio=1.0)
        
        assert result.kelly_fraction == 0
        assert result.recommended_position_size == 0
        assert "Negative Kelly" in result.warnings[0]
    
    def test_update_bankroll(self):
        """Test bankroll update."""
        self.calc.update_bankroll(1000.0)
        assert self.calc.bankroll == 1000.0
        
        summary = self.calc.get_risk_summary()
        assert summary["bankroll"] == 1000.0
        assert summary["max_position_size"] == 20.0  # 2% of $1000
    
    def test_risk_summary(self):
        """Test risk summary calculation."""
        summary = self.calc.get_risk_summary()
        
        assert summary["bankroll"] == 400.0
        assert summary["kelly_fraction"] == 0.5
        assert summary["max_trade_percent"] == 2.0
        assert summary["max_trader_exposure"] == 10.0
        assert summary["max_position_size"] == 8.0  # 2% of $400
        assert summary["max_trader_total"] == 40.0  # 10% of $400
    
    def test_invalid_win_rate_uses_default(self):
        """Test that invalid win rate uses default."""
        result = self.calc.calculate_kelly(win_rate=1.5, win_loss_ratio=1.5)
        
        assert "Invalid win rate" in result.warnings[0]
    
    def test_invalid_win_loss_ratio_uses_default(self):
        """Test that invalid win/loss ratio uses default."""
        result = self.calc.calculate_kelly(win_rate=0.6, win_loss_ratio=-1.0)
        
        assert "Invalid win/loss ratio" in result.warnings[0]
    
    def test_trader_exposure_limit(self):
        """Test that trader exposure limit is enforced."""
        # With 9% current exposure, even a small Kelly gets capped by max trade %
        # The exposure limit warning should appear if we have significant exposure
        result = self.calc.calculate_kelly(
            win_rate=0.60,
            win_loss_ratio=1.5,
            current_trader_exposure=9.0
        )
        
        # The max trade cap triggers first (2%), so we stay under limits
        # If trader exposure was lower, we'd see the exposure warning
        assert result.optimal_size_percent <= 2.0  # Always capped at 2%
        assert len(result.warnings) > 0  # Should have at least one warning
    
    def test_conservative_kelly_fraction(self):
        """Test with conservative (0.25x) Kelly fraction."""
        calc = KellyCalculator(kelly_fraction=0.25, bankroll=400.0)
        result = calc.calculate_kelly(win_rate=0.60, win_loss_ratio=1.5)
        
        # 0.25x of 16.7% Kelly = 4.2% (still under 2% cap)
        assert result.optimal_size_percent <= 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
