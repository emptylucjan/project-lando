"""
Pricing utilities — buy price formula and EUR/PLN exchange rate from NBP API.

Formula: buy_eur = (price_pln * 0.8) / 1.23 / eur_rate
  - * 0.8  → our purchase price is 80% of Zalando price
  - / 1.23 → strip VAT margin
  - / rate → PLN to EUR conversion (live rate from NBP)
"""

import json
import logging
import time
import urllib.request

logger = logging.getLogger(__name__)

# Cache: (rate_value, timestamp)
_eur_rate_cache: tuple = (None, 0)
_CACHE_TTL = 86400  # seconds (24 hours — fetch once per day)


def get_eur_rate() -> float:
    """
    Fetch live EUR/PLN exchange rate from NBP API.
    Cached for 1 hour to avoid hammering the API.
    Falls back to 4.25 if request fails.
    """
    global _eur_rate_cache
    rate, ts = _eur_rate_cache
    if rate and (time.time() - ts) < _CACHE_TTL:
        return rate

    try:
        url = "https://api.nbp.pl/api/exchangerates/rates/A/EUR/?format=json"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            rate = float(data["rates"][0]["mid"])
            _eur_rate_cache = (rate, time.time())
            logger.info("Kurs EUR/PLN z NBP: %.4f", rate)
            return rate
    except Exception as e:
        fallback = 4.25
        logger.warning("Nie udało się pobrać kursu EUR z NBP (%s) — używam %.2f", e, fallback)
        return fallback


def calculate_buy_price_eur(price_pln: float, eur_rate: float = None) -> float:
    """
    Calculate buy price in EUR using the formula:
        buy_eur = (price_pln * 0.8) / 1.23 / eur_rate

    If eur_rate is not provided, fetches live rate from NBP.
    """
    if eur_rate is None:
        eur_rate = get_eur_rate()
    return round((price_pln * 0.8) / 1.23 / eur_rate, 2)
