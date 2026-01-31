"""Tests for Perfect Money Bridge."""

import pytest
from src.services.perfect_money_bridge import PerfectMoneyBridge, PMAccount, PMTransferResult


class TestPerfectMoneyBridge:
    """Test cases for PerfectMoneyBridge."""
    
    def setup_method(self):
        """Set up bridge for each test."""
        self.bridge = PerfectMoneyBridge(
            account_id="test_account",
            password="test_password"
        )
    
    def test_check_balance_not_configured(self):
        """Test balance check with test credentials."""
        account = self.bridge.check_balance()
        assert isinstance(account, PMAccount)
    
    def test_transfer_to_wallet_not_configured(self):
        """Test transfer without payee account configured."""
        bridge = PerfectMoneyBridge()
        result = bridge.transfer_to_wallet(
            amount=100.0,
            wallet_address="0x3854c129cd856ee518bf0661792e01ef1f2f586a"
        )
        assert isinstance(result, PMTransferResult)
        assert result.success is False
        assert "not configured" in result.message
    
    def test_estimate_gas_for_transfer(self):
        """Test gas estimation for transfers."""
        amount = 100.0
        total = self.bridge.estimate_gas_for_transfer(amount)
        expected_fee = amount * 0.015 + 1.0
        assert total == amount + expected_fee
    
    def test_get_bankroll_status(self):
        """Test bankroll status retrieval."""
        status = self.bridge.get_bankroll_status(current_polymarket_balance=400.0)
        assert "perfect_money" in status
        assert "polymarket" in status
        assert "total_bankroll" in status
        assert "allocation" in status
        assert "recommendation" in status
        assert status["polymarket"]["balance_usdc"] == 400.0
        assert status["total_bankroll"] == 400.0
    
    def test_reallocation_recommendation(self):
        """Test reallocation recommendations."""
        # High Polymarket balance (100% in Polymarket)
        status = self.bridge.get_bankroll_status(current_polymarket_balance=400.0)
        assert "withdrawing" in status["recommendation"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
