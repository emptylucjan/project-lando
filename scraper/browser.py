"""
Browser setup module — creates a Selenium Chrome instance with anti-detection measures.
Uses webdriver-manager for automatic ChromeDriver version matching.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random
import logging

logger = logging.getLogger(__name__)


def create_browser(headless: bool = False) -> webdriver.Chrome:
    """Create a Chrome browser instance with stealth settings."""
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # Anti-detection flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=pl-PL")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    )

    # Auto-download matching ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Remove webdriver flag from navigator
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                // Overwrite the 'plugins' property to use a custom getter
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                // Overwrite the 'languages' property
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['pl-PL', 'pl', 'en-US', 'en'],
                });
            """
        },
    )

    driver.set_page_load_timeout(30)
    logger.info("Przeglądarka Chrome uruchomiona (headless=%s)", headless)
    return driver


def accept_cookies(driver: webdriver.Chrome) -> None:
    """Try to accept the cookie consent popup on Zalando."""
    try:
        wait = WebDriverWait(driver, 10)
        # Zalando cookie consent — try multiple possible button texts
        cookie_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//button[contains(., 'Akceptuj wszystko') "
                 "or contains(., 'Rozumiem') or contains(., 'akceptuję') "
                 "or contains(., 'OK') or contains(., 'Zgadzam') "
                 "or contains(., 'przyjmuję') or contains(., 'Zaakceptuj') "
                 "or contains(., 'Accept') or contains(., 'agree')]")
            )
        )
        cookie_btn.click()
        logger.info("Cookie popup zaakceptowany")
        time.sleep(random.uniform(1, 2))
    except Exception:
        logger.debug("Brak cookie popup lub nie udało się go zamknąć")


def random_delay(min_sec: float = 3, max_sec: float = 7) -> None:
    """Sleep for a random duration to mimic human behavior."""
    delay = random.uniform(min_sec, max_sec)
    logger.debug("Czekam %.1f sek...", delay)
    time.sleep(delay)
