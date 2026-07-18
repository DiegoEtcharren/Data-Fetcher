import subprocess
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def test_selenium(headless_mode="--headless"):
    print(f"--- Testing Selenium with flag: {headless_mode} ---")
    chrome_options = Options()
    chrome_options.add_argument(headless_mode)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    chrome_service = Service(executable_path="/usr/bin/chromedriver")
    
    try:
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        print("Driver initialized successfully.")
        driver.get("https://app.agendapro.com/sign_in")
        print(f"Successfully loaded page. Title: {driver.title}")
        driver.quit()
        print("SUCCESS!")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

def test_chromium_direct():
    print("\n--- Testing Chromium Binary Directly via Subprocess ---")
    cmd = [
        "/usr/bin/chromium",
        "--headless",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--dump-dom",
        "https://www.google.com"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print(f"Return code: {res.returncode}")
        if res.returncode == 0:
            print("Chromium direct run succeeded. First 200 chars of output:")
            print(res.stdout[:200])
        else:
            print("Chromium direct run returned non-zero code.")
            print("--- STDOUT ---")
            print(res.stdout)
            print("--- STDERR ---")
            print(res.stderr)
    except Exception as e:
        print(f"Error running chromium directly: {e}")

if __name__ == "__main__":
    # Test with standard --headless
    success = test_selenium("--headless")
    
    # If standard headless failed, try --headless=old and --headless=new
    if not success:
        print("\nRetrying with --headless=old...")
        success = test_selenium("--headless=old")
        
    if not success:
        print("\nRetrying with --headless=new...")
        success = test_selenium("--headless=new")
        
    # Run direct test to get internal errors
    if not success:
        test_chromium_direct()
