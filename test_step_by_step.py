"""
Krok-po-kroku test klikania rozmiaru z dropdownu i odczytywania EAN.
"""
import sys, time
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from selenium import webdriver

options = webdriver.ChromeOptions()
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'

try:
    driver.get(url)
    time.sleep(3)
    
    # Odrzuć cookies
    driver.execute_script("""
        var btns = document.querySelectorAll('button');
        for (var b of btns) {
            if (b.innerText.includes('Akceptuj wszystko')) { b.click(); break; }
        }
    """)
    time.sleep(1)

    size_str = '44'
    
    print("Krok 1: Otwieramy dropdown...")
    driver.execute_script("""
        var trigger = document.querySelector('[data-testid="pdp-size-picker-trigger"]');
        if (trigger) trigger.click();
    """)
    time.sleep(0.5)
    
    listbox = driver.execute_script("return !!document.querySelector('[role=\"listbox\"]')")
    print(f"  Listbox w DOM: {listbox}")
    
    print(f"Krok 2: Klikamy rozmiar {size_str}...")
    clicked = driver.execute_script(f"""
        var sizeStr = '{size_str}';
        var listbox = document.querySelector('[role="listbox"]');
        if (!listbox) return 'NO LISTBOX';
        var items = listbox.querySelectorAll('[role="listitem"]');
        for (var i = 0; i < items.length; i++) {{
            var spans = items[i].querySelectorAll('span');
            for (var j = 0; j < spans.length; j++) {{
                if (spans[j].textContent.trim() === sizeStr) {{
                    var label = items[i].querySelector('label');
                    if (label) {{ label.click(); return 'clicked label'; }}
                    var inp = items[i].querySelector('input');
                    if (inp) {{ inp.click(); return 'clicked input'; }}
                    spans[j].click();
                    return 'clicked span';
                }}
            }}
        }}
        var allSpans = Array.from(listbox.querySelectorAll('span')).map(s => s.textContent.trim()).filter(t => t.length < 8);
        return 'NOT_FOUND. Sizes in listbox: ' + allSpans.slice(0, 10).join(', ');
    """)
    print(f"  Kliknięcie: {clicked}")
    
    # Escape to close listbox
    driver.execute_script("""
        document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', bubbles: true}));
    """)
    time.sleep(0.3)
    
    print("Krok 3: Zwijamy sekcję szczegółów produktu...")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
    time.sleep(0.3)
    found_details = driver.execute_script("""
        var buttons = document.querySelectorAll('button[aria-expanded], button');
        for (var i = 0; i < buttons.length; i++) {
            var text = buttons[i].innerText.trim();
            if (text === 'Szczegóły produktu') {
                if (buttons[i].getAttribute('aria-expanded') === 'false') buttons[i].click();
                return 'found and expanded';
            }
        }
        return 'not found';
    """)
    print(f"  Szczegóły produktu: {found_details}")
    time.sleep(0.4)
    
    print("Krok 4: Klikamy Wyświetl szczegóły produkcji...")
    for attempt in range(10):
        wyswietl = driver.execute_script("""
            var elements = document.querySelectorAll('button, a, span');
            for (var i = 0; i < elements.length; i++) {
                var t = elements[i].innerText.trim().toLowerCase();
                if (t.includes('wyświetl') && t.includes('produkcji')) {
                    elements[i].click();
                    return true;
                }
            }
            return false;
        """)
        if wyswietl:
            print(f"  Kliknięto w próbie {attempt}")
            break
        time.sleep(0.3)
    else:
        print("  NIE ZNALEZIONO PRZYCISKU!")
    
    print("Krok 5: Szukamy EAN/GTIN...")
    for attempt in range(15):
        time.sleep(0.3)
        result = driver.execute_script("""
            var text = document.body.innerText;
            var eanMatch = text.match(/EAN\\/GTIN[:\\s]*([0-9]+)/);
            var skuMatch = text.match(/[Nn]umer\\s+modelu[:\\s]*([A-Za-z0-9\\-]+)/);
            return {ean: eanMatch ? eanMatch[1] : null, sku: skuMatch ? skuMatch[1] : null};
        """)
        if result.get('ean'):
            print(f"  SUKCES! EAN: {result['ean']}, SKU: {result.get('sku')}")
            break
    else:
        print(f"  BRAK EAN po 15 próbach. Ostatni wynik: {result}")
        # Sprawdź czy jesteśmy nadal na stronie produktu
        current_url = driver.current_url
        print(f"  Obecny URL: {current_url}")

finally:
    driver.quit()
