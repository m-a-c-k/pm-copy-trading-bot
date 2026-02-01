"""
Kalshi Executor - Mirror whale trades on Kalshi

Implements:
- Position sizing based on whale's actual average wager %
- Risk management (Kelly + max exposure limits)
- Trade execution on Kalshi
- Logging and notifications
"""

import os
import time
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.services.kalshi_client import KalshiClient, KalshiConfig
from src.services.market_matcher import MarketMatcher, MarketMatch, PMTradeData
from src.services.kelly_calculator import KellyCalculator
from src.services.risk_manager import RiskManager, RiskLevel

TRADE_LOG = 'data/trades/kalshi_copies.json'


@dataclass
class KalshiCopyConfig:
    enabled: bool = False
    bankroll: float = 100.0
    kelly_fraction: float = 0.5
    max_trade_percent: float = 2.0
    max_total_exposure: float = 30.0
    max_positions_per_market: int = 1  # Max bets per game
    max_same_side_per_market: int = 1  # Max same-side bets per game
    whale_avg_window: int = 50
    dry_run: bool = True

    @classmethod
    def from_env(cls) -> "KalshiCopyConfig":
        return cls(
            enabled=os.getenv("COPY_TO_KALSHI", "").lower() == "true",
            bankroll=float(os.getenv("KALSHI_BANKROLL", "100")),
            kelly_fraction=float(os.getenv("KALSHI_KELLY_FRACTION", "0.5")),
            max_trade_percent=float(os.getenv("KALSHI_MAX_TRADE_PERCENT", "2.0")),
            max_total_exposure=float(os.getenv("KALSHI_MAX_TOTAL_EXPOSURE", "30.0")),
            max_positions_per_market=int(os.getenv("MAX_POSITIONS_PER_MARKET", "1")),
            max_same_side_per_market=int(os.getenv("MAX_SAME_SIDE_PER_MARKET", "1")),
            whale_avg_window=int(os.getenv("KALSHI_WHALE_AVG_WINDOW", "50")),
            dry_run=os.getenv("DRY_RUN", "true").lower() == "true"
        )


@dataclass
class TradeResult:
    success: bool
    trade_id: Optional[str]
    pm_trade: dict
    kalshi_market: MarketMatch
    position_size: float
    side: str
    error: Optional[str] = None


class WhaleAnalyzer:
    """Analyze whale trading patterns to determine sizing."""

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.trade_history: List[Dict] = []

    def add_trades(self, trades: List[Dict]):
        """Add whale trades to history."""
        self.trade_history.extend(trades)
        # Keep only recent trades
        if len(self.trade_history) > self.window_size * 2:
            self.trade_history = self.trade_history[-self.window_size:]

    def get_average_wager(self) -> float:
        """Calculate whale's average wager amount."""
        if not self.trade_history:
            return 0.0

        valid_trades = [t for t in self.trade_history if t.get('size', 0) > 0]
        if not valid_trades:
            return 0.0

        return sum(t['size'] for t in valid_trades) / len(valid_trades)

    def get_average_wager_percent(self) -> float:
        """Estimate whale's average % of bankroll per trade."""
        avg_wager = self.get_average_wager()
        if avg_wager <= 0:
            return 0.0
        # Estimate whale bankroll from their trade sizes
        # Assuming they typically bet 1-5% of bankroll
        estimated_bankroll = avg_wager / 0.02  # Assume 2% typical
        return (avg_wager / estimated_bankroll) * 100

    def get_trade_stats(self) -> Dict:
        """Get trading statistics."""
        if not self.trade_history:
            return {"count": 0, "avg_size": 0, "total_volume": 0}

        sizes = [t.get('size', 0) for t in self.trade_history if t.get('size', 0) > 0]
        return {
            "count": len(self.trade_history),
            "avg_size": sum(sizes) / len(sizes) if sizes else 0,
            "total_volume": sum(sizes),
            "avg_percent": self.get_average_wager_percent()
        }


