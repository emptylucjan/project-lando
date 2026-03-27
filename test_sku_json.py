"""
Diagnostic: znajdź Nike model number w JSON strony Air Max 90 BEZ klikania UI.
Sprawdza: window.__NUXT__, window.dataLayer, inne JSON-y na stronie.
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

    print("=== SZUKAM Nike model number w JSON strony ===")
    
    # Szukaj w WSZYSTKICH script tagach
    scripts = driver.execute_script("""
        var tags = document.querySelectorAll('script');
        var result = [];
        for (var s of tags) {
            var t = s.textContent;
            if (t && t.length > 50) result.push(t.substring(0, 5000));
        }
        return result;
    """)
    
    # Szukaj wzorca Nike model number (np. HV4517-100, FD9749-100, etc.)
    nike_pattern = re.compile(r'[A-Z]{2}[0-9]{4}[-][0-9]{3}')
    
    for i, sc in enumerate(scripts):
        matches = nike_pattern.findall(sc)
        if matches:
            print(f"Script {i}: Nike-like SKU znalezione: {set(matches)}")
            # Pokaż kontekst
            for m in set(matches):
                idx = sc.find(m)
                print(f"  Kontekst: ...{sc[max(0,idx-50):idx+100]}...")
    
    # Sprawdź window.__NUXT__ lub podobne
    nuxt = driver.execute_script("return typeof window.__NUXT__ !== 'undefined' ? JSON.stringify(window.__NUXT__).substring(0, 2000) : null")
    if nuxt:
        matches = nike_pattern.findall(nuxt)
        print(f"window.__NUXT__ Nike SKUs: {set(matches)}")
    
    # Sprawdź dataLayer
    dl = driver.execute_script("return typeof window.dataLayer !== 'undefined' ? JSON.stringify(window.dataLayer).substring(0, 3000) : null")
    if dl:
        matches = nike_pattern.findall(dl)
        if matches:
            print(f"dataLayer Nike SKUs: {set(matches)}")
    
    # Sprawdź cały innerText strony (już bez klikania)
    all_text = driver.execute_script("return document.body.innerHTML.substring(0, 50000)")
    matches = nike_pattern.findall(all_text)
    if matches:
        unique = set(matches)
        print(f"W HTML: {unique}")
    
    print("=== KONIEC ===")
    input("Naciśnij Enter...")
finally:
    driver.quit()
