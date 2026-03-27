"""
Sprawdź kompletną zawartość JSON-LD strony Zalando.
"""
import sys, time, json, re
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from scraper import browser

driver = browser.create_browser(headless=True)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'

try:
    driver.get(url)
    time.sleep(3)

    ld_raw = driver.execute_script("""
        var scripts = document.querySelectorAll('script[type="application/ld+json"]');
        var results = [];
        for (var s of scripts) { results.push(s.textContent); }
        return results;
    """)
    
    for i, raw in enumerate(ld_raw):
        try:
            data = json.loads(raw)
            print(f"\n=== LD+JSON #{i} ===")
            if isinstance(data, list):
                for item in data:
                    d_str = json.dumps(item, ensure_ascii=False)
                    if 'gtin' in d_str.lower() or 'ean' in d_str.lower() or 'offers' in d_str.lower():
                        print("Contains EAN/GTIN/offers!")
                        print(d_str[:3000])
            elif isinstance(data, dict):
                d_str = json.dumps(data, ensure_ascii=False)
                if 'gtin' in d_str.lower() or 'ean' in d_str.lower() or 'offers' in d_str.lower():
                    print("Contains EAN/GTIN/offers!")
                    print(d_str[:3000])
                else:
                    print("Keys:", list(data.keys()))
        except Exception as e:
            print(f"Error parsing #{i}: {e}")
    
    # Też sprawdź window.__INITIAL_STATE__
    print("\n=== Sprawdzam window.__INITIAL_STATE__ ===")
    state = driver.execute_script("""
        if (window.__INITIAL_STATE__) {
            var s = JSON.stringify(window.__INITIAL_STATE__);
            if (s.includes('gtin') || s.includes('EAN') || s.includes('ean')) return s.substring(0, 3000);
            return 'NO_EAN in state, keys: ' + Object.keys(window.__INITIAL_STATE__).join(', ');
        }
        return 'no __INITIAL_STATE__';
    """)
    print(state[:500])
    
    # Sprawdź Apollo cache
    print("\n=== Sprawdzam Apollo/GraphQL cache ===")
    apollo = driver.execute_script("""
        if (window.__APOLLO_STATE__) {
            var s = JSON.stringify(window.__APOLLO_STATE__);
            if (s.includes('gtin') || s.includes('EAN') || s.includes('ean')) return 'HAS EAN: ' + s.substring(0, 2000);
            return 'no EAN in Apollo, size: ' + s.length;
        }
        return 'no Apollo';
    """)
    print(apollo[:500])

finally:
    driver.quit()
