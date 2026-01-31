"""
Configuration Module for PM Copy Trading Bot
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BlockchainConfig:
    alchemy_api_key: str
    proxy_wallet: str
    private_key: str
    rpc_url: str = "https://polygon-rpc.com"
    
    @classmethod
    def from_env(cls) -> "BlockchainConfig":
        return cls(
            alchemy_api_key=os.getenv("ALCHEMY_API_KEY", ""),
            proxy_wallet=os.getenv("PROXY_WALLET", ""),
            private_key=os.getenv("PRIVATE_KEY", ""),
            rpc_url=f"https://polygon-mainnet.g.alchemy.com/v2/{os.getenv('ALCHEMY_API_KEY', '')}"
        )


@dataclass
class KellyConfig:
    kelly_fraction: float = 0.5
    max_trade_percent: float = 2.0
    max_trader_exposure: float = 10.0
    bankroll: float = 400.0
    
    @classmethod
    def from_env(cls) -> "KellyConfig":
        return cls(
            kelly_fraction=float(os.getenv("KELLY_FRACTION", "0.5")),
            max_trade_percent=float(os.getenv("MAX_TRADE_PERCENT", "2.0")),
            max_trader_exposure=float(os.getenv("MAX_TRADER_EXPOSURE", "10.0")),
            bankroll=float(os.getenv("BANKROLL", "400.0"))
        )


@dataclass
class CopyTradingConfig:
    user_addresses: list[str] = field(default_factory=list)
    trade_multiplier: float = 1.0
    fetch_interval: int = 1
    min_trader_trades: int = 10
    copy_delay_seconds: float = 2.0
    
    @classmethod
    def from_env(cls) -> "CopyTradingConfig":
        addresses = os.getenv("USER_ADDRESSES", "")
        return cls(
            user_addresses=[a.strip() for a in addresses.split(",") if a.strip()],
            trade_multiplier=float(os.getenv("TRADE_MULTIPLIER", "1.0")),
            fetch_interval=int(os.getenv("FETCH_INTERVAL", "1")),
            min_trader_trades=int(os.getenv("MIN_TRADER_TRADES", "10")),
            copy_delay_seconds=float(os.getenv("COPY_DELAY_SECONDS", "2.0"))
        )


@dataclass
class DatabaseConfig:
    mongo_uri: str
    database_name: str = "pm-copy-trading-bot"
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        return cls(
            mongo_uri=uri,
            database_name=os.getenv("MONGO_DATABASE", "pm-copy-trading-bot")
        )


@dataclass
class PerfectMoneyConfig:
    account_id: str = ""
    password: str = ""
    payee_account: str = ""
    enabled: bool = False
    
    @classmethod
    def from_env(cls) -> "PerfectMoneyConfig":
        account_id = os.getenv("PERFECT_MONEY_ACCOUNT_ID", "")
        return cls(
            account_id=account_id,
            password=os.getenv("PERFECT_MONEY_PASSWORD", ""),
            payee_account=os.getenv("PERFECT_MONEY_PAYEE_ACCOUNT", ""),
            enabled=bool(account_id)
        )


@dataclass
class Config:
    blockchain: BlockchainConfig
    kelly: KellyConfig
    copy_trading: CopyTradingConfig
    database: DatabaseConfig
    perfect_money: PerfectMoneyConfig
    
    @classmethod
    def load(cls, env_path: str = ".env") -> "Config":
        if os.path.exists(env_path):
            load_dotenv(env_path)
        
        return cls(
            blockchain=BlockchainConfig.from_env(),
            kelly=KellyConfig.from_env(),
            copy_trading=CopyTradingConfig.from_env(),
            database=DatabaseConfig.from_env(),
            perfect_money=PerfectMoneyConfig.from_env()
        )
    
    def validate(self) -> tuple[bool, list[str]]:
        errors = []
        if not self.blockchain.alchemy_api_key:
            errors.append("ALCHEMY_API_KEY is required")
        if not self.blockchain.proxy_wallet:
            errors.append("PROXY_WALLET is required")
        if not self.blockchain.private_key:
            errors.append("PRIVATE_KEY is required")
        if not self.copy_trading.user_addresses:
            errors.append("USER_ADDRESSES is required")
        return len(errors) == 0, errors


if __name__ == "__main__":
    print("Configuration Test")
    print("=" * 50)
    config = Config.load()
    print(f"Wallet: {config.blockchain.proxy_wallet}")
    print(f"Bankroll: ${config.kelly.bankroll}")
    print(f"Kelly Fraction: {config.kelly.kelly_fraction}x")
    print(f"Traders: {len(config.copy_trading.user_addresses)}")
    valid, errors = config.validate()
    print(f"Validation: {'PASSED' if valid else 'FAILED'}")
    if errors:
        for e in errors:
            print(f"  Error: {e}")
