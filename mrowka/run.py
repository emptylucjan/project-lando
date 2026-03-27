"""
run.py — uruchamianie bota Mrówka v2 na Windows
Użycie: py -3.12 run.py   LUB:  uruchom start.bat
"""
import sys
import os
import asyncio
import pathlib

# Ustaw working directory na folder mrowka/
os.chdir(pathlib.Path(__file__).parent)

# Dodaj folder nadrzędny do path żeby importy scraper/ działały
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


import logger as _logger
_logger.setup_logging()

# Uruchom bota
import mrowka_bot
import json

with open("config.json", "r", encoding="utf-8") as f:
    cfg = json.load(f)

print("Starting bot loop...")
try:
    mrowka_bot.bot.run(cfg["discord_token"])
except KeyboardInterrupt:
    pass
