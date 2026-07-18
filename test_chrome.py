import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def test_balanced_low_memory():
    print("\n--- Testing Passive Page Load with Balanced Low-Memory Flags ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-webgl")
    
    # Disable GPU compositing to save RAM and prevent compositor crashes
    chrome_options.add_argument("--disable-gpu-compositing")
    
    # Offload shared memory to /tmp disk/swap to protect physical RAM
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Balanced V8 heap (256MB) and disable optimizations to save CPU/RAM
    chrome_options.add_argument('--js-flags=--max-old-space-size=256 --no-opt')
    
    # Optimize features and background processes
    chrome_options.add_argument("--disable-features=AudioServiceOutOfProcess,ClientSidePhishingDetection,JavaScriptProfiler,OptimizationGuide,SitePerProcess,Translate")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad")
    
    # Standard desktop User-Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Auto-detect Chromium and ChromeDriver binary locations
    chrome_path = "/usr/bin/chromium"
    if not os.path.exists(chrome_path):
        chrome_path = "/usr/bin/chromium-browser"

    driver_path = "/usr/bin/chromedriver"
    if not os.path.exists(driver_path):
        driver_path = "/usr/lib/chromium-browser/chromedriver"

    # Force execution via native ARM64 Chromium build
    chrome_options.binary_location = chrome_path

    # Directly reference native system driver binary pathway
    chrome_service = Service(executable_path=driver_path)
    
    driver = None
    try:
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        print("1. Driver initialized.")
        
        driver.get("https://app.agendapro.com/sign_in")
        print("2. Driver.get() returned. Starting 5-second sleep...")
        
        for i in range(1, 6):
            time.sleep(1)
            # Try to query title to verify the tab is still alive
            title = driver.title
            print(f"   Sleep second {i}... tab is alive (Title: {title})")
            
        print("3. Sleep completed successfully! Browser did not crash passively.")
        print("4. Attempting to get DOM length...")
        dom_length = len(driver.page_source)
        print(f"   Page source size: {dom_length} characters.")
        
        return True
        
    except Exception as e:
        print(f"❌ Balanced test FAILED: {e}")
        return False
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    test_balanced_low_memory()
