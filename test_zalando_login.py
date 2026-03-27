"""
Test logowania na Zalando przez stealth Selenium.
Używa tej samej przeglądarki co scraper (anti-bot).

Użycie:
  python test_zalando_login.py eleatowskiedomeny+fiz10@gmail.com
"""

import sys
import time
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.browser import create_browser, accept_cookies

EMAIL    = sys.argv[1] if len(sys.argv) > 1 else "eleatowskiedomeny+fiz10@gmail.com"
PASSWORD = "Luki6720"
LOGIN_URL = "https://accounts.zalando.com/authenticate?client_id=fashion-store-web&redirect_uri=https%3A%2F%2Fwww.zalando.pl%2Fsso%2Fcallback&response_type=code&scope=openid&ui_locales=pl-PL&sales_channel=ca9d5f22-2a1b-4799-b3b7-83f47c191489&client_country=PL"


def try_login(driver, email: str, password: str) -> bool:
    logger.info("Otwieranie strony Zalando...")
    driver.get("https://www.zalando.pl")
    time.sleep(3)
    accept_cookies(driver)
    time.sleep(2)

    logger.info("Przechodzenie na stronę logowania...")
    driver.get(LOGIN_URL)
    time.sleep(3)

    # Wpisz email
    try:
        wait = WebDriverWait(driver, 15)
        email_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id*='email']"))
        )
        email_field.clear()
        email_field.send_keys(email)
        logger.info("Wpisano email: %s", email)
        time.sleep(1)
    except Exception as e:
        logger.error("Nie znaleziono pola email: %s", e)
        driver.save_screenshot("debug_login_email.png")
        return False

    # Kliknij Kontynuuj
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(., 'Kontynuuj') or contains(., 'Continue') or contains(., 'Weiter')]")
        btn.click()
        logger.info("Kliknięto Kontynuuj")
        time.sleep(3)
    except Exception as e:
        logger.error("Nie znaleziono przycisku Kontynuuj: %s", e)
        driver.save_screenshot("debug_login_btn.png")
        return False

    # Wpisz hasło — czekaj aż pole jest interaktywne, wpisz send_keys
    try:
        wait = WebDriverWait(driver, 10)
        pwd_field = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
        )
        # Scroll do pola i kliknij przez JS
        driver.execute_script("arguments[0].scrollIntoView(true);", pwd_field)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", pwd_field)
        time.sleep(1)
        # Wpisz znak po znaku żeby zareagował React
        import random as _rnd
        for ch in password:
            pwd_field.send_keys(ch)
            time.sleep(_rnd.uniform(0.05, 0.15))
        logger.info("Wpisano hasło (send_keys)")
        time.sleep(1)
    except Exception as e:
        logger.error("Nie znaleziono pola hasła: %s", e)
        driver.save_screenshot("debug_login_pwd.png")
        return False

    # Kliknij "Zaloguj się"
    try:
        login_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Zaloguj się') or contains(., 'Log in') or contains(., 'Anmelden')]"))
        )
        driver.execute_script("arguments[0].click();", login_btn)
        logger.info("Kliknięto Zaloguj się")
        time.sleep(5)
    except Exception as e:
        logger.error("Nie znaleziono przycisku Zaloguj: %s", e)
        driver.save_screenshot("debug_login_submit.png")
        return False



    # Sprawdź czy zalogowany
    current_url = driver.current_url
    logger.info("URL po logowaniu: %s", current_url)

    if "myaccount" in current_url or "zalando.pl" in current_url and "authenticate" not in current_url:
        logger.info("✅ Zalogowano pomyślnie!")
        driver.save_screenshot("debug_login_success.png")
        return True
    else:
        logger.warning("⚠️ Nie wiadomo czy zalogowany — sprawdź screenshot")
        driver.save_screenshot("debug_login_result.png")
        return False


if __name__ == "__main__":
    logger.info("Email: %s", EMAIL)
    driver = create_browser(headless=False)  # headless=False żeby zobaczyć co się dzieje
    try:
        result = try_login(driver, EMAIL, PASSWORD)
        if result:
            logger.info("✅ Login SUCCESS")
            logger.info("Czekam 10s żebyś mógł zobaczyć stronę...")
            time.sleep(10)
        else:
            logger.error("❌ Login FAILED")
            time.sleep(5)
    finally:
        driver.quit()