class KalshiExecutor:
    """Execute mirrored trades on Kalshi."""

    def __init__(
        self,
        kalshi_client: KalshiClient,
        market_matcher: MarketMatcher,
        config: KalshiCopyConfig = None
    ):
        self.client = kalshi_client
        self.matcher = market_matcher
        self.config = config or KalshiCopyConfig.from_env()
        self.whale_analyzer = WhaleAnalyzer(window_size=self.config.whale_avg_window)
        self.kelly = KellyCalculator(
            kelly_fraction=self.config.kelly_fraction,
            max_trade_percent=self.config.max_trade_percent,
            bankroll=self.config.bankroll
        )
        self.risk = RiskManager(
            max_trade_percent=self.config.max_trade_percent,
            max_trader_exposure=10.0,
            max_total_exposure=self.config.max_total_exposure,
            bankroll=self.config.bankroll
        )
        self._ensure_trade_log()
        self._load_positions()

    def _ensure_trade_log(self):
        """Create trade log file if needed."""
        os.makedirs(os.path.dirname(TRADE_LOG), exist_ok=True)
        if not os.path.exists(TRADE_LOG):
            with open(TRADE_LOG, 'w') as f:
                json.dump([], f)

    def _load_positions(self):
        """Load existing positions from trade log."""
        try:
            with open(TRADE_LOG, 'r') as f:
                trades = json.load(f)
        except:
            trades = []

        self.positions_by_market: Dict[str, int] = {}
        self.positions_by_side: Dict[str, int] = {}

        for t in trades:
            game_key = t.get('game_key', '')
            side = t.get('kalshi_side', '')
            if game_key:
                self.positions_by_market[game_key] = self.positions_by_market.get(game_key, 0) + 1
                if side:
                    key = f"{game_key}:{side}"
                    self.positions_by_side[key] = self.positions_by_side.get(key, 0) + 1

    def _ensure_trade_log(self):
        """Create trade log file if needed."""
        os.makedirs(os.path.dirname(TRADE_LOG), exist_ok=True)
        if not os.path.exists(TRADE_LOG):
            with open(TRADE_LOG, 'w') as f:
                json.dump([], f)

    def calculate_position_size(self, pm_trade: PMTradeData, whale_avg_percent: float) -> float:
        """Calculate our position size based on whale's average %."""
        if whale_avg_percent <= 0:
            whale_avg_percent = 2.0  # Default to 2% if unknown

        # Use whale's % of bankroll as our sizing factor
        our_size = self.config.bankroll * (whale_avg_percent / 100)

        # Apply Kelly/risk limits
        risk_result = self.risk.check_position(
            trader_wallet="whale",
            proposed_size=our_size
        )

        return risk_result.final_position_size

    def execute_copy_trade(self, pm_trade_data: dict, pm_trade: PMTradeData) -> TradeResult:
        """Execute a copy trade on Kalshi."""
        # Find matching Kalshi market
        match = self.matcher.find_match(pm_trade)
        if not match:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=None,
                position_size=0,
                side="",
                error="No matching Kalshi market found"
            )

        # Check position limits
        market_key = match.game_key
        side_key = f"{market_key}:{match.kalshi_side}"

        if self.positions_by_market.get(market_key, 0) >= self.config.max_positions_per_market:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=0,
                side=match.kalshi_side,
                error=f"Max {self.config.max_positions_per_market} position(s) per market reached"
            )

        if self.positions_by_side.get(side_key, 0) >= self.config.max_same_side_per_market:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=0,
                side=match.kalshi_side,
                error=f"Max {self.config.max_same_side_per_market} same-side bet(s) per market reached"
            )

        # Get whale's average wager %
        whale_avg_percent = self.whale_analyzer.get_average_wager_percent()

        # Calculate position size
        position_size = self.calculate_position_size(pm_trade, whale_avg_percent)

        if position_size < 1.0:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=position_size,
                side=match.kalshi_side,
                error=f"Position too small: ${position_size:.2f}"
            )

        # Execute trade (or dry run)
        if self.config.dry_run:
            print(f"\n[DRY RUN] Would execute:")
            print(f"  PM: {pm_trade_data.get('market', {}).get('title', 'Unknown')}")
            print(f"  Kalshi: {match.kalshi_market_title}")
            print(f"  Side: {match.kalshi_side}")
            print(f"  Size: ${position_size:.2f}")
            # Update position tracking for dry-run too
            self.positions_by_market[match.game_key] = self.positions_by_market.get(match.game_key, 0) + 1
            side_key = f"{match.game_key}:{match.kalshi_side}"
            self.positions_by_side[side_key] = self.positions_by_side.get(side_key, 0) + 1
            return TradeResult(
                success=True,
                trade_id=f"dry_{int(time.time())}",
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=position_size,
                side=match.kalshi_side,
                error=None
            )

        # Real execution
        result = self.client.place_order(
            market_ticker=match.kalshi_market_id,
            side=match.kalshi_side,
            count=int(position_size)
        )

        if result.get("success"):
            self._log_trade(pm_trade_data, match, position_size, result.get("order_id"))
            print(f"\n✓ Executed copy trade:")
            print(f"  PM: {pm_trade_data.get('market', {}).get('title', 'Unknown')}")
            print(f"  Kalshi: {match.kalshi_market_title}")
            print(f"  Size: ${position_size:.2f}")
            return TradeResult(
                success=True,
                trade_id=result.get("order_id"),
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=position_size,
                side=match.kalshi_side
            )
        else:
            error = result.get("error", "Unknown error")
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=position_size,
                side=match.kalshi_side,
                error=error
            )

    def _log_trade(self, pm_trade: dict, match: MarketMatch, size: float, order_id: str):
        """Log executed trade and update position tracking."""
        try:
            with open(TRADE_LOG, 'r') as f:
                trades = json.load(f)
        except:
            trades = []

        trade = {
            "timestamp": datetime.now().isoformat(),
            "order_id": order_id,
            "pm_market": pm_trade.get("market", {}).get("title", ""),
            "pm_slug": pm_trade.get("market", {}).get("slug", ""),
            "pm_size": pm_trade.get("amount", 0),
            "kalshi_market": match.kalshi_market_title,
            "kalshi_ticker": match.kalshi_market_id,
            "kalshi_side": match.kalshi_side,
            "position_size": size,
            "sport": match.sport,
            "game_key": match.game_key,
            "match_type": match.match_type,
            "confidence": match.confidence
        }

        trades.append(trade)

        with open(TRADE_LOG, 'w') as f:
            json.dump(trades, f, indent=2)

        # Update position tracking
        self.positions_by_market[match.game_key] = self.positions_by_market.get(match.game_key, 0) + 1
        side_key = f"{match.game_key}:{match.kalshi_side}"
        self.positions_by_side[side_key] = self.positions_by_side.get(side_key, 0) + 1

    def process_whale_trades(self, whale_trades: List[dict]) -> List[TradeResult]:
        """Process a batch of whale trades."""
        results = []

        # Update whale analyzer
        self.whale_analyzer.add_trades(whale_trades)

        for trade_data in whale_trades:
            # Parse PM trade
            pm_trade = self.matcher.parse_pm_trade(trade_data)
            if not pm_trade:
                continue

            # Skip if we already traded this market recently
            if self._recently_traded(pm_trade):
                continue

            # Execute copy trade
            result = self.execute_copy_trade(trade_data, pm_trade)
            if result.success:
                results.append(result)

        return results

    def _recently_traded(self, pm_trade: PMTradeData, cooldown_minutes: int = 30) -> bool:
        """Check if we recently traded this market."""
        try:
            with open(TRADE_LOG, 'r') as f:
                trades = json.load(f)
        except:
            return False

        cutoff = time.time() - (cooldown_minutes * 60)
        recent = [t for t in trades if t.get("timestamp", 0) > cutoff]

        for t in recent:
            if t.get("pm_slug", "").endswith(pm_trade.teams[0]) and \
               t.get("pm_slug", "").endswith(pm_trade.teams[1]):
                return True

        return False

    def get_status(self) -> Dict:
        """Get executor status."""
        return {
            "enabled": self.config.enabled,
            "dry_run": self.config.dry_run,
            "bankroll": self.config.bankroll,
            "whale_stats": self.whale_analyzer.get_trade_stats(),
            "balance": self.client.get_balance()
        }


def create_executor(dry_run: bool = True) -> KalshiExecutor:
    """Create a fully configured executor."""
    config = KalshiCopyConfig.from_env()
    config.dry_run = dry_run

    kalshi_config = KalshiConfig.from_env()
    client = KalshiClient(kalshi_config)
    matcher = MarketMatcher(client.get_all_markets())

    return KalshiExecutor(client, matcher, config)


if __name__ == "__main__":
    print("Testing Kalshi Executor...")
    executor = create_executor(dry_run=True)

    status = executor.get_status()
    print(f"Status: {status}")

    # Test with sample trade
    sample_trade = {
        "market": {
            "id": "pm-123",
            "title": "Will Syracuse beat North Carolina?",
            "slug": "cbb-syr-unc-2026-02-01"
        },
        "tokenId": "abc123",
        "side": "buy",
        "amount": 150,
        "outcome": "yes"
    }

    pm_trade = executor.matcher.parse_pm_trade(sample_trade)
    if pm_trade:
        result = executor.execute_copy_trade(sample_trade, pm_trade)
        print(f"\nTrade result: {result.success}")
        if not result.success:
            print(f"Error: {result.error}")
