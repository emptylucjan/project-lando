import sys
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from scraper import extractor, browser
import time

driver = browser.create_browser(headless=True)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'
try:
    driver.get(url)
    time.sleep(3)
    result = extractor._extract_eans_from_ldjson(driver)
    print(f"Total sizes in JSON-LD: {len(result)}")
    for size in sorted(result.keys(), key=lambda x: float(x.replace(',','.'))):
        data = result[size]
        print(f"  {size} -> EAN={data.get('ean')} SKU={data.get('sku')}")
finally:
    driver.quit()
