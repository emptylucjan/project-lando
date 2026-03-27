"""
Diagnoza: co mówi JSON-LD o dostępności rozmiarów + co jest widoczne po kliknięciu dla SKU.
"""
import sys, time, json, re
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from scraper import browser

driver = browser.create_browser(headless=False)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'
try:
    driver.get(url)
    time.sleep(3)
    browser.accept_cookies(driver)
    time.sleep(1)

    # Sprawdź availability w JSON-LD
    scripts = driver.execute_script("""
        var scripts = document.querySelectorAll('script[type="application/ld+json"]');
        var results = [];
        for (var s of scripts) { results.push(s.textContent); }
        return results;
    """)
    
    print("=== AVAILABILITY Z JSON-LD ===")
    for raw in scripts:
        try:
            data = json.loads(raw)
            items = data if isinstance(data, list) else [data]
            for item in items:
                variants = item.get('hasVariant', [])
                if not variants and item.get('@type') == 'Product':
                    variants = [item]
                for v in variants:
                    sku = v.get('sku', '')
                    offers = v.get('offers', {})
                    if isinstance(offers, list) and offers:
                        offers = offers[0]
                    url_val = v.get('url', '') or offers.get('url', '')
                    availability = offers.get('availability', '')
                    gtin = v.get('gtin') or offers.get('gtin', '')
                    m = re.search(r'[?&]size=([^&]+)', url_val)
                    size = m.group(1).replace('%2C', ',').replace(',', '.') if m else '?'
                    print(f"  Size {size}: availability={availability.split('/')[-1]}, gtin={gtin}")
        except Exception as e:
            pass

    # Po kliknięciu rozmiaru - skąd wziąć SKU Nike
    print("\n=== SKU PO KLIKNIĘCIU ===")
    # Kliknij trigger i wybierz pierwszy dostępny rozmiar z InStock
    driver.execute_script("document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]').click()")
    time.sleep(0.4)
    
    # Sprawdź jakie rozmiary są dostępne (pdp-stockAvailable vs pdp-stockNotAvailable)
    available_items = driver.execute_script("""
        var listbox = document.querySelector('[role="listbox"]');
        if (!listbox) return [];
        var items = listbox.querySelectorAll('[role="listitem"]');
        var result = [];
        for (var i of items) {
            var inp = i.querySelector('input');
            var spans = i.querySelectorAll('span');
            var size = '';
            for (var s of spans) {
                var t = s.textContent.trim();
                if (t.length > 0 && t.length < 6) { size = t; break; }
            }
            var disabled = inp ? inp.disabled : true;
            var testid = i.querySelector('[data-testid]') ? i.querySelector('[data-testid]').getAttribute('data-testid') : 'none';
            result.push({size: size, disabled: disabled, testid: testid});
        }
        return result;
    """)
    print("Listbox items:")
    for item in available_items[:8]:
        print(f"  size={item.get('size')} disabled={item.get('disabled')} testid={item.get('testid')}")

    # Zamknij dropdown
    driver.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));")
    time.sleep(0.2)
    
finally:
    input("Naciśnij Enter...")
    driver.quit()
