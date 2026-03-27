"""Debug: step-by-step EAN extraction to see where it fails."""
import sys, os, time, json
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
from scraper.browser import create_browser, accept_cookies

URL = "https://www.zalando.pl/nike-sportswear-shox-ride-2-sneakersy-niskie-blackuniv-red-ni112p05b-q12.html"
driver = create_browser(headless=False)
try:
    driver.get("https://www.zalando.pl")
    time.sleep(3)
    accept_cookies(driver)
    time.sleep(1)
    driver.get(URL)
    time.sleep(5)
    
    # Select size 38.5 first
    driver.execute_script("document.getElementById('picker-trigger').click()")
    time.sleep(1)
    driver.execute_script("""
        var allSpans = document.querySelectorAll('span');
        for (var i = 0; i < allSpans.length; i++) {
            if (allSpans[i].textContent.trim() === '38.5') {
                var rect = allSpans[i].getBoundingClientRect();
                if (rect.width > 0) {
                    var el = allSpans[i];
                    for (var k = 0; k < 3; k++) {
                        if (el.parentElement) el = el.parentElement;
                    }
                    el.click();
                    break;
                }
            }
        }
    """)
    time.sleep(2)
    
    print("=== Step 1: Find 'Szczegóły produktu' ===")
    # Search for all possible elements
    step1 = driver.execute_script("""
        var results = [];
        var allElements = document.querySelectorAll('*');
        for (var i = 0; i < allElements.length; i++) {
            var text = allElements[i].innerText;
            if (text && text.trim().startsWith('Szczegóły produktu') && text.trim().length < 30) {
                results.push({
                    tag: allElements[i].tagName,
                    text: text.trim(),
                    id: allElements[i].id,
                    classes: allElements[i].className.substring(0, 60),
                    clickable: allElements[i].tagName === 'BUTTON' || allElements[i].onclick !== null,
                    role: allElements[i].getAttribute('role'),
                    ariaExpanded: allElements[i].getAttribute('aria-expanded')
                });
            }
        }
        return results;
    """)
    print(f"Found {len(step1)} elements matching 'Szczegóły produktu':")
    for s in step1:
        print(f"  {s['tag']} | text: '{s['text']}' | id: '{s['id']}' | role: {s['role']} | aria-expanded: {s['ariaExpanded']} | classes: {s['classes']}")
    
    print("\n=== Step 2: Scroll to and click 'Szczegóły produktu' ===")
    clicked = driver.execute_script("""
        var allElements = document.querySelectorAll('h2, button, div[role], summary, span');
        for (var i = 0; i < allElements.length; i++) {
            var text = allElements[i].innerText;
            if (text && text.trim() === 'Szczegóły produktu') {
                allElements[i].scrollIntoView({behavior: 'instant', block: 'center'});
                
                // Try clicking the element or its parent
                var target = allElements[i];
                // Try to find the clickable parent (button, summary, etc.)
                for (var k = 0; k < 3; k++) {
                    if (target.tagName === 'BUTTON' || target.tagName === 'SUMMARY' || 
                        target.getAttribute('role') === 'button' || target.onclick) {
                        break;
                    }
                    if (target.parentElement) target = target.parentElement;
                }
                target.click();
                return {clicked: true, tag: target.tagName, role: target.getAttribute('role')};
            }
        }
        return {clicked: false};
    """)
    print(f"Click result: {clicked}")
    time.sleep(1.5)
    
    print("\n=== Step 3: Find 'Wyświetl szczegóły produkcji' ===")
    step3 = driver.execute_script("""
        var results = [];
        var allElements = document.querySelectorAll('*');
        for (var i = 0; i < allElements.length; i++) {
            var text = allElements[i].innerText;
            if (text && (text.toLowerCase().includes('szczegóły produkcji') || 
                         text.toLowerCase().includes('wyświetl szczegóły'))) {
                if (text.trim().length < 50) {
                    results.push({
                        tag: allElements[i].tagName,
                        text: text.trim(),
                        visible: allElements[i].getBoundingClientRect().width > 0,
                        classes: allElements[i].className.substring(0, 60)
                    });
                }
            }
        }
        return results;
    """)
    print(f"Found {len(step3)} elements matching 'szczegóły produkcji':")
    for s in step3:
        print(f"  {s['tag']} | text: '{s['text']}' | visible: {s['visible']}")
    
    if step3:
        print("\n=== Step 4: Click 'Wyświetl szczegóły produkcji' ===")
        clicked2 = driver.execute_script("""
            var allElements = document.querySelectorAll('a, button, span, div');
            for (var i = 0; i < allElements.length; i++) {
                var text = allElements[i].innerText;
                if (text && text.trim().toLowerCase().includes('wyświetl szczegóły produkcji')) {
                    allElements[i].scrollIntoView({behavior: 'instant', block: 'center'});
                    allElements[i].click();
                    return {clicked: true, tag: allElements[i].tagName, text: text.trim()};
                }
            }
            return {clicked: false};
        """)
        print(f"Click result: {clicked2}")
        time.sleep(3)
        
        print("\n=== Step 5: Read EAN/GTIN ===")
        ean = driver.execute_script("""
            var body = document.body.innerText;
            var eanMatch = body.match(/EAN\\/GTIN[:\\s]*([0-9]+)/);
            var skuMatch = body.match(/[Nn]umer\\s+modelu[:\\s]*([A-Za-z0-9\\-]+)/);
            return {
                ean: eanMatch ? eanMatch[1] : null,
                sku: skuMatch ? skuMatch[1] : null
            };
        """)
        print(f"EAN: {ean}")

finally:
    driver.quit()
