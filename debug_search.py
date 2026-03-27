"""
Debug: Open Zalando search and save page HTML to inspect structure.
"""
import os, sys, time, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
from scraper.browser import create_browser, accept_cookies

driver = create_browser(headless=False)
try:
    driver.get("https://www.zalando.pl")
    time.sleep(2)
    accept_cookies(driver)
    time.sleep(2)

    # Try the search URL
    url = "https://www.zalando.pl/search/?q=shox"
    logging.info("Going to: %s", url)
    driver.get(url)
    time.sleep(5)

    # Scroll a bit
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1)

    # Save current URL (maybe redirected)
    logging.info("Current URL: %s", driver.current_url)

    # Count product-like links
    count = driver.execute_script("""
        var links = document.querySelectorAll('a[href]');
        var product_links = [];
        for(var i=0;i<links.length;i++){
            var h = links[i].href;
            if(h && h.includes('zalando.pl') && h.match(/\\-[a-z0-9]{5,}\\-[a-z0-9]+\\.html/)){
                product_links.push(h);
            }
        }
        return product_links.length + ' | first: ' + (product_links[0]||'none');
    """)
    logging.info("Product links found: %s", count)

    # Save HTML
    html_path = os.path.join(PROJECT_ROOT, "debug_search.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info("HTML saved to %s (%d bytes)", html_path, os.path.getsize(html_path))

    input("Press ENTER to close browser...")
finally:
    driver.quit()
