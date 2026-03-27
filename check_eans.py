import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(".")), "scraper"))
import logging
logging.basicConfig(level=logging.WARNING)

from scraper.browser import create_browser
from scraper.extractor import extract_product_data

url = "https://www.zalando.pl/jordan-air-jordan-1-mid-se-sneakersy-wysokie-blackolive-greywild-mango-joc12p00y-q11.html"
driver = create_browser(headless=True)
try:
    import time
    driver.get(url)
    time.sleep(3)
    try:
        btn = driver.find_element("xpath", "//button[contains(.,'Zaakceptuj')]")
        btn.click(); time.sleep(1)
    except: pass
    data = extract_product_data(driver, url)
finally:
    driver.quit()

if data:
    print(f"BRAND: {data.get('brand')}")
    print(f"NAME: {data.get('name')}")
    print(f"PRICE: {data.get('current_price')} PLN")
    print(f"SKU from sizes: ", end="")
    for s in data.get("sizes", []):
        if s.get("ean"):
            print(f"\n  Rozmiar {s['size']}: EAN={s['ean']} SKU={s.get('sku','?')}")
