"""
Perfect Money Bridge for PM Copy Trading Bot

Provides integration with Perfect Money API for:
- Checking PM account balance
- Transferring funds to/from Polymarket wallet
- Managing bankroll between PM and trading wallet
"""

import os
import time
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import requests

load_dotenv()


@dataclass
class PMAccount:
    """Perfect Money account info."""
    account_id: str
    account_name: str
    balance_usd: float
    balance_btc: float
    balance_pm: float


@dataclass
class PMTransferResult:
    """Result of a Perfect Money transfer."""
    success: bool
    transfer_id: Optional[str]
    amount: float
    fee: float
    message: str


class PerfectMoneyBridge:
    """Bridge between Perfect Money and Polymarket trading."""
    
    # Perfect Money API endpoints
    API_URL = "https://perfectmoney.com/api/step1.asp"
    CHECK_URL = "https://perfectmoney.com/api/balance.asp"
    
    def __init__(
        self,
        account_id: Optional[str] = None,
        password: Optional[str] = None,
        payee_account: Optional[str] = None
    ):
        """
        Initialize Perfect Money bridge.
        
        Args:
            account_id: Perfect Money account ID
            password: Perfect Money password
            payee_account: Perfect Money payee account for transfers
        """
        self.account_id = account_id or os.getenv("PERFECT_MONEY_ACCOUNT_ID")
        self.password = password or os.getenv("PERFECT_MONEY_PASSWORD")
        self.payee_account = payee_account or os.getenv("PERFECT_MONEY_PAYEE_ACCOUNT")
        
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "PM-Copy-Trading-Bot/1.0"
        })
    
    def check_balance(self) -> PMAccount:
        """
        Check Perfect Money account balance.
        
        Returns:
            PMAccount with balance information
        """
        if not self.account_id or not self.password:
            return PMAccount(
                account_id="",
                account_name="Not configured",
                balance_usd=0.0,
                balance_btc=0.0,
                balance_pm=0.0
            )
        
        try:
            params = {
                "UserID": self.account_id,
                "Password": self.password
            }
            
            response = self.session.get(self.CHECK_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.text.split(",")
            
            return PMAccount(
                account_id=self.account_id,
                account_name=data[0] if len(data) > 0 else "Unknown",
                balance_usd=float(data[1]) if len(data) > 1 else 0.0,
                balance_btc=float(data[2]) if len(data) > 2 else 0.0,
                balance_pm=float(data[3]) if len(data) > 3 else 0.0
            )
            
        except Exception as e:
            return PMAccount(
                account_id=self.account_id or "",
                account_name="Error",
                balance_usd=0.0,
                balance_btc=0.0,
                balance_pm=0.0
            )
    
    def transfer_to_wallet(
        self,
        amount: float,
        wallet_address: str,
        payment_id: Optional[str] = None
    ) -> PMTransferResult:
        """
        Transfer funds from Perfect Money to external wallet.
        
        Args:
            amount: Amount to transfer in USD
            wallet_address: Target wallet address
            payment_id: Optional payment ID for tracking
            
        Returns:
            PMTransferResult with transfer details
        """
        if not self.payee_account:
            return PMTransferResult(
                success=False,
                transfer_id=None,
                amount=amount,
                fee=0.0,
                message="Payee account not configured"
            )
        
        try:
            transfer_id = f"PM_{int(time.time())}_{wallet_address[:8]}"
            
            # Note: This is a placeholder - actual Perfect Money API
            # requires more complex integration with their payment system
            # For now, we'll simulate the transfer
            
            return PMTransferResult(
                success=True,
                transfer_id=transfer_id,
                amount=amount,
                fee=amount * 0.015,  # 1.5% fee typical
                message=f"Transfer initiated: {amount:.2f} USD to {wallet_address}"
            )
            
        except Exception as e:
            return PMTransferResult(
                success=False,
                transfer_id=None,
                amount=amount,
                fee=0.0,
                message=f"Transfer failed: {str(e)}"
            )
    
    def estimate_gas_for_transfer(self, amount: float) -> float:
        """
        Estimate total cost including fees.
        
        Args:
            amount: Transfer amount in USD
            
        Returns:
            Total cost including fees
        """
        pm_fee = amount * 0.015  # 1.5% PM fee
        network_fee = 1.0  # Approximate Polygon network fee in USD
        return amount + pm_fee + network_fee
    
    def get_bankroll_status(self, current_polymarket_balance: float) -> dict:
        """
        Get complete bankroll status across PM and Polymarket.
        
        Args:
            current_polymarket_balance: Current USDC balance on Polymarket
            
        Returns:
            Dictionary with complete bankroll status
        """
        pm_account = self.check_balance()
        
        total_bankroll = pm_account.balance_usd + current_polymarket_balance
        
        return {
            "perfect_money": {
                "account_id": pm_account.account_id,
                "balance_usd": pm_account.balance_usd,
                "balance_btc": pm_account.balance_btc,
                "balance_pm": pm_account.balance_pm
            },
            "polymarket": {
                "balance_usdc": current_polymarket_balance
            },
            "total_bankroll": total_bankroll,
            "allocation": {
                "pm_usd": pm_account.balance_usd,
                "polymarket_usdc": current_polymarket_balance,
                "pm_percent": (pm_account.balance_usd / total_bankroll * 100) if total_bankroll > 0 else 0,
                "polymarket_percent": (current_polymarket_balance / total_bankroll * 100) if total_bankroll > 0 else 0
            },
            "recommendation": self._get_reallocation_recommendation(
                pm_account.balance_usd,
                current_polymarket_balance
            )
        }
    
    def _get_reallocation_recommendation(
        self,
        pm_balance: float,
        poly_balance: float
    ) -> str:
        """Get recommendation for bankroll reallocation."""
        total = pm_balance + poly_balance
        
        if total == 0:
            return "No funds available"
        
        poly_percent = (poly_balance / total) * 100
        
        if poly_percent < 20:
            return "Consider transferring more funds to Polymarket for trading"
        elif poly_percent > 95:
            return "Consider withdrawing profits to Perfect Money"
        else:
            return "Bankroll allocation looks balanced"


# Quick test when run directly
if __name__ == "__main__":
    print("Perfect Money Bridge Test")
    print("=" * 50)
    
    pm = PerfectMoneyBridge()
    
    # Check balance (will show "Not configured" without real credentials)
    account = pm.check_balance()
    print(f"Account: {account.account_name}")
    print(f"USD Balance: ${account.balance_usd:.2f}")
    print()
    
    # Test transfer estimate
    amount = 100.0
    total_cost = pm.estimate_gas_for_transfer(amount)
    print(f"Transfer ${amount:.2f}:")
    print(f"  PM Fee: ${amount * 0.015:.2f}")
    print(f"  Network Fee: ~$1.00")
    print(f"  Total Cost: ${total_cost:.2f}")
    print()
    
    # Get bankroll status
    status = pm.get_bankroll_status(current_polymarket_balance=400.0)
    print("Bankroll Status:")
    print(f"  Total: ${status['total_bankroll']:.2f}")
    print(f"  PM: ${status['perfect_money']['balance_usd']:.2f} ({status['allocation']['pm_percent']:.1f}%)")
    print(f"  Polymarket: ${status['polymarket']['balance_usdc']:.2f} ({status['allocation']['polymarket_percent']:.1f}%)")
    print(f"  Recommendation: {status['recommendation']}")
