"""
Price filter — compares actual product price with threshold from XLSX.
"""

import logging

logger = logging.getLogger(__name__)


def passes_price_filter(product: dict, max_price: float) -> bool:
    """
    Check if a product passes the price filter.
    Returns True if current_price <= max_price.
    """
    current_price = product.get("current_price")

    if current_price is None:
        logger.warning(
            "Nie udało się odczytać ceny dla: %s — pomijam",
            product.get("url", "?")
        )
        return False

    if current_price <= max_price:
        logger.info(
            "✅ PRZESZŁO: %.2f PLN ≤ %.2f PLN — %s",
            current_price, max_price, product.get("name", "?")
        )
        return True
    else:
        logger.info(
            "❌ ODRZUCONE: %.2f PLN > %.2f PLN — %s",
            current_price, max_price, product.get("name", "?")
        )
        return False
