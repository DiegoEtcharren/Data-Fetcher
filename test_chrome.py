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

def test_login_variation(disable_shm_usage=False, site_per_process=True):
    print(f"\n--- Testing Login Flow (disable_shm_usage={disable_shm_usage}, site_per_process={site_per_process}) ---")
    if not AGENDA_USER or not AGENDA_PASS:
        print("Error: AGENDA_USER or AGENDA_PASS is not set in .env. Skipping login test.")
        return False
        
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    
    if disable_shm_usage:
        chrome_options.add_argument("--disable-dev-shm-usage")
        
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    
    if site_per_process:
        chrome_options.add_argument("--disable-features=site-per-process")
        
    chrome_options.binary_location = "/usr/bin/chromium"
    chrome_service = Service(executable_path="/usr/bin/chromedriver")
    
    driver = None
    try:
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        print("1. Driver initialized.")
        
        driver.get("https://app.agendapro.com/sign_in")
        print("2. Loaded Sign-In page.")
        
        wait = WebDriverWait(driver, 20)
        
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
        print(f"❌ Test FAILED: {e}")
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    # Test variation 1: Use the 2GB shared memory (/dev/shm) directly (disable_shm_usage=False)
    success = test_login_variation(disable_shm_usage=False, site_per_process=True)
    
    if not success:
        # Test variation 2: disable_shm_usage=True but site_per_process=True
        print("\nRetrying with disable_shm_usage=True...")
        success = test_login_variation(disable_shm_usage=True, site_per_process=True)
        
    if not success:
        # Test variation 3: disable_shm_usage=False, site_per_process=False
        print("\nRetrying with disable_shm_usage=False, site_per_process=False...")
        success = test_login_variation(disable_shm_usage=False, site_per_process=False)
