#!/usr/bin/env python3
"""
Explicit team name mappings for cross-platform market matching.
SAFE: Only matches known aliases - never guesses.
"""

from typing import Dict, Set, Tuple, Optional
import re

TEAM_ALIASES: Dict[str, Set[str]] = {
    "utah jazz": {"utah", "uta", "jazz"},
    "boston celtics": {"boston", "bos", "celtics"},
    "brooklyn nets": {"brooklyn", "bkn", "nets"},
    "charlotte hornets": {"charlotte", "cha", "hornets"},
    "chicago bulls": {"chicago", "chi", "bulls"},
    "cleveland cavaliers": {"cleveland", "cle", "cavaliers", "cavs"},
    "dallas mavericks": {"dallas", "dal", "mavericks", "mavs"},
    "denver nuggets": {"denver", "den", "nuggets"},
    "detroit pistons": {"detroit", "det", "pistons"},
    "golden state warriors": {"golden state", "gsw", "warriors"},
    "houston rockets": {"houston", "hou", "rockets"},
    "indiana pacers": {"indiana", "ind", "pacers"},
    "la clippers": {"la clippers", "lac", "clippers"},
    "la lakers": {"la lakers", "lal", "lakers"},
    "memphis grizzlies": {"memphis", "mem", "grizzlies"},
    "miami heat": {"miami", "mia", "heat"},
    "milwaukee bucks": {"milwaukee", "mil", "bucks"},
    "minnesota timberwolves": {"minnesota", "min", "timberwolves", "twolves"},
    "new orleans pelicans": {"new orleans", "nop", "pelicans"},
    "new york knicks": {"new york", "nyk", "knicks"},
    "oklahoma city thunder": {"oklahoma city", "okc", "thunder"},
    "orlando magic": {"orlando", "orl", "magic"},
    "philadelphia 76ers": {"philadelphia", "phi", "76ers", "sixers"},
    "phoenix suns": {"phoenix", "phx", "suns"},
    "portland trail blazers": {"portland", "por", "trail blazers", "blazers"},
    "sacramento kings": {"sacramento", "sac", "kings"},
    "san antonio spurs": {"san antonio", "sas", "spurs"},
    "toronto raptors": {"toronto", "tor", "raptors"},
    "washington wizards": {"washington", "wsh", "wizards"},
    "arizona cardinals": {"arizona", "ari", "cardinals"},
    "atlanta falcons": {"atlanta", "atl", "falcons"},
    "baltimore ravens": {"baltimore", "bal", "ravens"},
    "buffalo bills": {"buffalo", "buf", "bills"},
    "carolina panthers": {"carolina", "car", "panthers"},
    "chicago bears": {"chicago", "chi", "bears"},
    "cincinnati bengals": {"cincinnati", "cin", "bengals"},
    "cleveland browns": {"cleveland", "cle", "browns"},
    "dallas cowboys": {"dallas", "dal", "cowboys"},
    "denver broncos": {"denver", "den", "broncos"},
    "detroit lions": {"detroit", "det", "lions"},
    "green bay packers": {"green bay", "gb", "packers"},
    "houston texans": {"houston", "hou", "texans"},
    "indianapolis colts": {"indianapolis", "ind", "colts"},
    "jacksonville jaguars": {"jacksonville", "jax", "jaguars"},
    "kansas city chiefs": {"kansas city", "kc", "chiefs"},
    "las vegas raiders": {"las vegas", "lv", "raiders"},
    "la chargers": {"la chargers", "lac", "chargers"},
    "la rams": {"la rams", "lar", "rams"},
    "miami dolphins": {"miami", "mia", "dolphins"},
    "minnesota vikings": {"minnesota", "min", "vikings"},
    "new england patriots": {"new england", "ne", "patriots"},
    "new orleans saints": {"new orleans", "no", "saints"},
    "new york giants": {"new york giants", "nyg", "giants"},
    "new york jets": {"new york jets", "nyj", "jets"},
    "philadelphia eagles": {"philadelphia", "phi", "eagles"},
    "pittsburgh steelers": {"pittsburgh", "pit", "steelers"},
    "san francisco 49ers": {"san francisco", "sf", "49ers"},
    "seattle seahawks": {"seattle", "sea", "seahawks"},
    "tampa bay buccaneers": {"tampa bay", "tb", "buccaneers"},
    "tennessee titans": {"tennessee", "ten", "titans"},
    "washington commanders": {"washington", "wsh", "commanders"},
    # NHL Teams - Using 3-letter codes as canonical for matching
    "cgy": {"calgary", "cgy", "flames", "cal"},
    "edm": {"edmonton", "edm", "oilers"},
    "van": {"vancouver", "van", "canucks"},
    "vgk": {"vegas", "vgk", "golden knights"},
    "lak": {"los angeles kings", "la", "lak", "kings", "los angeles"},
    "sea": {"seattle", "sea", "kraken"},
    "dal": {"dallas", "dal", "stars"},
    "stl": {"st. louis", "stl", "blues"},
    "col": {"colorado", "col", "avalanche"},
    "sjc": {"san jose", "sjc", "sharks"},
    "chi": {"chicago", "chi", "blackhawks"},
    "cbj": {"columbus", "cbj", "blue jackets"},
    "det": {"detroit", "det", "red wings"},
    "uta": {"utah", "uta", "utah hockey club"},
    "bos": {"boston", "bos", "bruins"},
    "fla": {"florida", "fla", "panthers"},
    "mtl": {"montreal", "mtl", "canadien"},
    "wpg": {"winnipeg", "wpg", "jets"},
    "min": {"minnesota", "min", "wild"},
    "nsh": {"nashville", "nsh", "predators"},
    "tor": {"toronto", "tor", "maple leafs"},
    "ott": {"ottawa", "ott", "senators"},
    "pit": {"pittsburgh", "pit", "penguins"},
    "nyi": {"new york islanders", "nyi", "islanders"},
    "nyr": {"new york rangers", "nyr", "rangers"},
    "njd": {"new jersey devils", "njd", "devils", "nj"},
    "phi": {"philadelphia", "phi", "flyers"},
    "wsh": {"washington", "wsh", "capitals", "capitals"},
    "car": {"carolina", "car", "hurricanes"},
    "buf": {"buffalo", "buf", "sabres"},
    "tbl": {"tampa bay", "tbl", "lightning"},
    "ana": {"anaheim", "ana", "ducks"},
    "ari": {"arizona", "ari", "coyotes"},
    "uconn": {"uconn", "connecticut"},
    "houston": {"houston", "hou"},
    "purdue": {"purdue"},
    "tennessee": {"tennessee", "ten"},
    "arizona": {"arizona", "ari"},
    "gonzaga": {"gonzaga"},
    "duke": {"duke"},
    "kansas": {"kansas"},
    "baylor": {"baylor"},
    "villanova": {"villanova"},
    "texas": {"texas"},
    "kentucky": {"kentucky"},
}

