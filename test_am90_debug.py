import sys, json, logging
logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from scraper import extractor, browser

driver = browser.create_browser(headless=False)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'
try:
    data = extractor.extract_product_data(driver, url)
    if data:
        print(f"Name: {data.get('name')}")
        print(f"Accepted sizes: {data.get('accepted_sizes')}")
        sizes = data.get('sizes', [])
        print(f"Total sizes: {len(sizes)}")
        for s in sizes:
            print(f"  {s.get('size')} available={s.get('available')} accepted={s.get('accepted')} ean={s.get('ean')} sku={s.get('sku')}")
    else:
        print("No data returned!")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    driver.quit()
