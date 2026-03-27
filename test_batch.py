"""Batch test — scrape 5 Nike Dunk products."""
import sys, os, json, time, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from scraper.browser import create_browser, accept_cookies, random_delay
from scraper.extractor import extract_product_data

URLS = [
    "https://www.zalando.pl/nike-sportswear-dunk-low-gtx-sneakersy-niskie-summit-white-off-white-light-smoke-grey-black-ni112p036-a12.html",
    "https://www.zalando.pl/nike-sportswear-dunk-retro-unisex-sneakersy-niskie-whitelight-smoke-greywhite-ni115o07u-a15.html",
    "https://www.zalando.pl/nike-sportswear-dunk-retro-sneakersy-wysokie-whiteblacktotal-orange-ni112o0gy-a15.html",
    "https://www.zalando.pl/nike-sportswear-dunk-retro-sneakersy-niskie-whiteblack-ni112o0gn-a11.html",
    "https://www.zalando.pl/nike-sportswear-dunk-retro-se-sneakersy-niskie-summit-whiteblue-voidpure-platinum-coloured-ni112p05p-a11.html",
]

driver = create_browser(headless=False)
results = []

try:
    driver.get("https://www.zalando.pl")
    time.sleep(3)
    accept_cookies(driver)
    random_delay(2, 3)

    for i, url in enumerate(URLS, 1):
        print(f"\n[{i}/{len(URLS)}] {url.split('/')[-1][:60]}...")
        product = extract_product_data(driver, url)
        if product:
            results.append(product)
            print(f"  => {product['name']} | {product['current_price']} zl | reg: {product.get('original_price', '-')}")
        else:
            print(f"  => BLAD!")
        if i < len(URLS):
            random_delay(3, 5)
finally:
    driver.quit()

# Save results
with open(os.path.join(PROJECT_ROOT, "batch_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"WYNIKI: {len(results)}/{len(URLS)} produktow zescrapowanych")
print(f"{'='*60}")
for r in results:
    disc = f" (-{r['discount_percent']}%)" if r.get('discount_percent') else ""
    reg = f" (reg: {r['original_price']})" if r.get('original_price') else ""
    print(f"  {r['current_price']:>7} zl{reg}{disc} | {r.get('name','?')[:50]}")
