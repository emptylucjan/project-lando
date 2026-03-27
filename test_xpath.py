from selenium import webdriver
import time

options = webdriver.ChromeOptions()
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)
driver.get('https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html')
time.sleep(3)

sizeStr = '44'

driver.execute_script('''
    window.scrollTo(0, document.body.scrollHeight * 0.6);
    var buttons = document.querySelectorAll('button');
    for (var i = 0; i < buttons.length; i++) {
        var t = buttons[i].innerText.trim().toLowerCase();
        if (t.includes('wybierz rozmiar') || t.includes('choose your size')) {
            if (buttons[i].getAttribute('aria-expanded') === 'false') buttons[i].click();
        }
    }
''')
time.sleep(1)

html = driver.execute_script(f'''
    var xpath = "//*[normalize-space(text())='{sizeStr}']";
    var iterator = document.evaluate(xpath, document, null, XPathResult.UNORDERED_NODE_ITERATOR_TYPE, null);
    var node = iterator.iterateNext();
    if (node) {{
        var clickable = node;
        while(clickable && clickable.tagName !== 'BUTTON' && clickable.tagName !== 'LABEL' && clickable.tagName !== 'DIV' && clickable.tagName !== 'A' && clickable.tagName !== 'LI') {{
            clickable = clickable.parentElement;
        }}
        if (clickable) {{
            clickable.scrollIntoView({{behavior: 'instant', block: 'center'}});
            clickable.click();
            return 'Clicked: ' + clickable.outerHTML;
        }}
    }}
    return 'Not found';
''')
print('Click Size Result:', html)

time.sleep(1)

details = driver.execute_script('''
    var buttons = document.querySelectorAll('button, a, span');
    for (var i = 0; i < buttons.length; i++) {
        var text = buttons[i].innerText.trim().toLowerCase();
        if (text.includes('wyświetl') && text.includes('produkcji')) {
            buttons[i].click();
            return true;
        }
    }
    return false;
''')
print('Click Wyświetl:', details)

time.sleep(1)

res = driver.execute_script('''
    var text = document.body.innerText;
    var eanMatch = text.match(/EAN\\/GTIN[:\\s]*([0-9]+)/);
    var skuMatch = text.match(/[Nn]umer\\s+modelu[:\\s]*([A-Za-z0-9\\-]+)/);
    return {ean: eanMatch ? eanMatch[1] : null, sku: skuMatch ? skuMatch[1] : null};
''')
print('Extracted:', res)

driver.quit()
