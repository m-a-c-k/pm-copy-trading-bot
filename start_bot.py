#!/usr/bin/env python3
"""Start copy trading bot."""

import os
os.chdir('/Users/alexandrastarnes/Documents/mack/github/pm-copy-trading-bot')

from src.config.config import Config
from src.services.kelly_calculator import KellyCalculator
from dotenv import load_dotenv

load_dotenv()
config = Config.load()

print('=' * 60)
print('COPY TRADING BOT - FollowMeABC123')
print('=' * 60)
print()
print('Wallet:', config.blockchain.proxy_wallet[:16], '...')
print('Bankroll: $%.2f' % config.kelly.bankroll)
print('Kelly: %.1fx' % config.kelly.kelly_fraction)
print('Max trade: $%.2f' % ((config.kelly.max_trade_percent/100) * config.kelly.bankroll))
print()
print('Trader:', config.copy_trading.user_addresses[0][:20], '...')
print()
print('BOT READY!')
print('=' * 60)
