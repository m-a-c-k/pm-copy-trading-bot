"""
Market Matcher - Match Polymarket whale trades to Kalshi markets

Critical module: Finds equivalent Kalshi markets for PM trades.
"""

import re
from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass
from src.services.team_mappings import is_same_team, get_canonical


@dataclass
class MarketMatch:
    """Result of matching a PM market to Kalshi."""
    pm_market_id: str
    pm_market_title: str
    pm_token_id: str
    pm_side: str  # "yes" or "no"
    kalshi_market_id: str
    kalshi_market_title: str
    kalshi_side: str  # "yes" or "no"
    sport: str
    game_key: str
    confidence: float  # 0.0 to 1.0
    match_type: str  # "exact", "fuzzy", "line_fuzzy"


@dataclass
class PMTradeData:
    """Parsed data from a Polymarket whale trade."""
    market_id: str
    token_id: str
    side: str  # "yes" or "no"
    size: float  # USDC amount
    sport: str
    teams: Tuple[str, str]  # team1, team2
    market_type: str  # "winner", "spread", "total"
    line: Optional[float]  # spread line or total line
    event_date: Optional[str]


class MarketMatcher:
    """Match Polymarket markets to Kalshi markets."""

    # Sport mappings
    SPORT_MAP = {
        "nfl": "nfl",
        "football": "nfl",
        "nba": "nba",
        "basketball": "nba",
        "cbb": "cbb",
        "college basketball": "cbb",
        "cfb": "cfb",
        "college football": "cfb",
        "nhl": "nhl",
        "hockey": "nhl",
    }

    # Market type patterns
    WINNER_PATTERNS = [
        r'winner',
        r'wins$',
        r'beat',
        r'vs\.?\s',
    ]

    SPREAD_PATTERNS = [
        r'spread',
        r'wins by',
        r' - \d+\.?\d*',
    ]

    TOTAL_PATTERNS = [
        r'total',
        r'o/u',
        r'over/under',
        r'points$',
    ]

    def __init__(self, kalshi_markets: Dict[str, List[Dict]]):
        """
        Initialize with Kalshi markets dictionary.

        Args:
            kalshi_markets: Dict mapping "sport:game_key" to list of market dicts
        """
        self.kalshi_markets = kalshi_markets
        self._build_index()

    def _build_index(self):
        """Build searchable index of Kalshi markets."""
        self._by_sport: Dict[str, Dict[str, List[Dict]]] = {}
        self._by_game_key: Dict[str, List[Dict]] = {}

        for tagged_key, markets in self.kalshi_markets.items():
            sport, game_key = self._parse_tagged_key(tagged_key)

            if sport not in self._by_sport:
                self._by_sport[sport] = {}
            if game_key not in self._by_sport[sport]:
                self._by_sport[sport][game_key] = []
            self._by_sport[sport][game_key].extend(markets)

            self._by_game_key[game_key] = markets

    def _parse_tagged_key(self, tagged_key: str) -> Tuple[str, str]:
        """Parse 'sport:game_key' into components."""
        if ':' in tagged_key:
            parts = tagged_key.split(':', 1)
            return parts[0], parts[1]
        return "unknown", tagged_key

    def parse_pm_trade(self, trade_data: dict) -> Optional[PMTradeData]:
        """
        Parse raw Polymarket trade data into structured format.

        Args:
            trade_data: Dict from Polymarket activity API

        Returns:
            PMTradeData or None if parsing fails
        """
        try:
            market_info = trade_data.get('market', {})
            token_id = trade_data.get('tokenId', '') or trade_data.get('clobTokenId', '')
            side = trade_data.get('side', 'buy').lower()
            size = float(trade_data.get('amount', 0) or trade_data.get('size', 0))

            if not token_id:
                return None

            # Determine side (buy yes = yes, sell yes = no, etc.)
            if side == 'buy':
                outcome = trade_data.get('outcome', 'yes').lower()
            else:
                outcome = trade_data.get('outcome', 'no').lower()

            side = 'yes' if outcome == 'yes' else 'no'

            # Parse market info
            title = (market_info.get('title', '') or market_info.get('question', '')).lower()
            slug = (market_info.get('slug', '') or '').lower()

            sport, teams, market_type, line = self._parse_market_title(title, slug)

            event_date = self._extract_date(slug, title)

            return PMTradeData(
                market_id=market_info.get('id', ''),
                token_id=token_id,
                side=side,
                size=size,
                sport=sport,
                teams=teams,
                market_type=market_type,
                line=line,
                event_date=event_date
            )

        except Exception:
            return None

    def _parse_market_title(self, title: str, slug: str) -> Tuple[str, Tuple[str, str], str, Optional[float]]:
        """Parse market title to extract sport, teams, market type, and line."""
        sport = self._detect_sport(title, slug)
        teams = self._extract_teams(title, slug, sport)
        market_type = self._detect_market_type(title)
        line = self._extract_line(title, market_type)

        return sport, teams, market_type, line

    def _detect_sport(self, title: str, slug: str) -> str:
        """Detect sport from title or slug."""
        text = f"{title} {slug}".lower()

        for pattern, sport in self.SPORT_MAP.items():
            if pattern in text:
                return sport

        # Fallback: check slug patterns
        if 'nfl' in slug:
            return 'nfl'
        elif 'nba' in slug:
            return 'nba'
        elif 'cbb' in slug or 'ncaab' in slug:
            return 'cbb'
        elif 'cfb' in slug:
            return 'cfb'
        elif 'nhl' in slug:
            return 'nhl'

        return 'unknown'

    def _extract_teams(self, title: str, slug: str, sport: str) -> Tuple[str, str]:
        """Extract team abbreviations from title or slug."""
        # Try slug first: "nfl-buf-den-2026-01-17" → ("buf", "den")
        if slug:
            parts = slug.lower().split('-')
            if len(parts) >= 3:
                team1 = parts[1].lower()
                team2 = parts[2].lower()
                if len(team1) >= 2 and len(team2) >= 2:
                    return (team1, team2)

        # Try title with team aliases
        for canonical, aliases in self._get_team_aliases(sport).items():
            if len(aliases) >= 2:
                for i, alias in enumerate(aliases):
                    if alias in title:
                        for alias2 in list(aliases)[i+1:]:
                            if alias2 in title:
                                return (alias, alias2)

        return ("", "")

    def _get_team_aliases(self, sport: str) -> dict:
        """Get team aliases for sport."""
        from src.services.team_mappings import TEAM_ALIASES
        return TEAM_ALIASES

    def _detect_market_type(self, title: str) -> str:
        """Detect market type from title."""
        title_lower = title.lower()

        if any(p in title_lower for p in self.SPREAD_PATTERNS):
            return 'spread'
        elif any(p in title_lower for p in self.TOTAL_PATTERNS):
            return 'total'
        elif any(p in title_lower for p in self.WINNER_PATTERNS):
            return 'winner'

        return 'winner'

    def _extract_line(self, title: str, market_type: str) -> Optional[float]:
        """Extract line number (spread or total) from title."""
        if market_type not in ('spread', 'total'):
            return None

        match = re.search(r'([-+]?\d+\.?\d*)', title)
        if match:
            return float(match.group(1))

        return None

    def _extract_date(self, slug: str, title: str) -> Optional[str]:
        """Extract event date from slug or title."""
        # Slug format: "nfl-buf-den-2026-01-17"
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', slug)
        if date_match:
            return date_match.group(1)

        # Try title
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', title)
        if date_match:
            return date_match.group(1)

        return None

    def find_match(self, pm_trade: PMTradeData) -> Optional[MarketMatch]:
        """
        Find matching Kalshi market for a PM trade.

        Args:
            pm_trade: Parsed PM trade data

        Returns:
            MarketMatch or None if no match found
        """
        if pm_trade.sport == 'unknown' or not pm_trade.teams[0]:
            return None

        sport = pm_trade.sport
        team1, team2 = pm_trade.teams

        # Build game key
        game_key = self._build_game_key(team1, team2)

        # Get Kalshi markets for this sport
        if sport not in self._by_sport:
            return None

        sport_markets = self._by_sport[sport]

        # Try exact game key first
        if game_key in sport_markets:
            return self._find_best_match(
                sport_markets[game_key],
                pm_trade,
                confidence=1.0,
                match_type='exact'
            )

        # Try fuzzy team matching
        for ks_game_key, ks_markets in sport_markets.items():
            if self._teams_match(team1, team2, ks_game_key):
                return self._find_best_match(
                    ks_markets,
                    pm_trade,
                    confidence=0.8,
                    match_type='fuzzy'
                )

        return None

    def _build_game_key(self, team1: str, team2: str) -> str:
        """Build normalized game key from teams."""
        t1 = team1.lower().strip()
        t2 = team2.lower().strip()
        return '-'.join(sorted([t1, t2]))

    def _teams_match(self, pm_team1: str, pm_team2: str, ks_game_key: str) -> bool:
        """Check if PM teams match Kalshi game key."""
        ks_teams = ks_game_key.split('-')
        if len(ks_teams) != 2:
            return False

        ks_team1, ks_team2 = ks_teams[0].lower(), ks_teams[1].lower()

        # Check if both PM teams match the KS teams (order doesn't matter)
        pm_matches = 0
        for pm_t in [pm_team1, pm_team2]:
            if is_same_team(pm_t, ks_team1) or is_same_team(pm_t, ks_team2):
                pm_matches += 1

        return pm_matches >= 2

    def _find_best_match(
        self,
        ks_markets: List[Dict],
        pm_trade: PMTradeData,
        confidence: float,
        match_type: str
    ) -> Optional[MarketMatch]:
        """Find the best matching market from a list."""
        best_match = None
        best_confidence = 0.0

        for ks_market in ks_markets:
            ks_title = ks_market.get('title', '').lower()

            # Match market type
            ks_market_type = self._detect_market_type(ks_title)
            if ks_market_type != pm_trade.market_type:
                continue

            # For spreads/totals, match line number
            if pm_trade.market_type in ('spread', 'total'):
                ks_line = self._extract_line(ks_title, ks_market_type)
                if ks_line is not None and pm_trade.line is not None:
                    if abs(ks_line - pm_trade.line) > 0.1:
                        continue

            # Determine side (YES = team wins, NO = team loses)
            ks_side = self._determine_kalshi_side(ks_market, pm_trade)

            if ks_side is None:
                continue

            match_confidence = confidence

            # Boost confidence if line matches exactly
            if pm_trade.market_type in ('spread', 'total'):
                if pm_trade.line is not None:
                    match_confidence += 0.1

            if match_confidence > best_confidence:
                best_confidence = match_confidence
                best_match = MarketMatch(
                    pm_market_id=pm_trade.market_id,
                    pm_market_title=ks_title,
                    pm_token_id=pm_trade.token_id,
                    pm_side=pm_trade.side,
                    kalshi_market_id=ks_market.get('id', ''),
                    kalshi_market_title=ks_title,
                    kalshi_side=ks_side,
                    sport=pm_trade.sport,
                    game_key=self._build_game_key(pm_trade.teams[0], pm_trade.teams[1]),
                    confidence=min(match_confidence, 1.0),
                    match_type=match_type
                )

        return best_match

    def _determine_kalshi_side(self, ks_market: Dict, pm_trade: PMTradeData) -> Optional[str]:
        """Determine which side (yes/no) to trade on Kalshi."""
        ks_title = ks_market.get('title', '').lower()
        team1, team2 = pm_trade.teams

        # Check which team is mentioned in the Kalshi market title
        ks_team = None
        for team in [team1, team2]:
            if self._team_mentioned_in_title(team, ks_title):
                ks_team = team
                break

        if not ks_team:
            return None

        # Determine side based on PM side and which team the market is for
        # If PM bought YES (team A wins) and KS market is for team A, buy YES
        # If PM bought YES and KS market is for team B, buy NO (bet against team A)
        opposite_team = team2 if team1 == ks_team else team1

        if pm_trade.side == 'yes':
            # PM bets team wins → on KS, bet the same team
            return 'yes'
        else:
            # PM bets team loses → on KS, bet the opposite team
            return 'no'

    def _team_mentioned_in_title(self, team: str, title: str) -> bool:
        """Check if team is mentioned in market title."""
        # Try canonical name matching
        canonical = get_canonical(team)
        if canonical:
            canonical_lower = canonical.lower()
            if canonical_lower in title:
                return True

        # Try direct match
        if team.lower() in title:
            return True

        return False


