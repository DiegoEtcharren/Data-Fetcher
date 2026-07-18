import subprocess
import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Load credentials
load_dotenv()
AGENDA_USER = os.getenv("AGENDA_USER")
AGENDA_PASS = os.getenv("AGENDA_PASS")

def test_login_stability():
    print("\n--- Testing Login Flow with Stability Flags ---")
    if not AGENDA_USER or not AGENDA_PASS:
        print("Error: AGENDA_USER or AGENDA_PASS is not set in .env. Skipping login test.")
        return False
        
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-webgl")
    chrome_options.add_argument("--disable-features=site-per-process")
    chrome_options.add_argument("--js-flags=--max-old-space-size=512")
    
    # Standard desktop User-Agent to avoid bot-protection script crashes
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    chrome_options.binary_location = "/usr/bin/chromium"
    chrome_service = Service(executable_path="/usr/bin/chromedriver")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        print("1. Driver initialized with stability flags.")
        
        driver.get("https://app.agendapro.com/sign_in")
        print("2. Loaded Sign-In page. Waiting for email field to render...")
        
        # Log page title and current URL to verify it's still alive
        print(f"Current Title: {driver.title} | Current URL: {driver.current_url}")
        
        wait = WebDriverWait(driver, 30)
        
        # Fill Email
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_field.send_keys(AGENDA_USER)
        print("3. Filled email.")
        
        # Fill Password
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.send_keys(AGENDA_PASS)
        print("4. Filled password.")
        
        # Click Login
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit-button")))
        login_button.click()
        print("5. Clicked login button. Waiting for redirect...")
        
        # Wait for redirect
        WebDriverWait(driver, 60).until(lambda d: "/bookings" in d.current_url)
        print(f"6. Redirected successfully! Current URL: {driver.current_url}")
        
        cookies = driver.get_cookies()
        print(f"Success! Obtained {len(cookies)} cookies.")
        return True
        
    except Exception as e:
        print(f"❌ Stability test FAILED: {e}")
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    test_login_stability()
