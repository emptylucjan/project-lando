"""
Shox Monitor — wyszukuje produkty Nike Shox na Zalando.pl,
filtruje te których URL nie ma jeszcze w produkty.xlsx,
oblicza buy price w EUR i wysyła alerty na Discorda.

Uruchomienie: python monitor_shox.py
Możesz też wrzucić do Taskera/crona żeby odpałał co kilka godzin.
"""

import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# ─────────────────────────────────────────────
#  KONFIGURACJA — edytuj tutaj
# ─────────────────────────────────────────────
SEARCH_QUERY    = "shox"
MAX_BUY_EUR     = 85.0      # alert gdy buy price poniżej tej kwoty
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1483592981725315213/VyUd3jeQVxmv3SCj7IbNia8dvaSzW9xD9Z_jS_nM7Yv0Qp18y3hjZ42SBxHUNhLjUsMF"
XLSX_FILE       = os.path.join(PROJECT_ROOT, "produkty.xlsx")
# ─────────────────────────────────────────────

from scraper.browser import create_browser, accept_cookies
from scraper.pricing import get_eur_rate, calculate_buy_price_eur
from scraper.discord import send_discord_alert


def load_watched_urls() -> set:
    """Load URLs from column A of produkty.xlsx (skip header row)."""
    try:
        import openpyxl
        if not os.path.exists(XLSX_FILE):
            logger.warning("Brak pliku %s — wszystkie produkty będą traktowane jako nowe", XLSX_FILE)
            return set()
        wb = openpyxl.load_workbook(XLSX_FILE, read_only=True)
        ws = wb.active
        urls = set()
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row and row[0] and str(row[0]).startswith("http"):
                urls.add(str(row[0]).strip())
        wb.close()
        logger.info("Załadowano %d obserwowanych URLi z xlsx", len(urls))
        return urls
    except Exception as e:
        logger.error("Błąd wczytywania xlsx: %s", e)
        return set()


def search_zalando(driver, query: str) -> list:
    """
    Open Zalando search results for `query` and extract product cards.
    Returns list: {name, brand, url, current_price, original_price, discount_pct, image_url}
    """
    search_url = f"https://www.zalando.pl/katalog/?q={query}"
    logger.info("Otwieram wyniki wyszukiwania: %s", search_url)
    driver.get(search_url)
    time.sleep(3)

    for _ in range(5):
        driver.execute_script("window.scrollBy(0, window.innerHeight * 1.5);")
        time.sleep(0.8)
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)

    products = driver.execute_script("""
        var results = [];
        var seen = {};
        var anchors = document.querySelectorAll('a[href]');

        for (var i = 0; i < anchors.length; i++) {
            var href = anchors[i].href || '';
            if (!href.includes('zalando.pl')) continue;
            var pathname = href.split('?')[0];
            if (!pathname.match(/\\-[a-z0-9]{6,}\\-[a-z0-9]+\\.html$/)) continue;
            if (seen[pathname]) continue;
            seen[pathname] = true;

            var card = anchors[i];
            for (var k = 0; k < 8; k++) {
                if (!card.parentElement) break;
                card = card.parentElement;
                if (card.tagName === 'ARTICLE' || card.tagName === 'LI') break;
                if (card.offsetHeight > 600) break;
            }

            var cardText = card.innerText || '';

            // Skip marketplace "od X zł" prices — those are minimum partner prices
            var odPrices = {};
            var odRegex = /\\bod\\s+(\\d[\\d\\s]*[.,]\\d{2})\\s*z/gi;
            var om;
            while ((om = odRegex.exec(cardText)) !== null) {
                var odVal = parseFloat(om[1].replace(/\\s/g, '').replace(',', '.'));
                odPrices[odVal] = true;
            }

            // Collect all prices NOT prefixed with "od"
            var allPrices = [];
            var priceRegex = /(\\d[\\d\\s]*[.,]\\d{2})\\s*zł/g;
            var pm;
            while ((pm = priceRegex.exec(cardText)) !== null) {
                var pVal = parseFloat(pm[1].replace(/\\s/g, '').replace(',', '.'));
                if (pVal > 0 && !odPrices[pVal] && allPrices.indexOf(pVal) === -1) allPrices.push(pVal);
            }
            if (allPrices.length === 0) continue;

            var current_price  = Math.min.apply(null, allPrices);
            var original_price = allPrices.length > 1 ? Math.max.apply(null, allPrices) : null;
            var discount_pct   = null;
            if (original_price && original_price > current_price) {
                discount_pct = Math.round((1 - current_price / original_price) * 100);
            }

            var nameEl = card.querySelector('h3, h2, h1, [class*="name"], [class*="title"]');
            var name = nameEl ? nameEl.innerText.trim() : anchors[i].innerText.trim();
            if (!name) continue;

            var brandEl = card.querySelector('[class*="brand"], [class*="Brand"]');
            var brand = brandEl ? brandEl.innerText.trim() : '';
            if (!brand && name.includes('\\n')) brand = name.split('\\n')[0].trim();

            var img = card.querySelector('img');
            var imgUrl = img ? (img.src || img.getAttribute('data-src') || '') : '';
            if (imgUrl && imgUrl.length < 30) imgUrl = '';

            results.push({
                url:            pathname,
                name:           name.replace(/\\n/g, ' ').trim(),
                brand:          brand,
                current_price:  current_price,
                original_price: original_price,
                discount_pct:   discount_pct,
                image_url:      imgUrl || null
            });
        }
        return results;
    """)

    count = len(products) if products else 0
    logger.info("Znaleziono %d produktów na stronie wyników", count)
    return products or []






