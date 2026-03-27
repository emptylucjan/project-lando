"""
Sprawdź czy EAN jest dostępny w danych JSON strony - bez klikania UI.
"""
import sys, time, json, re
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from scraper import browser

driver = browser.create_browser(headless=True)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'

try:
    driver.get(url)
    time.sleep(3)

    # 1. Sprawdź window.__INITIAL_STATE__ lub podobne
    window_keys = driver.execute_script("""
        var keys = [];
        for (var k in window) {
            if (k.includes('STATE') || k.includes('DATA') || k.includes('PRODUCT') || k.includes('CONFIG')) keys.push(k);
        }
        return keys;
    """)
    print("Window keys:", window_keys)

    # 2. Sprawdź JSON-LD scripts
    ld_data = driver.execute_script("""
        var scripts = document.querySelectorAll('script[type="application/ld+json"]');
        var results = [];
        for (var s of scripts) {
            try { results.push(JSON.parse(s.textContent)); } catch(e) {}
        }
        return JSON.stringify(results);
    """)
    try:
        ld = json.loads(ld_data)
        for item in ld:
            if isinstance(item, dict):
                print("LD+JSON keys:", list(item.keys())[:10])
                # Szukaj EAN, GTIN, offers
                if 'offers' in item:
                    print("Offers:", str(item['offers'])[:500])
                if 'gtin' in str(item).lower() or 'ean' in str(item).lower():
                    print("EAN/GTIN in LD+JSON!")
                    s = str(item)
                    # Find EAN patterns
                    matches = re.findall(r'"(?:gtin|ean|gtin13|gtin8)[^"]*":\s*"([^"]+)"', s, re.IGNORECASE)
                    print("Matches:", matches[:10])
    except Exception as e:
        print("LD JSON error:", e)

    # 3. Sprawdź script tags z danymi produktu
    script_data = driver.execute_script("""
        var scripts = document.querySelectorAll('script:not([src]):not([type="application/ld+json"])');
        for (var s of scripts) {
            var t = s.textContent;
            if (t.includes('EAN') || t.includes('ean') || t.includes('gtin')) {
                return t.substring(0, 2000);
            }
        }
        return 'not found';
    """)
    if script_data != 'not found':
        print("Script with EAN found!")
        print(script_data[:500])
    else:
        print("No script with EAN")

    # 4. Sprawdź czy strona ma API calls - network log
    logs = driver.get_log('performance')
    ean_urls = [l['message'] for l in logs if 'ean' in l['message'].lower() or 'gtin' in l['message'].lower()]
    print(f"API calls with EAN: {len(ean_urls)}")
    for u in ean_urls[:3]:
        print(" -", u[:200])

finally:
    driver.quit()
