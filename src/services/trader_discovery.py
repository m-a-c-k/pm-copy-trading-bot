"""
Trader Discovery Module for PM Copy Trading Bot

Discovers and evaluates Polymarket traders to copy based on:
- Win rate (target 55-65%)
- Profit factor (>1.5)
- Max drawdown (<15%)
- Consistency over time
- PnL history
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv
import httpx

load_dotenv()


@dataclass
class TraderMetrics:
    """Performance metrics for a trader."""
    wallet_address: str
    pseudonym: str
    total_pnl: float
    win_rate: float
    total_trades: int
    profit_factor: float
    max_drawdown: float
    avg_position_size: float
    active_markets: int
    last_active: datetime
    risk_score: float  # 0-100, lower is better
    copy_score: float  # 0-100, higher is better
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "wallet_address": self.wallet_address,
            "pseudonym": self.pseudonym,
            "total_pnl": self.total_pnl,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "avg_position_size": self.avg_position_size,
            "active_markets": self.active_markets,
            "last_active": self.last_active.isoformat(),
            "risk_score": self.risk_score,
            "copy_score": self.copy_score
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TraderMetrics":
        """Create from dictionary."""
        return cls(
            wallet_address=data["wallet_address"],
            pseudonym=data["pseudonym"],
            total_pnl=data["total_pnl"],
            win_rate=data["win_rate"],
            total_trades=data["total_trades"],
            profit_factor=data["profit_factor"],
            max_drawdown=data["max_drawdown"],
            avg_position_size=data["avg_position_size"],
            active_markets=data["active_markets"],
            last_active=datetime.fromisoformat(data["last_active"]),
            risk_score=data["risk_score"],
            copy_score=data["copy_score"]
        )


@dataclass
class TraderDiscoveryResult:
    """Result from trader discovery search."""
    traders: list[TraderMetrics]
    total_analyzed: int
    qualified_count: int
    search_time_ms: float


class TraderDiscovery:
    """Discovers and evaluates traders to copy."""
    
    # Polymarket API endpoints
    POLYMARKET_API = "https://api.polymarket.com"
    POLYMARKET_ANALYTICS = "https://polymarketanalytics.com"
    
    def __init__(self, data_dir: str = "data/traders"):
        """
        Initialize trader discovery.
        
        Args:
            data_dir: Directory to store trader profiles
        """
        self.data_dir = data_dir
        self.session = httpx.AsyncClient(timeout=30.0)
        os.makedirs(data_dir, exist_ok=True)
    
    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()
    
    async def get_trader_from_api(self, wallet_address: str) -> Optional[dict]:
        """
        Fetch trader data from Polymarket API.
        
        Args:
            wallet_address: Trader's wallet address
            
        Returns:
            Trader data dictionary or None
        """
        try:
            # Get user activity/trades
            response = await self.session.get(
                f"{self.POLYMARKET_API}/api/core/users/{wallet_address}/activity",
                params={"limit": 100}
            )
            if response.status_code != 200:
                return None
            
            return response.json()
            
        except Exception:
            return None
    
    def calculate_risk_score(self, metrics: TraderMetrics) -> float:
        """
        Calculate risk score (0-100, lower is better).
        
        Factors:
        - Drawdown: Higher drawdown = higher risk
        - Win rate: Very high/low win rates may indicate cherry-picking
        - Trade count: Too few trades = less confidence
        - Consistency: Variable results = higher risk
        """
        risk_score = 0
        
        # Drawdown penalty (0-40 points)
        if metrics.max_drawdown > 30:
            risk_score += 40
        elif metrics.max_drawdown > 20:
            risk_score += 30
        elif metrics.max_drawdown > 15:
            risk_score += 20
        elif metrics.max_drawdown > 10:
            risk_score += 10
        else:
            risk_score += 0
        
        # Win rate anomaly penalty (0-20 points)
        if metrics.win_rate > 0.80 or metrics.win_rate < 0.40:
            risk_score += 20  # Suspiciously high or low
        elif metrics.win_rate > 0.70 or metrics.win_rate < 0.45:
            risk_score += 10  # Slightly unusual
        
        # Sample size penalty (0-20 points)
        if metrics.total_trades < 10:
            risk_score += 20
        elif metrics.total_trades < 50:
            risk_score += 10
        elif metrics.total_trades < 100:
            risk_score += 5
        
        # Inactivity penalty (0-20 points)
        days_inactive = (datetime.now() - metrics.last_active).days
        if days_inactive > 7:
            risk_score += 20
        elif days_inactive > 3:
            risk_score += 10
        elif days_inactive > 1:
            risk_score += 5
        
        return min(risk_score, 100)
    
    def calculate_copy_score(self, metrics: TraderMetrics) -> float:
        """
        Calculate copy score (0-100, higher is better).
        
        Ideal profile:
        - Win rate: 55-65%
        - Profit factor: >1.5
        - Drawdown: <15%
        - Active recently
        - Consistent trading history
        """
        score = 0
        
        # PnL contribution (0-30 points)
        if metrics.total_pnl > 10000:
            score += 30
        elif metrics.total_pnl > 1000:
            score += 20
        elif metrics.total_pnl > 100:
            score += 10
        elif metrics.total_pnl > 0:
            score += 5
        
        # Win rate contribution (0-25 points)
        if 0.55 <= metrics.win_rate <= 0.65:
            score += 25  # Ideal range
        elif 0.50 <= metrics.win_rate <= 0.70:
            score += 15  # Good range
        elif 0.45 <= metrics.win_rate <= 0.75:
            score += 10  # Acceptable
        
        # Profit factor contribution (0-20 points)
        if metrics.profit_factor > 2.0:
            score += 20
        elif metrics.profit_factor > 1.5:
            score += 15
        elif metrics.profit_factor > 1.2:
            score += 10
        elif metrics.profit_factor > 1.0:
            score += 5
        
        # Drawdown contribution (0-15 points)
        if metrics.max_drawdown < 10:
            score += 15
        elif metrics.max_drawdown < 15:
            score += 10
        elif metrics.max_drawdown < 20:
            score += 5
        
        # Activity contribution (0-10 points)
        if metrics.total_trades > 500:
            score += 10
        elif metrics.total_trades > 100:
            score += 7
        elif metrics.total_trades > 50:
            score += 5
        
        return min(score, 100)
    
    def evaluate_trader(
        self,
        wallet_address: str,
        total_pnl: float = 0.0,
        win_rate: float = 0.6,
        total_trades: int = 100,
        profit_factor: float = 1.5,
        max_drawdown: float = 10.0,
        avg_position_size: float = 100.0,
        active_markets: int = 5,
        pseudonym: str = "",
        last_active: Optional[datetime] = None
    ) -> TraderMetrics:
        """
        Evaluate a trader and calculate scores.
        
        Args:
            wallet_address: Trader's wallet address
            total_pnl: Total profit/loss
            win_rate: Win rate (0-1)
            total_trades: Total number of trades
            profit_factor: Gross profit / gross loss
            max_drawdown: Maximum drawdown percentage
            avg_position_size: Average position size
            active_markets: Number of active markets
            pseudonym: Trader's display name
            last_active: Last active timestamp
            
        Returns:
            TraderMetrics with evaluation scores
        """
        if last_active is None:
            last_active = datetime.now()
        
        metrics = TraderMetrics(
            wallet_address=wallet_address,
            pseudonym=pseudonym or wallet_address[:8],
            total_pnl=total_pnl,
            win_rate=win_rate,
            total_trades=total_trades,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            avg_position_size=avg_position_size,
            active_markets=active_markets,
            last_active=last_active,
            risk_score=0.0,
            copy_score=0.0
        )
        
        # Calculate scores
        metrics.risk_score = self.calculate_risk_score(metrics)
        metrics.copy_score = self.calculate_copy_score(metrics)
        
        return metrics
    
    def is_qualified_for_copying(self, metrics: TraderMetrics) -> bool:
        """
        Check if trader qualifies for copying.
        
        Criteria:
        - Copy score >= 50
        - Risk score <= 50
        - Win rate between 45-75%
        - Total trades >= 10
        - Active within last 7 days
        """
        return (
            metrics.copy_score >= 50 and
            metrics.risk_score <= 50 and
            0.45 <= metrics.win_rate <= 0.75 and
            metrics.total_trades >= 10 and
            (datetime.now() - metrics.last_active).days <= 7
        )
    
    def save_trader(self, metrics: TraderMetrics):
        """Save trader profile to file."""
        filepath = os.path.join(self.data_dir, f"{metrics.wallet_address}.json")
        with open(filepath, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)
    
    def load_trader(self, wallet_address: str) -> Optional[TraderMetrics]:
        """Load trader profile from file."""
        filepath = os.path.join(self.data_dir, f"{wallet_address}.json")
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r") as f:
            data = json.load(f)
        return TraderMetrics.from_dict(data)
    
    async def discover_top_traders(
        self,
        count: int = 10,
        min_trades: int = 50
    ) -> TraderDiscoveryResult:
        """
        Discover top traders from Polymarket.
        
        Args:
            count: Number of traders to return
            min_trades: Minimum trades required
            
        Returns:
            TraderDiscoveryResult with ranked traders
        """
        import time
        start_time = time.time()
        
        traders = []
        
        # For now, return example traders for testing
        # In production, would fetch from Polymarket Analytics API
        example_traders = [
            {
                "wallet": "0xabc123...",
                "pnl": 5000,
                "win_rate": 0.62,
                "trades": 200,
                "pf": 1.8,
                "drawdown": 8.5
            },
            {
                "wallet": "0xdef456...",
                "pnl": 2500,
                "win_rate": 0.58,
                "trades": 150,
                "pf": 1.5,
                "drawdown": 12.0
            }
        ]
        
        for t in example_traders:
            metrics = self.evaluate_trader(
                wallet_address=t["wallet"],
                total_pnl=t["pnl"],
                win_rate=t["win_rate"],
                total_trades=t["trades"],
                profit_factor=t["pf"],
                max_drawdown=t["drawdown"]
            )
            traders.append(metrics)
        
        # Sort by copy score
        traders.sort(key=lambda x: x.copy_score, reverse=True)
        
        search_time = (time.time() - start_time) * 1000
        qualified = [t for t in traders if self.is_qualified_for_copying(t)]
        
        return TraderDiscoveryResult(
            traders=traders[:count],
            total_analyzed=len(traders),
            qualified_count=len(qualified),
            search_time_ms=search_time
        )


# Quick test when run directly
if __name__ == "__main__":
    import asyncio
    
    async def test():
        print("Trader Discovery Test")
        print("=" * 50)
        
        discovery = TraderDiscovery()
        
        # Test 1: Evaluate a good trader
        good_trader = discovery.evaluate_trader(
            wallet_address="0x1234567890abcdef",
            total_pnl=5000.0,
            win_rate=0.62,
            total_trades=200,
            profit_factor=1.8,
            max_drawdown=8.5,
            pseudonym="ProfitableTrader"
        )
        
        print(f"Trader: {good_trader.pseudonym}")
        print(f"  PnL: ${good_trader.total_pnl:.2f}")
        print(f"  Win Rate: {good_trader.win_rate*100:.1f}%")
        print(f"  Profit Factor: {good_trader.profit_factor:.2f}")
        print(f"  Max Drawdown: {good_trader.max_drawdown:.1f}%")
        print(f"  Risk Score: {good_trader.risk_score:.1f}/100")
        print(f"  Copy Score: {good_trader.copy_score:.1f}/100")
        print(f"  Qualified: {discovery.is_qualified_for_copying(good_trader)}")
        print()
        
        # Test 2: Evaluate a risky trader
        risky_trader = discovery.evaluate_trader(
            wallet_address="0x9876543210fedcba",
            total_pnl=-500.0,
            win_rate=0.35,
            total_trades=20,
            profit_factor=0.6,
            max_drawdown=35.0,
            pseudonym="RiskyTrader"
        )
        
        print(f"Trader: {risky_trader.pseudonym}")
        print(f"  PnL: ${risky_trader.total_pnl:.2f}")
        print(f"  Win Rate: {risky_trader.win_rate*100:.1f}%")
        print(f"  Risk Score: {risky_trader.risk_score:.1f}/100")
        print(f"  Copy Score: {risky_trader.copy_score:.1f}/100")
        print(f"  Qualified: {discovery.is_qualified_for_copying(risky_trader)}")
        print()
        
        # Save good trader
        discovery.save_trader(good_trader)
        print(f"Saved {good_trader.pseudonym} to data/traders/")
        
        # Test discovery
        result = await discovery.discover_top_traders(count=5)
        print(f"\nDiscovery Results:")
        print(f"  Analyzed: {result.total_analyzed}")
        print(f"  Qualified: {result.qualified_count}")
        print(f"  Time: {result.search_time_ms:.1f}ms")
        
        await discovery.close()
    
    asyncio.run(test())
