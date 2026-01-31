"""Tests for Trader Discovery."""

import pytest
from datetime import datetime, timedelta
from src.services.trader_discovery import TraderDiscovery, TraderMetrics


class TestTraderDiscovery:
    """Test cases for TraderDiscovery."""
    
    def setup_method(self):
        """Set up discovery for each test."""
        self.discovery = TraderDiscovery()
    
    def test_evaluate_good_trader(self):
        """Test evaluating a good trader."""
        metrics = self.discovery.evaluate_trader(
            wallet_address="0xgood123",
            total_pnl=5000.0,
            win_rate=0.62,
            total_trades=200,
            profit_factor=1.8,
            max_drawdown=8.5,
            pseudonym="GoodTrader"
        )
        
        assert metrics.wallet_address == "0xgood123"
        assert metrics.total_pnl == 5000.0
        assert metrics.win_rate == 0.62
        assert metrics.risk_score < 30  # Should be low risk
        assert metrics.copy_score > 70  # Should be high copy score
    
    def test_evaluate_risky_trader(self):
        """Test evaluating a risky trader."""
        metrics = self.discovery.evaluate_trader(
            wallet_address="0xbadrandom",
            total_pnl=-500.0,
            win_rate=0.35,
            total_trades=20,
            profit_factor=0.6,
            max_drawdown=35.0,
            pseudonym="BadTrader"
        )
        
        assert metrics.risk_score > 50  # Should be high risk
        assert metrics.copy_score < 30  # Should be low copy score
    
    def test_is_qualified_for_copying_good(self):
        """Test good trader qualification."""
        metrics = self.discovery.evaluate_trader(
            wallet_address="0xqualified",
            total_pnl=1000.0,
            win_rate=0.60,
            total_trades=100,
            profit_factor=1.5,
            max_drawdown=12.0
        )
        
        assert self.discovery.is_qualified_for_copying(metrics) is True
    
    def test_is_qualified_for_copying_bad(self):
        """Test bad trader qualification."""
        metrics = self.discovery.evaluate_trader(
            wallet_address="0xunqualified",
            total_pnl=-100.0,
            win_rate=0.30,
            total_trades=5,
            profit_factor=0.5,
            max_drawdown=40.0,
            last_active=datetime.now() - timedelta(days=30)
        )
        
        assert self.discovery.is_qualified_for_copying(metrics) is False
    
    def test_trader_to_dict_and_from_dict(self):
        """Test trader serialization."""
        metrics = self.discovery.evaluate_trader(
            wallet_address="0xserialtest",
            total_pnl=2500.0,
            win_rate=0.58,
            total_trades=150,
            pseudonym="SerialTest"
        )
        
        data = metrics.to_dict()
        restored = TraderMetrics.from_dict(data)
        
        assert restored.wallet_address == metrics.wallet_address
        assert restored.total_pnl == metrics.total_pnl
        assert restored.win_rate == metrics.win_rate
        assert restored.pseudonym == metrics.pseudonym
    
    def test_calculate_risk_score(self):
        """Test risk score calculation."""
        # Low risk trader
        low_risk = self.discovery.evaluate_trader(
            wallet_address="0xlowrisk",
            total_pnl=1000,
            win_rate=0.60,
            total_trades=200,
            max_drawdown=5.0,
            last_active=datetime.now() - timedelta(hours=1)
        )
        assert low_risk.risk_score < 20
        
        # High risk trader
        high_risk = self.discovery.evaluate_trader(
            wallet_address="0xhighrisk",
            total_pnl=-500,
            win_rate=0.30,
            total_trades=5,
            max_drawdown=40.0,
            last_active=datetime.now() - timedelta(days=14)
        )
        assert high_risk.risk_score > 50
    
    def test_calculate_copy_score(self):
        """Test copy score calculation."""
        # Excellent trader
        excellent = self.discovery.evaluate_trader(
            wallet_address="0xexcellent",
            total_pnl=10000,
            win_rate=0.62,
            total_trades=500,
            profit_factor=2.0,
            max_drawdown=8.0
        )
        assert excellent.copy_score > 70
        
        # Poor trader
        poor = self.discovery.evaluate_trader(
            wallet_address="0xpoor",
            total_pnl=-1000,
            win_rate=0.40,
            total_trades=20,
            profit_factor=0.5,
            max_drawdown=30.0
        )
        assert poor.copy_score < 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