def create_market_matcher(kalshi_client) -> MarketMatcher:
    """Create a MarketMatcher from a KalshiClient."""
    markets = kalshi_client.get_all_markets()
    return MarketMatcher(markets)


if __name__ == "__main__":
    from src.services.kalshi_client import KalshiClient, KalshiConfig

    config = KalshiConfig.from_env()
    client = KalshiClient(config)

    print("Creating market matcher...")
    matcher = create_market_matcher(client)

    # Test with sample PM trade data
    test_trades = [
        {
            "market": {
                "id": "pm-123",
                "title": "Will Utah beat Colorado?",
                "slug": "nba-uta-col-2026-02-01"
            },
            "tokenId": "abc123",
            "side": "buy",
            "amount": 100,
            "outcome": "yes"
        },
        {
            "market": {
                "id": "pm-456",
                "title": "Will Denver cover -3.5?",
                "slug": "nfl-den-buf-2026-02-02"
            },
            "tokenId": "def456",
            "side": "buy",
            "amount": 50,
            "outcome": "no"
        }
    ]

    print("\nTesting market matching...")
    for trade in test_trades:
        pm_trade = matcher.parse_pm_trade(trade)
        if pm_trade:
            match = matcher.find_match(pm_trade)
            if match:
                print(f"\n✓ Match found: {match.match_type} (confidence: {match.confidence:.2f})")
                print(f"  PM: {trade['market']['title']}")
                print(f"  Kalshi: {match.kalshi_market_title}")
                print(f"  Side: {match.kalshi_side}")
            else:
                print(f"\n✗ No match for: {trade['market']['title']}")