_CANONICAL_FROM_ALIAS: Dict[str, str] = {}
for canonical, aliases in TEAM_ALIASES.items():
    for alias in aliases:
        _CANONICAL_FROM_ALIAS[alias.lower()] = canonical


def normalize(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', name.lower().strip())


def get_canonical(name: str) -> Optional[str]:
    if not name:
        return None
    return _CANONICAL_FROM_ALIAS.get(normalize(name))


def is_same_team(name1: str, name2: str) -> bool:
    if not name1 or not name2:
        return False
    c1 = get_canonical(name1)
    c2 = get_canonical(name2)
    if c1 and c2:
        return c1 == c2
    return normalize(name1) == normalize(name2)


def extract_teams_from_slug(slug: str) -> Tuple[Optional[str], Optional[str]]:
    parts = slug.split('-')
    if len(parts) >= 3:
        return parts[1], parts[2]
    return None, None


def extract_teams_from_ticker(ticker: str) -> Tuple[Optional[str], Optional[str]]:
    ticker = re.sub(r'^KX', '', ticker)
    ticker = re.sub(r'GAME-?\d*[A-Z]*', '', ticker)
    match = re.search(r'([A-Z]{3})([A-Z]{3,4})$', ticker)
    if match:
        return match.group(1).lower(), match.group(2).lower()
    return None, None


def log_unknown_team(name: str, platform: str) -> None:
    print(f"  [UNKNOWN] {platform}: '{name}' - consider adding to TEAM_ALIASES")
