"""
Sprawdź kompletny ProductGroup JSON-LD z Zalando.
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
            print(f"\n=== LD+JSON #{i} - dump ===")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:6000])
        except Exception as e:
            print(f"Error parsing #{i}: {e}")
            print(raw[:200])

finally:
    driver.quit()
