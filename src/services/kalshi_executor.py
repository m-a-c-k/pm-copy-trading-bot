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
    max_positions_per_market: int = 1
    max_same_side_per_market: int = 1
    max_trades_per_hour: int = 10
    max_trades_per_day: int = 50
    min_trade_size: float = 1.0
    max_single_trade_size: float = 10.0
    cooldown_minutes: int = 30
    whale_avg_window: int = 50
    dry_run: bool = True

    @classmethod
    def from_env(cls) -> "KalshiCopyConfig":
        bankroll_env = os.getenv("KALSHI_BANKROLL", "")
        if bankroll_env:
            bankroll = float(bankroll_env)
        else:
            kalshi_config = KalshiConfig.from_env()
            if kalshi_config.enabled:
                client = KalshiClient(kalshi_config)
                bankroll = client.get_balance()
            else:
                bankroll = 100.0

        return cls(
            enabled=os.getenv("COPY_TO_KALSHI", "").lower() == "true",
            bankroll=bankroll,
            kelly_fraction=float(os.getenv("KALSHI_KELLY_FRACTION", "0.5")),
            max_trade_percent=float(os.getenv("KALSHI_MAX_TRADE_PERCENT", "5.0")),
            max_total_exposure=float(os.getenv("KALSHI_MAX_TOTAL_EXPOSURE", "30.0")),
            max_positions_per_market=int(os.getenv("MAX_POSITIONS_PER_MARKET", "1")),
            max_same_side_per_market=int(os.getenv("MAX_SAME_SIDE_PER_MARKET", "1")),
            max_trades_per_hour=int(os.getenv("MAX_TRADES_PER_HOUR", "15")),
            max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "50")),
            min_trade_size=float(os.getenv("MIN_TRADE_SIZE", "1.0")),
            max_single_trade_size=float(os.getenv("MAX_SINGLE_TRADE_SIZE", "25.0")),
            cooldown_minutes=int(os.getenv("COOLDOWN_MINUTES", "30")),
            whale_avg_window=int(os.getenv("KALSHI_WHALE_AVG_WINDOW", "50")),
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true"
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
    """Analyze whale trading patterns for sizing."""
    
    def __init__(self, window_size: int = 50, estimated_whale_bankroll: float = 0.0):
        self.window_size = window_size
        # 0 means auto-estimate from trades
        self._estimated_whale_bankroll = estimated_whale_bankroll if estimated_whale_bankroll > 0 else None
        self.trade_history = []
        self.trade_history = []
    
    def add_trades(self, trades: List[Dict]):
        """Add new trades to history."""
        self.trade_history.extend(trades)
        # Keep only recent trades
        self.trade_history = self.trade_history[-self.window_size:]
    
    def get_stats(self, our_bankroll: float) -> Dict:
        """Get whale statistics and calculate scaling."""
        sizes = [t.get('size', 0) for t in self.trade_history if t.get('size', 0) > 0]
        avg_wager = sum(sizes) / len(sizes) if sizes else 0.0
        
        # Dynamic whale bankroll estimation
        # Assume whale bets 2-3% of bankroll (conservative Kelly)
        if avg_wager > 0 and self._estimated_whale_bankroll is None:
            # If whale bets $100 on avg, assume $4K-$5K bankroll (2-2.5%)
            estimated_whale_bankroll = avg_wager / 0.025
        elif self._estimated_whale_bankroll:
            estimated_whale_bankroll = self._estimated_whale_bankroll
        else:
            # Fallback: assume $10K whale bankroll
            estimated_whale_bankroll = 10000.0
        
        scaling = our_bankroll / estimated_whale_bankroll

        return {
            "count": len(self.trade_history),
            "avg_size": avg_wager,
            "total_volume": sum(sizes),
            "scaling_factor": scaling,
            "our_position": avg_wager * scaling,
            "whale_bankroll_est": estimated_whale_bankroll
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

    def calculate_position_size(self, pm_trade: PMTradeData) -> float:
        """
        Calculate our position using whale's trading patterns:
        our = (trade_size / whale_avg) * our_normal_size
        
        Our normal size = 2% of our bankroll
        """
        trade_size = pm_trade.size
        if trade_size <= 0:
            return 0.0

        # Our normal position (2% of bankroll)
        our_normal_size = self.config.bankroll * (self.config.max_trade_percent / 100)

        our_size = self.whale_analyzer.get_scaled_position(
            our_bankroll=self.config.bankroll,
            trade_size=trade_size,
            our_normal_size=our_normal_size
        )

        return our_size

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

        # Calculate position size using whale's avg
        position_size = self.calculate_position_size(pm_trade)

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
            "whale_stats": self.whale_analyzer.get_stats(self.config.bankroll),
            "balance": self.client.get_balance()
        }


def create_executor(dry_run: bool = True) -> KalshiExecutor:
    """Create a fully configured executor."""
    config = KalshiCopyConfig.from_env()
    config.dry_run = dry_run

    kalshi_config = KalshiConfig.from_env()
    client = KalshiClient(kalshi_config)
    
    # Lazily load markets on first use (for faster startup)
    # Markets will be fetched when first trade is detected
    matcher = MarketMatcher({})  # Empty initially
    
    executor = KalshiExecutor(client, matcher, config)
    
    # Fetch markets in background
    import threading
    def fetch_markets():
        try:
            markets = client.get_all_markets()
            executor.matcher = MarketMatcher(markets)
        except Exception:
            pass
    
    thread = threading.Thread(target=fetch_markets, daemon=True)
    thread.start()
    
    return executor


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
