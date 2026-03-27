"""
Main entry point — reads product URLs from XLSX, scrapes prices, filters, saves.
"""

import json
import os
from typing import List
import sys
import logging
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from scraper.browser import create_browser, accept_cookies, random_delay
from scraper.extractor import extract_product_data
from scraper.price_filter import passes_price_filter
from offers.storage import add_offer


def load_config() -> dict:
    """Load configuration from config.json."""
    config_path = os.path.join(PROJECT_ROOT, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_products_from_xlsx(filepath: str) -> List[dict]:
    """
    Load product URLs and max prices from XLSX file.
    Expected columns: URL (col A), Max Cena (col B)
    """
    try:
        import openpyxl
    except ImportError:
        logger.error("Brak modułu openpyxl. Zainstaluj: pip install openpyxl")
        sys.exit(1)

    products = []
    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not row[0]:
            continue

        url = str(row[0]).strip()
        if not url.startswith("http"):
            logger.warning("Wiersz %d: nieprawidłowy URL — pomijam: %s", row_num, url)
            continue

        try:
            max_price = float(row[1]) if row[1] is not None else None
        except (ValueError, TypeError):
            logger.warning("Wiersz %d: nieprawidłowa cena — pomijam: %s", row_num, row[1])
            continue

        if max_price is None:
            logger.warning("Wiersz %d: brak max ceny — pomijam", row_num)
            continue

        products.append({"url": url, "max_price": max_price})

    wb.close()
    logger.info("Załadowano %d produktów z %s", len(products), filepath)
    return products


def run_scraper():
    """Main scraper loop."""
    config = load_config()

    xlsx_path = os.path.join(PROJECT_ROOT, config["xlsx_file"])
    if not os.path.exists(xlsx_path):
        logger.error("Nie znaleziono pliku XLSX: %s", xlsx_path)
        logger.info("Utwórz plik '%s' z kolumnami: URL | Max Cena", config["xlsx_file"])
        sys.exit(1)

    products = load_products_from_xlsx(xlsx_path)
    if not products:
        logger.warning("Brak produktów do sprawdzenia!")
        return

    delay_range = config.get("delay_between_requests_sec", [3, 7])
    headless = config.get("headless", False)

    logger.info("=" * 60)
    logger.info("ZALANDO SCRAPER — Start")
    logger.info("Produktów do sprawdzenia: %d", len(products))
    logger.info("=" * 60)

    driver = create_browser(headless=headless)
    stats = {"checked": 0, "passed": 0, "failed": 0, "errors": 0}

    try:
        # First visit to handle cookies
        driver.get("https://www.zalando.pl")
        time.sleep(3)
        accept_cookies(driver)
        random_delay(*delay_range)

        for i, prod_entry in enumerate(products, 1):
            url = prod_entry["url"]
            max_price = prod_entry["max_price"]

            logger.info("—" * 40)
            logger.info("[%d/%d] Sprawdzam: %s", i, len(products), url)
            logger.info("Max cena: %.2f PLN", max_price)

            product_data = extract_product_data(driver, url, max_price=max_price)

            if product_data is None:
                stats["errors"] += 1
                logger.error("Nie udało się pobrać danych — pomijam")
                random_delay(*delay_range)
                continue

            stats["checked"] += 1

            if passes_price_filter(product_data, max_price):
                added = add_offer(product_data, max_price)
                if added:
                    stats["passed"] += 1
                    logger.info("➕ Dodano do oferty!")
                else:
                    logger.info("Produkt już był w ofercie (duplikat)")
            else:
                stats["failed"] += 1

            # Random delay before next product
            if i < len(products):
                random_delay(*delay_range)

    except KeyboardInterrupt:
        logger.info("\nPrzerwano przez użytkownika (Ctrl+C)")
    except Exception as e:
        logger.error("Nieoczekiwany błąd: %s", e, exc_info=True)
    finally:
        driver.quit()
        logger.info("Przeglądarka zamknięta")

    # Summary
    logger.info("=" * 60)
    logger.info("PODSUMOWANIE")
    logger.info("Sprawdzono: %d", stats["checked"])
    logger.info("Dodano do oferty: %d", stats["passed"])
    logger.info("Odrzucono (za drogo): %d", stats["failed"])
    logger.info("Błędy: %d", stats["errors"])
    logger.info("=" * 60)


if __name__ == "__main__":
    run_scraper()
