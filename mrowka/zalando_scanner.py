"""
zalando_scanner.py — Skanuje Zalando URL przez Selenium, zwraca cenę i EANy.
Uruchamiany w osobnym wykonaniu asyncio (executor) żeby nie blokować Discord.
Importuje z istniejącego scraperа projektu.
"""
from __future__ import annotations
import sys
import os
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional, Union

log = logging.getLogger("mrowka.scanner")

# Dodaj główny folder projektu do path żeby móc importować scraper/
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, _PROJECT_ROOT)


@dataclass
class ScanResult:
    url: str
    name: Optional[str] = None
    brand: Optional[str] = None
    sku: Optional[str] = None          # Numer modelu (SKU) — taki sam dla wszystkich rozmiarów
    current_price: Optional[float] = None
    original_price: Optional[float] = None
    size_to_ean: dict[str, Optional[str]] = field(default_factory=dict)
    error: Optional[str] = None

    sold_out: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None and self.current_price is not None and not self.sold_out


def _scan_sync(urls: list[str]) -> list[ScanResult]:
    """
    Synchroniczny scan — uruchamia Selenium i skanuje każdy URL.
    Wywoływany w executor żeby nie blokować event loop bota.
    """
    try:
        from scraper.browser import create_browser, accept_cookies
        from scraper.extractor import extract_product_data
        import time
    except ImportError as e:
        log.error("Brak scraperа: %s", e)
        return [ScanResult(url=u, error=f"Brak modułu scraperа: {e}") for u in urls]

    results: list[ScanResult] = []
    driver = None

    try:
        driver = create_browser(headless=False)  # UWAGA: headless=False wymagane dla Nike SKU (Wyświetl szczegóły produkcji)
        # Otwórz od razu pierwszy URL produktu żeby nie tracić czasu na homepage
        if urls:
            driver.get(urls[0])
            time.sleep(2)
            accept_cookies(driver)
            time.sleep(0.5)

        for url in urls:
            log.info("Skanuję: %s", url)
            try:
                data = extract_product_data(driver, url, max_price=None)
                if data is None:
                    results.append(ScanResult(url=url, error="Brak danych — strona nie załadowała?"))
                    continue

                # Sprawdź czy produkt jest wyprzedany (brak accepted_sizes = wszystkie OutOfStock)
                accepted_sizes = data.get("accepted_sizes", None)
                is_sold_out = accepted_sizes is not None and len(accepted_sizes) == 0
                if is_sold_out:
                    log.warning("Artykuł WYPRZEDANY — pomijam: %s", url)
                    results.append(ScanResult(
                        url=url,
                        name=data.get("name"),
                        brand=data.get("brand"),
                        current_price=data.get("current_price"),
                        sold_out=True,
                        error="Artykuł wyprzedany",
                    ))
                    continue

                # Zbierz EANy per rozmiar — dla PZ potrzebujemy EAN dla KAŻDEGO rozmiaru
                # nawet jeśli Zalando oznacza go jako low_stock/niedostępny
                size_to_ean: dict[str, Optional[str]] = {}
                sku_value: Optional[str] = None
                for s in data.get("sizes", []):
                    ean = s.get("ean")
                    if ean:  # każdy rozmiar z EAN — niezależnie od dostępności
                        size_to_ean[s["size"]] = ean
                    if not sku_value and s.get("sku"):  # SKU taki sam dla wszystkich rozmiarów
                        sku_value = s["sku"]

                results.append(ScanResult(
                    url=url,
                    name=data.get("name"),
                    brand=data.get("brand"),
                    sku=sku_value,
                    current_price=data.get("current_price"),
                    original_price=data.get("original_price"),
                    size_to_ean=size_to_ean,
                ))
                time.sleep(2)  # opóźnienie między stronami

            except Exception as e:
                log.error("Błąd przy skanowaniu %s: %s", url, e)
                results.append(ScanResult(url=url, error=str(e)))

    except Exception as e:
        log.error("Błąd inicjalizacji przeglądarki: %s", e)
        for u in urls:
            results.append(ScanResult(url=u, error=f"Błąd przeglądarki: {e}"))
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return results


async def scan_urls(urls: list[str]) -> list[ScanResult]:
    """
    Async wrapper — uruchamia scan w thread executor żeby nie blokować Discord.
    """
    loop = asyncio.get_event_loop()
    unique_urls = list(dict.fromkeys(urls))  # deduplicate zachowując kolejność
    results = await loop.run_in_executor(None, _scan_sync, unique_urls)
    # Mapuj z powrotem na oryginalną kolejność (ze zduplikowanymi URLami)
    result_map = {r.url: r for r in results}
    return [result_map.get(u, ScanResult(url=u, error="Nieznany błąd")) for u in urls]
