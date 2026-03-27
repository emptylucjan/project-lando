from selenium import webdriver
import time

options = webdriver.ChromeOptions()
options.add_argument('--window-size=1920,1080')
driver = webdriver.Chrome(options=options)
driver.get('https://www.zalando.pl/nike-sportswear-air-max-90-prm-reflect-sneakersy-niskie-whitemetallic-silver-coloured-ni112p039-a11.html')
time.sleep(3)

# Accept cookies if present
driver.execute_script("""
    var btns = document.querySelectorAll('button');
    for (var b of btns) {
        if (b.innerText.includes('Akceptuj wszystko')) { b.click(); break; }
    }
""")
time.sleep(1)

# Click "Wybierz rozmiar" trigger
driver.execute_script("""
    var trigger = document.querySelector('[data-testid="pdp-size-picker-trigger"]');
    if (trigger) trigger.click();
""")
time.sleep(0.5)

# Dump the listbox/options HTML
html = driver.execute_script("""
    // Look for listbox role
    var listbox = document.querySelector('[role="listbox"]');
    if (listbox) return listbox.outerHTML.substring(0, 3000);
    
    // Look for items in the dropdown overlay
    var items = document.querySelectorAll('[role="option"]');
    if (items.length > 0) return Array.from(items).map(i => i.outerHTML).join('\\n').substring(0, 3000);
    
    // Look for any new elements after click
    return 'No listbox found. Body snapshot: ' + document.body.innerHTML.substring(0, 2000);
""")

with open('dropdown_options.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Done, check dropdown_options.html')
driver.quit()
