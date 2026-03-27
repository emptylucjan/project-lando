"""
Sprawdź co pojawia się po kliknięciu rozmiaru - skąd brać Nike SKU.
"""
import sys, time
sys.path.append('C:\\Users\\lukko\\Desktop\\projekt zalando')
from scraper import extractor, browser

driver = browser.create_browser(headless=False)
url = 'https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html'
try:
    driver.get(url)
    time.sleep(3)
    browser.accept_cookies(driver)
    time.sleep(1)

    # Kliknij rozmiar 43 (dostępny)
    clicked = extractor._select_size_in_dropdown(driver, '43')
    print(f"Kliknięto 43: {clicked}")
    time.sleep(0.5)

    # Sprawdź szczegóły produktu
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
    time.sleep(0.5)

    # Otwórz sekcję szczegółów
    opened = driver.execute_script("""
        var buttons = document.querySelectorAll('button');
        for (var b of buttons) {
            if (b.innerText.trim() === 'Szczegóły produktu') {
                if (b.getAttribute('aria-expanded') === 'false') b.click();
                return 'opened: ' + b.innerText;
            }
        }
        return 'not found';
    """)
    print(f"Szczegóły produktu: {opened}")
    time.sleep(0.5)

    # Sprawdź co jest w szczegółach
    details_text = driver.execute_script("""
        var sections = document.querySelectorAll('[aria-label], [data-testid*="detail"], [class*="detail"]');
        var texts = [];
        for (var s of sections) {
            var t = s.innerText;
            if (t && t.includes('Numer modelu') || t && t.includes('Wyświetl szczegóły') || t && t.includes('model')) {
                texts.push(t.substring(0, 200));
            }
        }
        return texts.join('\\n---\\n');
    """)
    print(f"Details text: {details_text[:500]}")
    
    # Szukaj bezpośrednio numeru modelu
    numer_modelu = driver.execute_script("""
        var allText = document.body.innerText;
        var patterns = [
            /Numer modelu[:\\s]+([\\w-]+)/i,
            /Style[:\\s]+([\\w-]+)/i,
            /ARA:[\\s]+([\\w-]+)/i
        ];
        for (var p of patterns) {
            var m = allText.match(p);
            if (m) return m[1];
        }
        return 'not found yet';
    """)
    print(f"Numer modelu: {numer_modelu}")

    # Kliknij "Wyświetl szczegóły produkcji"
    wyswietl = driver.execute_script("""
        var els = document.querySelectorAll('button, span, a');
        for (var e of els) {
            if (e.innerText && e.innerText.trim().toLowerCase().includes('wyświetl') && 
                e.innerText.trim().toLowerCase().includes('produkcji')) {
                e.click();
                return 'clicked: ' + e.innerText;
            }
        }
        return 'not found';
    """)
    print(f"Wyświetl: {wyswietl}")
    time.sleep(1.5)
    
    numer_modelu2 = driver.execute_script("""
        var allText = document.body.innerText;
        var patterns = [
            /Numer modelu[:\\s]+([\\w-]+)/i,
            /Style[:\\s]+([\\w-]+)/i,
        ];
        for (var p of patterns) {
            var m = allText.match(p);
            if (m) return m[1];
        }
        return 'still not found';
    """)
    print(f"Numer modelu po wyswietl: {numer_modelu2}")

    input("Naciśnij Enter...")
finally:
    driver.quit()
