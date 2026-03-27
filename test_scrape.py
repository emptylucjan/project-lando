"""
Quick test — scrape a single Zalando product URL (non-interactive).
Usage: python test_scrape.py
"""

import sys
import os
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from scraper.browser import create_browser
from scraper.extractor import extract_product_data, download_product_image

TEST_URL = "https://www.zalando.pl/nike-sportswear-air-max-90-sneakersy-niskie-whiteuniversity-red-ni112o0p5-a28.html"


def main():
    print("=" * 60)
    print("TEST: Scrapowanie pojedynczego produktu z Zalando")
    print(f"URL: {TEST_URL}")
    print("=" * 60)

    driver = create_browser(headless=False)

    try:
        # Scrape the product directly
        product = extract_product_data(driver, TEST_URL)

        if product:
            print("\n" + "=" * 60)
            print("SUKCES! Dane produktu:")
            print("=" * 60)
            result = json.dumps(product, indent=2, ensure_ascii=False)
            print(result)

            # Save result for inspection
            with open(os.path.join(PROJECT_ROOT, "test_result.json"), "w", encoding="utf-8") as f:
                f.write(result)
            print(f"\nZapisano wynik do test_result.json")

            # Download packshot image (first gallery image = left-facing on gray bg)
            gallery = product.get("gallery_images", [])
            img_url = gallery[0] if gallery else product.get("image_url")
            if img_url:
                sku = None
                for s in product.get("sizes", []):
                    if s.get("sku"):
                        sku = s["sku"]
                        break
                fname = sku or "product"
                img_path = os.path.join(PROJECT_ROOT, "images", f"{fname}.jpg")
                result_imgs = download_product_image(img_url, img_path)
                if result_imgs:
                    print(f"JPG: {result_imgs['jpg']}")
                    print(f"PNG: {result_imgs['png']}")
                else:
                    print("Nie udało się pobrać zdjęcia")
        else:
            print("\nNie udalo sie wyciagnac danych!")
            debug_path = os.path.join(PROJECT_ROOT, "debug_page.html")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print(f"Zapisano HTML strony do: {debug_path}")

    finally:
        driver.quit()
        print("Przegladarka zamknieta.")


if __name__ == "__main__":
    main()
