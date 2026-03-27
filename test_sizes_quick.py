"""Szybki test scrapera na two URL — one size i dzieciece rozmiary."""
import sys, os, json, time
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
from scraper.browser import create_browser, accept_cookies
from scraper.extractor import extract_product

URLS = [
    "https://www.zalando.pl/hugo-marsel-trucker-fish-unisex-czapka-z-daszkiem-white-hu754b00b-a11.html",
    "https://www.zalando.pl/nike-sportswear-unisex-bluza-rozpinana-photon-dustcollege-greypencil-pointsapphire-ni124k02z-c18.html",
]

driver = create_browser(headless=True)
try:
    driver.get("https://www.zalando.pl")
    time.sleep(3)
    accept_cookies(driver)
    time.sleep(1)
    for url in URLS:
        print(f"\n{'='*60}\nURL: {url}\n{'='*60}")
        result = extract_product(driver, url)
        if result:
            print(f"Nazwa:   {result.get('name')}")
            print(f"Cena:    {result.get('current_price')}")
            print(f"Rozmiary ({len(result.get('sizes', []))}):")
            for s in result.get('sizes', []):
                avail = "OK" if s.get("available") else "OOS"
                ean = s.get("ean","?")
                print(f"  [{avail}] {s['size']!r:20s}  EAN={ean}")
        else:
            print("BRAK WYNIKÓW / BLAD")
finally:
    driver.quit()
