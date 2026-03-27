"""
Uproszczony test - tylko sprawdź czy można otworzyć listbox i znaleźć rozmiary.
"""
import sys, time
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from selenium import webdriver
import json

options = webdriver.ChromeOptions()
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'

try:
    driver.get(url)
    time.sleep(3)
    
    # Accept cookies
    try:
        accept = driver.find_element("css selector", "button[data-testid='uc-accept-all-button']")
        accept.click()
        time.sleep(1)
    except:
        pass
    
    print("URL po załadowaniu:", driver.current_url)
    
    # Otwórz dropdown
    trigger = driver.execute_script("return !!document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]')")
    print("Trigger istnieje:", trigger)
    
    if trigger:
        driver.execute_script("document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]').click()")
        time.sleep(0.5)
        
        listbox = driver.execute_script("return !!document.querySelector('[role=\"listbox\"]')")
        print("Listbox po kliknięciu:", listbox)
        
        if listbox:
            items_count = driver.execute_script("return document.querySelector('[role=\"listbox\"]').querySelectorAll('[role=\"listitem\"]').length")
            print("Liczba itemów:", items_count)
            
            sizes_found = driver.execute_script("""
                var items = document.querySelector('[role="listbox"]').querySelectorAll('[role="listitem"]');
                var sizes = [];
                for (var i = 0; i < Math.min(items.length, 10); i++) {
                    var spans = items[i].querySelectorAll('span');
                    for (var j = 0; j < spans.length; j++) {
                        var t = spans[j].textContent.trim();
                        if (t.length > 0 && t.length < 6) { sizes.push(t); break; }
                    }
                }
                return sizes;
            """)
            print("Znalezione rozmiary:", sizes_found)
            
            # Kliknij rozmiar 44
            result = driver.execute_script("""
                var items = document.querySelector('[role="listbox"]').querySelectorAll('[role="listitem"]');
                for (var i = 0; i < items.length; i++) {
                    var spans = items[i].querySelectorAll('span');
                    for (var j = 0; j < spans.length; j++) {
                        if (spans[j].textContent.trim() === '44') {
                            var label = items[i].querySelector('label');
                            if (label) { label.click(); return 'clicked label'; }
                            return 'no label found in item ' + i;
                        }
                    }
                }
                return 'size 44 not found';
            """)
            print("Kliknięcie 44:", result)
            time.sleep(0.5)
            print("URL po kliknięciu:", driver.current_url)
            
            # Poczekaj i sprawdź EAN
            driver.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', bubbles: true}));")
            time.sleep(0.3)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
            time.sleep(0.5)
            
            # Kliknij wyswietl szczegoly
            wyswietl = driver.execute_script("""
                var elements = document.querySelectorAll('button, a, span');
                for (var i = 0; i < elements.length; i++) {
                    var t = elements[i].innerText.trim().toLowerCase();
                    if (t.includes('wyświetl') && t.includes('produkcji')) {
                        elements[i].click(); return 'clicked';
                    }
                }
                return 'not found';
            """)
            print("Wyswietl:", wyswietl)
            time.sleep(1)
            
            ean = driver.execute_script("""
                var text = document.body.innerText;
                var m = text.match(/EAN\\/GTIN[:\\s]*([0-9]+)/);
                return m ? m[1] : 'not found';
            """)
            print("EAN:", ean)

finally:
    input("Naciśnij Enter żeby zamknąć...")
    driver.quit()