def run_monitor():
    logger.info("=" * 60)
    logger.info("SHOX MONITOR — start")
    logger.info("Szukam: '%s' | Próg buy price: %.2f EUR", SEARCH_QUERY, MAX_BUY_EUR)
    logger.info("=" * 60)

    # Load EUR rate once
    eur_rate = get_eur_rate()
    logger.info("Kurs EUR/PLN: %.4f", eur_rate)

    # Load already-watched URLs
    watched_urls = load_watched_urls()

    driver = create_browser(headless=False)

    try:
        driver.get("https://www.zalando.pl")
        time.sleep(2)
        accept_cookies(driver)
        time.sleep(2)

        products = search_zalando(driver, SEARCH_QUERY)

    finally:
        driver.quit()
        logger.info("Przeglądarka zamknięta")

    if not products:
        logger.warning("Brak produktów w wynikach — koniec")
        return

    # Filter + evaluate
    stats = {"total": len(products), "new": 0, "alerted": 0, "too_expensive": 0}
    new_products = []

    for p in products:
        url_clean = p["url"].split("?")[0]
        if any(url_clean in w or w.split("?")[0] == url_clean for w in watched_urls):
            continue  # already watched

        stats["new"] += 1
        buy_eur = calculate_buy_price_eur(p["current_price"], eur_rate)
        p["buy_eur"] = buy_eur

        logger.info(
            "[NOWY] %s — %.2f PLN → buy %.2f EUR %s",
            p.get("name", "?")[:50],
            p["current_price"],
            buy_eur,
            "✅" if buy_eur <= MAX_BUY_EUR else "❌ za drogo",
        )

        if buy_eur <= MAX_BUY_EUR:
            stats["alerted"] += 1
            new_products.append(p)
        else:
            stats["too_expensive"] += 1

    # Send Discord alerts
    if new_products:
        logger.info("Wysyłam %d alert(y) na Discorda...", len(new_products))
        for p in new_products:
            send_discord_alert(DISCORD_WEBHOOK, p, p["buy_eur"], eur_rate)
            time.sleep(0.5)  # small delay between webhooks
    else:
        logger.info("Brak nowych produktów poniżej %.2f EUR — żaden alert nie wysłany", MAX_BUY_EUR)

    # Summary
    logger.info("=" * 60)
    logger.info("PODSUMOWANIE")
    logger.info("Znalezione produkty:   %d", stats["total"])
    logger.info("Nowe (nie w xlsx):     %d", stats["new"])
    logger.info("Alerty wysłane:        %d", stats["alerted"])
    logger.info("Za drogie:             %d", stats["too_expensive"])
    logger.info("Kurs EUR/PLN użyty:    %.4f", eur_rate)
    logger.info("=" * 60)


if __name__ == "__main__":
    run_monitor()
