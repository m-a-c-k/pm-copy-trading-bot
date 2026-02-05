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

    # Sport mappings - detected from PM market title/slug
    SPORT_MAP = {
        # Football
        "nfl": "nfl",
        "football": "nfl",
        "super bowl": "nfl",
        "cfb": "cfb",
        "college football": "cfb",
        # Basketball
        "nba": "nba",
        "basketball": "nba",
        "cbb": "cbb",
        "college basketball": "cbb",
        "ncaab": "cbb",
        # Hockey
        "nhl": "nhl",
        "hockey": "nhl",
        # Baseball
        "mlb": "mlb",
        "baseball": "mlb",
        # Soccer
        "soccer": "soccer",
        "premier": "soccer",
        "la liga": "soccer",
        "serie a": "soccer",
        "bundesliga": "soccer",
        "ligue 1": "soccer",
        "fc": "soccer",
        "united": "soccer",
        "city": "soccer",
        "rangers": "soccer",
        "celtic": "soccer",
        # Combat
        "ufc": "ufc",
        "mma": "ufc",
        "boxing": "ufc",
        # Golf
        "pga": "pga",
        "golf": "pga",
        "masters": "pga",
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
        r' -\d+\.?\d*',  # "Team -2.5"
        r' \+\d+\.?\d*',  # "Team +2.5"
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
            sport, market_type, game_key = self._parse_tagged_key(tagged_key)

            if sport not in self._by_sport:
                self._by_sport[sport] = {}
            if game_key not in self._by_sport[sport]:
                self._by_sport[sport][game_key] = []
            
            # Add market type to each market dict
            for m in markets:
                m['market_type'] = market_type
            
            self._by_sport[sport][game_key].extend(markets)
            self._by_game_key[game_key] = markets

    def _parse_tagged_key(self, tagged_key: str) -> Tuple[str, str, str]:
        """Parse 'sport:market_type:game_key' into components."""
        parts = tagged_key.split(':')
        if len(parts) >= 3:
            return parts[0], parts[1], ':'.join(parts[2:])
        elif len(parts) == 2:
            return parts[0], 'winner', parts[1]
        return "unknown", "winner", tagged_key

    def parse_pm_trade(self, trade_data: dict) -> Optional[PMTradeData]:
        """
        Parse raw Polymarket trade data into structured format.

        Args:
            trade_data: Dict from Polymarket activity API (flat or nested market)

        Returns:
            PMTradeData or None if parsing fails
        """
        try:
            market_info = trade_data.get('market', {})
            
            # Handle both flat (API) and nested structures
            if market_info:
                title = (market_info.get('title', '') or market_info.get('question', '')).lower()
                slug = (market_info.get('slug', '') or '').lower()
                market_id = market_info.get('id', '')
            else:
                # Flat structure - fields at top level
                title = (trade_data.get('title', '') or trade_data.get('question', '')).lower()
                slug = (trade_data.get('slug', '') or '').lower()
                market_id = trade_data.get('conditionId', trade_data.get('id', ''))
            
            # PM API uses conditionId/asset, fallback to tokenId for compatibility
            token_id = (
                trade_data.get('tokenId') or 
                trade_data.get('clobTokenId') or 
                trade_data.get('conditionId', '') or 
                trade_data.get('asset', '')
            )
            side = trade_data.get('side', 'buy').lower()
            
            # PM API uses 'size' or 'usdcSize'
            size = float(trade_data.get('size', 0) or trade_data.get('usdcSize', 0) or trade_data.get('amount', 0))

            if not token_id:
                return None

            # Skip zero-value trades
            if size <= 0:
                return None

            # Determine side - handle outcomeIndex (0=yes, 1=no) or outcome string
            if 'outcomeIndex' in trade_data:
                outcome = 'yes' if trade_data.get('outcomeIndex', 0) == 0 else 'no'
            else:
                outcome = trade_data.get('outcome', 'yes').lower()

            side = 'yes' if outcome == 'yes' else 'no'

            sport, teams, market_type, line = self._parse_market_title(title, slug)

            event_date = self._extract_date(slug, title)

            return PMTradeData(
                market_id=market_id,
                token_id=token_id,
                side=side,
                size=size,
                sport=sport,
                teams=teams,
                market_type=market_type,
                line=line,
                event_date=event_date
            )

        except Exception as e:
            return None

    def _parse_market_title(self, title: str, slug: str) -> Tuple[str, Tuple[str, str], str, Optional[float]]:
        """Parse market title to extract sport, teams, market type, and line."""
        sport = self._detect_sport(title, slug)
        teams = self._extract_teams(title, slug, sport)
        market_type = self._detect_market_type(title)
        line = self._extract_line(title, market_type)

        return sport, teams, market_type, line

    def _detect_sport(self, title: str, slug: str) -> str:
        """Detect sport from title or slug. Returns empty string for non-sports."""
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
        elif 'premier' in slug or 'laliga' in slug or 'serie-a' in slug or 'bundesliga' in slug:
            return 'soccer'
        elif 'epl' in slug or 'pl' in slug:
            return 'soccer'

        return ""  # Empty = not a sports market

    def _extract_teams(self, title: str, slug: str, sport: str) -> Tuple[str, str]:
        """Extract team abbreviations from title or slug.

        For spread markets like "Knicks (-5.5)", extract the team being bet on from title,
        not both teams from slug.
        """
        title_lower = title.lower()
        slug_lower = slug.lower()

        # For spread markets: extract the specific team being bet on from title
        if 'spread' in title_lower or self._detect_market_type(title_lower) == 'spread':
            # Find team mentioned in spread title like "Knicks (-5.5)" or "Timberwolves (-1.5)"
            bet_team_code = None
            for canonical, aliases in self._get_team_aliases(sport).items():
                for alias in aliases:
                    if alias in title_lower:
                        # Found a team being bet on
                        # Find the 3-letter code from the aliases set
                        for code in aliases:
                            if len(code) == 3:
                                bet_team_code = code.lower()
                                break
                        if bet_team_code:
                            break
                if bet_team_code:
                    break

            if bet_team_code:
                # For spread markets, we only care about the team being bet on
                # Get opponent from slug: "nba-den-nyk-..." with bet_team='nyk' → opponent='den'
                parts = slug_lower.split('-')
                if len(parts) >= 3:
                    for part in parts[1:3]:  # Check team codes from slug
                        if part.lower() != bet_team_code and len(part) >= 2 and len(part) <= 4:
                            # Found opponent
                            return (bet_team_code[:3], part[:3])

                # Fallback: return bet_team with empty string for opponent
                return (bet_team_code[:3], '')

        # For non-spread markets: Try slug first: "nhl-tor-cal-2026-01-17" → ("tor", "cal")
        extracted_teams = None
        if slug:
            parts = slug_lower.split('-')
            if len(parts) >= 3:
                team1 = parts[1].lower()
                team2 = parts[2].lower()
                if len(team1) >= 2 and len(team2) >= 2:
                    extracted_teams = (team1, team2)

        # Normalize extracted teams using aliases
        if extracted_teams:
            team1, team2 = extracted_teams
            normalized = self._normalize_team_code(team1, team2, sport)
            if normalized:
                return normalized

        # Try title with team aliases - return canonical 3-letter codes
        for canonical, aliases in self._get_team_aliases(sport).items():
            # Find which aliases from this team appear in title
            found_alias = None
            for alias in aliases:
                if alias in title.lower():
                    found_alias = alias
                    break
            
            if found_alias:
                # Look for a second team
                for canonical2, aliases2 in self._get_team_aliases(sport).items():
                    if canonical2 != canonical:
                        for alias2 in aliases2:
                            if alias2 in title.lower():
                                # Return 3-letter canonical codes
                                code1 = canonical if len(canonical) == 3 else self._get_3letter_code(canonical, sport)
                                code2 = canonical2 if len(canonical2) == 3 else self._get_3letter_code(canonical2, sport)
                                return (code1, code2)

        return ("", "")

    def _normalize_team_code(self, team1: str, team2: str, sport: str) -> Optional[Tuple[str, str]]:
        """Normalize team codes using alias mapping.
        
        For NHL, use 3-letter codes directly.
        For other sports, use canonical names.
        """
        aliases = self._get_team_aliases(sport)
        
        # Build reverse mapping: alias -> canonical (for non-NHL)
        alias_to_canonical = {}
        for canonical, alias_set in aliases.items():
            for alias in alias_set:
                alias_to_canonical[alias.lower()] = canonical.lower()

        # For ALL sports, extract 3-letter codes from aliases
        # Get all 3-letter codes from canonical names and aliases
        three_letter_codes = set()
        for canonical in aliases.keys():
            if len(canonical) == 3:
                three_letter_codes.add(canonical.lower())
        
        # Also check aliases for 3-letter codes
        for alias_set in aliases.values():
            for alias in alias_set:
                if len(alias) == 3:
                    three_letter_codes.add(alias.lower())
        
        # Find which 3-letter code matches
        t1 = team1.lower()
        t2 = team2.lower()
        
        # Use exact match for 3-letter codes first
        if t1 in three_letter_codes:
            norm_team1 = t1
        else:
            # Try to find canonical, then extract 3-letter from it
            canonical1 = alias_to_canonical.get(t1, t1)
            norm_team1 = canonical1 if len(canonical1) == 3 else self._get_3letter_from_canonical(canonical1, aliases)
            
        if t2 in three_letter_codes:
            norm_team2 = t2
        else:
            canonical2 = alias_to_canonical.get(t2, t2)
            norm_team2 = canonical2 if len(canonical2) == 3 else self._get_3letter_from_canonical(canonical2, aliases)

        # Return sorted
        if norm_team1 and norm_team2:
            return (norm_team1, norm_team2)
        return None

    def _get_3letter_code(self, canonical: str, sport: str) -> str:
        """Extract 3-letter code from canonical name or aliases."""
        # If already 3 letters, return as-is
        if len(canonical) == 3:
            return canonical.lower()
        
        # Look through aliases for 3-letter code
        aliases = self._get_team_aliases(sport)
        for alias_set in aliases.values():
            for alias in alias_set:
                if len(alias) == 3:
                    return alias.lower()
        
        # Fallback: return first 3 chars
        return canonical[:3].lower()

    def _get_3letter_from_canonical(self, canonical: str, aliases: dict) -> str:
        """Extract 3-letter code from a canonical team name using aliases."""
        canonical_lower = canonical.lower()
        
        # Direct match - canonical is already 3 letters
        if len(canonical_lower) == 3 and canonical_lower in aliases:
            return canonical_lower
        
        # Find the canonical entry that matches
        for can_name, alias_set in aliases.items():
            if can_name.lower() == canonical_lower or canonical_lower in alias_set:
                # Found it! Return the canonical name if it's 3 letters
                if len(can_name) == 3:
                    return can_name.lower()
                # Otherwise look for a 3-letter alias
                for alias in alias_set:
                    if len(alias) == 3:
                        return alias.lower()
        
        # Ultimate fallback: first 3 chars
        return canonical_lower[:3]

    def _get_team_aliases(self, sport: str) -> dict:
        """Get team aliases for sport."""
        from src.services.team_mappings import TEAM_ALIASES
        return TEAM_ALIASES

    def _detect_market_type(self, title: str) -> str:
        """Detect market type from title."""
        title_lower = title.lower()

        # Use regex matching for spread patterns
        for pattern in self.SPREAD_PATTERNS:
            if re.search(pattern, title_lower):
                return 'spread'
        
        # Use regex matching for total patterns  
        for pattern in self.TOTAL_PATTERNS:
            if re.search(pattern, title_lower):
                return 'total'
        
        # Use regex matching for winner patterns
        for pattern in self.WINNER_PATTERNS:
            if re.search(pattern, title_lower):
                return 'winner'

        return 'winner'

    def _extract_line(self, title: str, market_type: str, market_id: str = "") -> Optional[float]:
        """Extract line number (spread or total) from title or ID."""
        if market_type not in ('spread', 'total'):
            return None

        # Try title first
        match = re.search(r'([-+]?\d+\.?\d*)', title)
        if match:
            return float(match.group(1))

        # For Kalshi totals/spreads, line is often in the ID (e.g., "KXNBATOTAL-26FEB04BOSHOU-231")
        if market_id:
            id_match = re.search(r'-(\d+\.?\d*)$', market_id)
            if id_match:
                return float(id_match.group(1))

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
        """Find matching Kalshi market for PM trade."""

        if not pm_trade.sport:
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
            match = self._find_best_match(
                sport_markets[game_key],
                pm_trade,
                confidence=1.0,
                match_type='exact'
            )
            if match:
                return match

        # DISABLED: Fuzzy matching causing false positives with unrelated games
        # Only use exact game keys for now
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
            ks_market_id = ks_market.get('id', '')

            # Use stored market type (from _build_index)
            ks_market_type = ks_market.get('market_type', 'winner')
            if ks_market_type != pm_trade.market_type:
                continue

            # For spread markets: ensure we match the team being bet on
            if pm_trade.market_type == 'spread' and len(pm_trade.teams) >= 1:
                bet_team = pm_trade.teams[0].lower()
                # Check if Kalshi market mentions the team being bet on
                # For "Knicks (-5.5)", bet_team='nyk', we need market mentioning Knicks
                team_mentioned = False
                for team in [bet_team]:
                    if team in ks_title:
                        team_mentioned = True
                        break
                if not team_mentioned:
                    # Skip this market - it's for the opponent, not the bet team
                    continue

            # For spreads/totals, match line number (allow 1.0 point tolerance)
            # For spreads, PM uses negative/positive (e.g., -2.5) while Kalshi uses positive (2.5)
            if pm_trade.market_type in ('spread', 'total'):
                ks_line = self._extract_line(ks_title, ks_market_type, ks_market_id)
                if ks_line is not None and pm_trade.line is not None:
                    # For spreads, use absolute values for comparison
                    pm_line_abs = abs(pm_trade.line) if pm_trade.market_type == 'spread' else pm_trade.line
                    if abs(ks_line - pm_line_abs) > 1.0:
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

        # Handle TOTALS markets (over/under)
        if pm_trade.market_type == 'total':
            # For totals: YES = over, NO = under
            # PM side tells us if whale bet over or under
            if 'over' in ks_title or 'o/u' in ks_title or 'total points' in ks_title:
                # Kalshi totals are always YES=over
                return 'yes' if pm_trade.side == 'yes' else 'no'
            return None

        # Handle WINNER/SPREAD markets
        team1, team2 = pm_trade.teams

        # Check which team is mentioned in the Kalshi market title
        ks_team = None
        for team in [team1, team2]:
            if self._team_mentioned_in_title(team, ks_title):
                ks_team = team
                break

        if not ks_team:
            return None

        # For winner/spread: match the side whale took
        return pm_trade.side

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
