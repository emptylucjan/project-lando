"""
Verbose test - każdy krok z pełnym raportem.
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

    size_str = '44'

    # Krok 1: Sprawdź trigger
    has_trigger = driver.execute_script(
        "return !!document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]')"
    )
    print(f"Trigger exists: {has_trigger}")

    # Krok 2: Kliknij trigger
    if has_trigger:
        driver.execute_script("document.querySelector('[data-testid=\"pdp-size-picker-trigger\"]').click()")
        time.sleep(0.5)
    
    # Krok 3: Sprawdź listbox
    listbox_exists = driver.execute_script("return !!document.querySelector('[role=\"listbox\"]')")
    print(f"Listbox visible: {listbox_exists}")
    
    if listbox_exists:
        # Pobierz listę rozmiarów
        sizes_in_list = driver.execute_script("""
            var items = document.querySelector('[role="listbox"]').querySelectorAll('[role="listitem"]');
            var sizes = [];
            for (var i = 0; i < items.length; i++) {
                var spans = items[i].querySelectorAll('span');
                for (var j = 0; j < spans.length; j++) {
                    var t = spans[j].textContent.trim();
                    if (t.length > 0 && t.length < 8) { sizes.push(t); break; }
                }
            }
            return sizes;
        """)
        print(f"Sizes in listbox: {sizes_in_list}")

    # Krok 4: Kliknij rozmiar
    result = extractor._select_size_in_dropdown(driver, size_str)
    print(f"_select_size_in_dropdown returned: {result}")
    time.sleep(0.5)
    
    print(f"URL after click: {driver.current_url}")
    
    # Krok 5: EAN extraction
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.6);")
    time.sleep(0.4)
    
    # Check for 'Szczegóły produktu'
    details_section = driver.execute_script("""
        var buttons = document.querySelectorAll('button, button[aria-expanded]');
        var texts = [];
        for (var i = 0; i < buttons.length; i++) {
            var t = buttons[i].innerText.trim();
            if (t.length > 0 && t.length < 50) texts.push(t);
        }
        return texts;
    """)
    print(f"Buttons on page (short text): {details_section[:10]}")
    
    ean_result = extractor._extract_ean_for_selected_size(driver, section_expanded=False)
    print(f"EAN result: {ean_result}")

finally:
    driver.quit()
