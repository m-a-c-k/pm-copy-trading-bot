#!/usr/bin/env python3
"""Test PM live order - WILL USE REAL MONEY."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

print("⚠️  LIVE MODE - This will place real orders with USDC!")
print("Wallet: 0xd4549c366965829bde8efdae823ff767f250b47f")
print("")
response = input("Type 'YES' to place a $0.50 test order: ")

if response != 'YES':
    print("Cancelled.")
    exit()

print("\n🔄 Setting up PM client with Builder auth...")

# TODO: Implement actual order placement
# Need to:
# 1. Find a cheap market (<$0.10 per share)
# 2. Get token_id
# 3. Sign order with private key
# 4. Submit via CLOB with Builder headers

print("\n❌ Actual order placement not yet implemented.")
print("Need to implement:")
print("  - EIP-712 order signing")
print("  - Token ID resolution")
print("  - Proper CLOB order submission")
