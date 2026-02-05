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
    max_position_size_per_market: float = 27.0  # Dollar limit per market side
    max_position_size_total: float = 108.0  # Dollar limit total exposure
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
        kalshi_config = KalshiConfig.from_env()
        bankroll = 100.0  # Default fallback
        
        if kalshi_config.enabled:
            try:
                client = KalshiClient(kalshi_config)
                balance = client.get_balance()
                if balance and balance > 0:
                    bankroll = balance
                    print(f"Loaded Kalshi balance: ${bankroll:.2f}")
                else:
                    print("Kalshi balance is $0 or unavailable, using default $100")
            except Exception as e:
                print(f"Could not fetch Kalshi balance: {e}, using default $100")

        return cls(
            enabled=os.getenv("COPY_TO_KALSHI", "").lower() == "true",
            bankroll=bankroll,
            kelly_fraction=float(os.getenv("KALSHI_KELLY_FRACTION", "0.5")),
            max_trade_percent=float(os.getenv("KALSHI_MAX_TRADE_PERCENT", "5.0")),
            max_total_exposure=float(os.getenv("KALSHI_MAX_TOTAL_EXPOSURE", "30.0")),
            max_positions_per_market=int(os.getenv("MAX_POSITIONS_PER_MARKET", "1")),
            max_position_size_per_market=float(os.getenv("MAX_POSITION_SIZE_PER_MARKET", "27.0")),
            max_position_size_total=float(os.getenv("MAX_POSITION_SIZE_TOTAL", "108.0")),
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
    
    def get_scaled_position(self, our_bankroll: float, trade_size: float, our_normal_size: float) -> float:
        """Calculate scaled position size based on whale's wager relative to their avg."""
        stats = self.get_stats(our_bankroll)
        avg_wager = stats["avg_size"]
        
        if avg_wager <= 0:
            # No history, use normal size
            return our_normal_size
        
        # Scale: if whale bets 2x their avg, we bet 2x our normal
        ratio = trade_size / avg_wager
        our_size = our_normal_size * ratio
        
        # Cap at max single trade size (25% of bankroll default)
        max_size = our_bankroll * 0.25
        return min(our_size, max_size)


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
        """Load existing positions from trade log.
        
        Tracks DOLLAR amounts per market, not counts.
        """
        try:
            with open(TRADE_LOG, 'r') as f:
                trades = json.load(f)
        except:
            trades = []

        # Track DOLLARS per market (game_key)
        self.positions_by_market: Dict[str, float] = {}
        # Track DOLLARS per market + side (game_key:side)
        self.positions_by_side: Dict[str, float] = {}

        for t in trades:
            game_key = t.get('game_key', '')
            side = t.get('kalshi_side', '')
            size = float(t.get('position_size', 0))
            
            if game_key and size > 0:
                self.positions_by_market[game_key] = self.positions_by_market.get(game_key, 0.0) + size
                if side:
                    key = f"{game_key}:{side}"
                    self.positions_by_side[key] = self.positions_by_side.get(key, 0.0) + size

    def _load_markets(self):
        """Load Kalshi markets if not already loaded."""
        try:
            markets = self.client.get_all_markets()
            if markets:
                # Update matcher with new markets
                from src.services.market_matcher import MarketMatcher
                self.matcher = MarketMatcher(markets)
        except Exception:
            pass

    def calculate_position_size(self, pm_trade: PMTradeData) -> float:
        """
        Calculate our position using whale's trading patterns:
        our = (trade_size / whale_avg) * our_normal_size
        
        Our normal size = 2% of our bankroll
        """
        trade_size = pm_trade.size
        if trade_size <= 0:
            return 0.0

        # Refresh markets if empty
        if not self.matcher.kalshi_markets:
            self._load_markets()

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
                error=f"No Kalshi market for {pm_trade.market_type} ({pm_trade.teams[0]}-{pm_trade.teams[1]})"
            )

        # Check position limits (DOLLAR-based)
        market_key = match.game_key
        side_key = f"{market_key}:{match.kalshi_side}"
        max_per_market = self.config.max_position_size_per_market  # $27 default
        max_total = self.config.max_position_size_total  # $108 default
        current_total = sum(self.positions_by_market.values())
        current_on_side = self.positions_by_side.get(side_key, 0.0)

        if current_on_side >= max_per_market:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=0,
                side=match.kalshi_side,
                error=f"Max ${max_per_market:.2f} on {side_key} (have ${current_on_side:.2f})"
            )

        if current_total >= max_total:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=0,
                side=match.kalshi_side,
                error=f"Max ${max_total:.2f} total exposure (have ${current_total:.2f})"
            )

        # Calculate position size using whale's avg
        position_size = self.calculate_position_size(pm_trade)

        # Cap by remaining budget for this side
        remaining = max_per_market - current_on_side
        if position_size > remaining:
            position_size = remaining

        if position_size < 1.0:
            return TradeResult(
                success=False,
                trade_id=None,
                pm_trade=pm_trade_data,
                kalshi_market=match,
                position_size=position_size,
                side=match.kalshi_side,
                error=f"Position too small after cap: ${position_size:.2f}"
            )

        # Execute trade (or dry run)
        trader_address = pm_trade_data.get("trader_address", "unknown")
        if self.config.dry_run:
            print(f"\n[DRY RUN] Would execute:")
            print(f"  Trader: {trader_address[:12]}...")
            print(f"  PM: {pm_trade_data.get('market', {}).get('title', 'Unknown')}")
            print(f"  Kalshi: {match.kalshi_market_title}")
            print(f"  Side: {match.kalshi_side}")
            print(f"  Size: ${position_size:.2f} (remaining: ${remaining:.2f})")
            # Update position tracking for dry-run too
            self.positions_by_market[match.game_key] = self.positions_by_market.get(match.game_key, 0.0) + position_size
            side_key = f"{match.game_key}:{match.kalshi_side}"
            self.positions_by_side[side_key] = self.positions_by_side.get(side_key, 0.0) + position_size
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
        print(f"\n✓ Executed copy trade:")
        print(f"  Trader: {trader_address[:12]}...")
        print(f"  PM: {pm_trade_data.get('market', {}).get('title', 'Unknown')}")
        print(f"  Kalshi: {match.kalshi_market_title}")
        print(f"  Side: {match.kalshi_side}")
        print(f"  Size: ${position_size:.2f}")

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

        # Update position tracking (DOLLAR-based)
        self.positions_by_market[match.game_key] = self.positions_by_market.get(match.game_key, 0.0) + size
        side_key = f"{match.game_key}:{match.kalshi_side}"
        self.positions_by_side[side_key] = self.positions_by_side.get(side_key, 0.0) + size

    def process_whale_trades(self, whale_trades: List[dict]) -> tuple:
        """Process a batch of whale trades.
        
        Returns: (executed_trades: List[TradeResult], skipped_trades: List[dict])
        Each skipped trade dict contains: {'trade': dict, 'reason': str}
        """
        executed = []
        skipped = []

        # Update whale analyzer
        self.whale_analyzer.add_trades(whale_trades)

        for trade_data in whale_trades:
            # Parse PM trade
            pm_trade = self.matcher.parse_pm_trade(trade_data)
            if not pm_trade:
                skipped.append({
                    'trade': trade_data,
                    'reason': 'Failed to parse PM trade'
                })
                continue

            # Skip if we already traded this market recently
            if self._recently_traded(pm_trade):
                skipped.append({
                    'trade': trade_data,
                    'reason': f'Recently traded ({pm_trade.teams[0]}-{pm_trade.teams[1]})'
                })
                continue

            # Execute copy trade
            result = self.execute_copy_trade(trade_data, pm_trade)
            if result.success:
                executed.append(result)
            else:
                reason = result.error or 'Unknown error'
                skipped.append({
                    'trade': trade_data,
                    'reason': reason
                })

        return executed, skipped

    def _recently_traded(self, pm_trade: PMTradeData, cooldown_minutes: int = 30) -> bool:
        """Check if we recently traded this market."""
        try:
            with open(TRADE_LOG, 'r') as f:
                trades = json.load(f)
        except:
            return False

        cutoff = time.time() - (cooldown_minutes * 60)
        recent = []
        for t in trades:
            ts = t.get("timestamp", 0)
            try:
                ts_float = float(ts)
            except (ValueError, TypeError):
                try:
                    from datetime import datetime
                    ts_float = datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp()
                except:
                    continue
            if ts_float > cutoff:
                recent.append(t)

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
    
    # Load markets at startup for proper matching
    print("Loading Kalshi markets...")
    markets = client.get_all_markets()
    print(f"Loaded {len(markets)} markets from Kalshi")
    matcher = MarketMatcher(markets)
    
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
