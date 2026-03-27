"""
Sprawdź dokładnie co zwraca _extract_eans_from_ldjson.
"""
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
    print(f"Result count: {len(result)}")
    for size, data in list(result.items())[:5]:
        print(f"  Size: '{size}' -> {data}")
    
    if not result:
        # Debug manually
        import json, re
        scripts = driver.execute_script("""
            var scripts = document.querySelectorAll('script[type="application/ld+json"]');
            var results = [];
            for (var s of scripts) { results.push(s.textContent); }
            return results;
        """)
        print(f"\nNumber of LD+JSON scripts: {len(scripts)}")
        for i, raw in enumerate(scripts):
            try:
                data = json.loads(raw)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    print(f"Script {i}: @type={item.get('@type')}, hasVariant count={len(item.get('hasVariant', []))}")
                    variants = item.get('hasVariant', [])
                    if variants:
                        v = variants[0]
                        print(f"  First variant keys: {list(v.keys())}")
                        print(f"  First variant gtin: {v.get('gtin')}")
                        print(f"  First variant url: {v.get('url', '')[:100]}")
                        print(f"  First variant sku: {v.get('sku')}")
                        offers = v.get('offers', {})
                        print(f"  First variant offers: {str(offers)[:200]}")
                        
                        # Check url
                        url_val = v.get('url', '')
                        m = re.search(r'[?&]size=([^&]+)', url_val)
                        print(f"  Size from URL regex: {m.group(1) if m else 'NOT FOUND'}")
            except Exception as e:
                print(f"Script {i} error: {e}")
                print(f"  Raw first 200: {raw[:200]}")

finally:
    driver.quit()
