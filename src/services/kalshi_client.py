"""
Kalshi API Client for Copy Trading Bot

Based on poly_bot_arb implementation.
"""

import os
import tempfile
from dataclasses import dataclass
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"


@dataclass
class KalshiConfig:
    api_key_id: str = ""
    private_key_pem: str = ""
    enabled: bool = False

    @classmethod
    def from_env(cls) -> "KalshiConfig":
        api_key_id = os.getenv("KALSHI_API_KEY_ID", "")
        pem_path = os.getenv("KALSHI_PRIVATE_KEY_PEM", "")
        private_key_pem = ""
        if pem_path and os.path.exists(pem_path):
            with open(pem_path, 'r') as f:
                private_key_pem = f.read()
        return cls(
            api_key_id=api_key_id,
            private_key_pem=private_key_pem,
            enabled=bool(api_key_id and private_key_pem)
        )


class KalshiClient:
    def __init__(self, config: KalshiConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def get_markets(self, series_ticker: str, sport: str) -> dict:
        """Fetch open markets for a given series."""
        if not self.config.enabled:
            return {}

        games = {}
        try:
            resp = self.session.get(
                f"{KALSHI_API}/markets",
                params={"series_ticker": series_ticker, "status": "open", "limit": 1000},
                timeout=30
            )
            if not resp.ok:
                return {}

            data = resp.json()
            markets = data.get('markets', [])

            for m in markets:
                event_ticker = m.get('event_ticker', '')
                title = (m.get('title') or "").lower()
                ticker = m.get('ticker', '')

                if not event_ticker or not title:
                    continue

                game_key = self._extract_game_key(event_ticker, title)
                if not game_key:
                    continue

                tagged_key = f"{sport}:{game_key}"

                if ',' in title:
                    continue

                yes_ask = float(m.get('yes_ask') or 50) / 100.0
                no_ask = (100.0 - float(m.get('yes_ask') or 50)) / 100.0

                if tagged_key not in games:
                    games[tagged_key] = []

                games[tagged_key].append({
                    'title': title,
                    'yes': yes_ask,
                    'no': no_ask,
                    'id': ticker,
                    'event_ticker': event_ticker,
                })

        except Exception:
            return {}

        return games

    def _extract_game_key(self, event_ticker: str, title: str) -> Optional[str]:
        """Extract normalized game key from Kalshi event ticker."""
        import re
        if not event_ticker:
            return None

        parts = event_ticker.upper().split('-')
        if len(parts) < 2:
            return None

        date_teams = parts[-1]
        teams_only = re.sub(r'^\d{2}[A-Z]{3}\d{2}', '', date_teams)

        if len(teams_only) < 4:
            return None

        if len(teams_only) == 6:
            team1 = teams_only[:3].lower()
            team2 = teams_only[3:].lower()
            return '-'.join(sorted([team1, team2]))
        elif len(teams_only) == 5:
            team1 = teams_only[:3].lower()
            team2 = teams_only[3:].lower()
            return '-'.join(sorted([team1, team2]))
        elif len(teams_only) == 7:
            team1 = teams_only[:4].lower()
            team2 = teams_only[4:].lower()
            return '-'.join(sorted([team1, team2]))

        return None

    def get_all_markets(self) -> dict:
        """Fetch all sports markets from Kalshi."""
        series_configs = [
            ("KXNFLGAME", "nfl"),
            ("KXNFLSPREAD", "nfl"),
            ("KXNFLTOTAL", "nfl"),
            ("KXCFBGAME", "cfb"),
            ("KXCFBSPREAD", "cfb"),
            ("KXCFBTOTAL", "cfb"),
            ("KXNCAAMBGAME", "cbb"),
            ("KXNCAAMBSPREAD", "cbb"),
            ("KXNCAAMBTOTAL", "cbb"),
            ("KXNBAGAME", "nba"),
            ("KXNBASPREAD", "nba"),
            ("KXNBATOTAL", "nba"),
        ]

        all_games = {}
        for series_ticker, sport in series_configs:
            markets = self.get_markets(series_ticker, sport)
            all_games.update(markets)

        return all_games

    def place_order(self, market_ticker: str, side: str, count: int, price: int = 99) -> dict:
        """Place a market order on Kalshi."""
        if not self.config.enabled:
            return {"success": False, "error": "Kalshi not enabled"}

        try:
            from kalshi_python import Configuration, PortfolioApi, ApiClient, CreateOrderRequest
            import tempfile

            pem = self.config.private_key_pem.replace('\\n', '\n')
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
                f.write(pem)
                key_path = f.name

            config = Configuration(host=KALSHI_API)
            api_client = ApiClient(config)
            api_client.set_kalshi_auth(self.config.api_key_id, key_path)
            portfolio_api = PortfolioApi(api_client)

            order_kwargs = {
                'ticker': market_ticker,
                'side': side.lower(),
                'action': 'buy',
                'count': int(count),
                'type': 'market',
            }

            if side.lower() == 'yes':
                order_kwargs['yes_price'] = price
            else:
                order_kwargs['no_price'] = price

            response = portfolio_api.create_order(**order_kwargs)
            os.unlink(key_path)

            order_obj = getattr(response, 'order', response)
            order_id = getattr(order_obj, 'order_id', None)
            status = getattr(order_obj, 'status', None)

            return {"success": bool(order_id), "order_id": order_id, "status": status}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_balance(self) -> float:
        """Get account balance."""
        if not self.config.enabled:
            return 0.0

        try:
            from kalshi_python import Configuration, PortfolioApi, ApiClient
            import tempfile

            pem = self.config.private_key_pem.replace('\\n', '\n')
            with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
                f.write(pem)
                key_path = f.name

            config = Configuration(host=KALSHI_API)
            api_client = ApiClient(config)
            api_client.set_kalshi_auth(self.config.api_key_id, key_path)
            portfolio_api = PortfolioApi(api_client)

            resp = portfolio_api.get_portfolio()
            os.unlink(key_path)

            balance_cents = getattr(resp, 'balance_cents', 0)
            return float(balance_cents) / 100.0 if balance_cents else 0.0

        except Exception:
            return 0.0


if __name__ == "__main__":
    config = KalshiConfig.from_env()
    print(f"Kalshi enabled: {config.enabled}")
    if config.enabled:
        client = KalshiClient(config)
        balance = client.get_balance()
        print(f"Balance: ${balance}")
        markets = client.get_all_markets()
        print(f"Markets found: {len(markets)}")
