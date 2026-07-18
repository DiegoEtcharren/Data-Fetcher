import re
import time
import calendar
from datetime import datetime, timedelta
import os

# Data & API Libraries
import requests
import pandas as pd
import mysql.connector
from dotenv import load_dotenv

# Selenium Libraries
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

# Load credentials from the .env file
load_dotenv()

# --- CONFIGURATION ---
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "Nailkery")

AGENDA_USER = os.getenv("AGENDA_USER")
AGENDA_PASS = os.getenv("AGENDA_PASS")

# Replace with your actual AgendaPro API base URL
API_BASE_URL = "https://agendapro.com/api/views/admin/v1"
API_BASE_URL_V1 = "https://agendapro.com/api/views/admin/v1"
API_BASE_URL_V2 = "https://agendapro.com/api/views/admin/v2"

def get_db_connection():
    """Establish connection to the Aiven MySQL database."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def get_agendapro_headers(credentials, headless=True):
    """ Get session cookies and headers configuration"""

    email, password = credentials[0], credentials[1]
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")

    # Required docker options
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Force execution via native ARM64 Chromium build inside the container
    chrome_options.binary_location = "/usr/bin/chromium"

    # Disable logging to keep the console clean
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # Directly reference native system driver binary pathway
    chrome_service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    try:
        driver.get("https://app.agendapro.com/sign_in")
        wait = WebDriverWait(driver, 20)

        # 1. Fill Email
        email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
        email_field.send_keys(email)

        # 2. Fill Password
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.send_keys(password)

        # 3. Click Login
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.submit-button")))
        login_button.click()

        # 4. Wait for redirect
        WebDriverWait(driver, 60).until(lambda d: "/bookings" in d.current_url)

        # Give it a moment to settle
        time.sleep(2)

        # 5. Extract Cookies
        cookies = driver.get_cookies()
        cookie_parts = [f"{c['name']}={c['value']}" for c in cookies]

        # 6. Form cookie string
        cookie_string = "; ".join(cookie_parts)
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9,es-US;q=0.8,es;q=0.7,de;q=0.6",
        "Cookie": cookie_string
        }
        return headers

    except Exception as e:
        print(f"❌ Session extraction failed: {e}")
        return None
    finally:
        driver.quit()

def convert_to_utc6(date_str):
    """
    Converts API date string to a Python datetime object in UTC-6.
    Returns a timestamp-ready object for MySQL.
    """
    if not date_str:
        return None
    try:
        dt = pd.to_datetime(date_str)
        # Localize to UTC if no timezone exists, then convert to Mexico City (UTC-6)
        if dt.tzinfo is None:
            dt = dt.tz_localize('UTC')
        dt_mexico = dt.tz_convert('America/Mexico_City')

        # Convert back to naive datetime object for standard DB upload
        return dt_mexico.to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None

def get_max_sale_date(cursor):
    """Retrieve the max date of sales currently in the database."""
    cursor.execute("SELECT MAX(paid_at) FROM sales")
    result = cursor.fetchone()[0]

    if result:
            return result + timedelta(seconds=1)
    else:
        # Default date JAN 1 2023:
        return datetime(2023, 1, 1)

def check_and_add_client(cursor, db_conn, external_client_id, headers):
    """Return clients id if not added it would added and then return client id"""
    # Check if the client already exists in the database:
    cursor.execute("SELECT client_id FROM clients WHERE external_client_id = %s", (external_client_id,))
    client_exists = cursor.fetchone()

    # If exists return ID:
    if client_exists:
        print(f"Returning client id: {client_exists[0]}")
        return client_exists[0]
    print(f"New client detected (ID: {external_client_id}). Fetching details...")
    try:
        # Fetch missing client profile from the API:
        client_url = f"{API_BASE_URL}/clients/{external_client_id}"
        print(f"Extracting sales_url: {client_url}")
        response = requests.get(client_url, headers=headers)
        response.raise_for_status()
        client_info = response.json().get('client', {})
        insert_query = """INSERT INTO clients (external_client_id, first_name, last_name, email, phone, created_at) VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(insert_query, (
            external_client_id,
            client_info.get('first_name', 'N/A'),
            client_info.get('last_name', ''),
            client_info.get('email', 'N/A'),
            client_info.get('phone', 'N/A'),
            client_info.get('created_at', None)
        ))
        db_conn.commit()
        new_internal_id = cursor.lastrowid
        print(f"Successfully added client (Internal ID: {new_internal_id})")
        return new_internal_id
    except Exception as e:
        print(f"❌ Error fetching client  {external_client_id}: {e}")
        return None

def get_category(name):
    """Identifies the category based on the item name prefix."""
    if not name:
        return "COMPLEMENTOS"

    if name.startswith("ML"): return "MANILOVE"
    if name.startswith("RT3"): return "RETOQUES 26 - 30 DÍAS"
    if name.startswith("GP"): return "GEL PIES"
    if name.startswith("RT2"): return "RETOQUES 21 - 25 DÍAS"
    if name.startswith("RT1"): return "RETOQUES 15 - 20 DÍAS"
    if name.startswith("CL"): return "COMBO LOVE"
    if name.startswith("PS"): return "PAQUETE SPA"
    if name.startswith("RC") or name.startswith("RG"): return "RETIROS"
    if name.startswith("MR") or name.startswith("C0"): return "MANIRUSO"
    if re.match(r"^(E00|D0|A0)", name): return "EFECTOS"

    return "COMPLEMENTOS"

def sync_sales_data(agendapro_credentials):
    """Main function to run the sync logic."""
    db_conn = get_db_connection()
    cursor = db_conn.cursor(buffered=True)

    try:
        headers = get_agendapro_headers(agendapro_credentials)
        start_date = get_max_sale_date(cursor)
        end_date_limit = datetime.now()

        print(f"Syncing sales starting from: {start_date}")

        current_chunk_start = start_date

        # Section the requests in periods of max 1 month
        while current_chunk_start < end_date_limit:
            # Find last day of the current month in the loop:
            last_day = calendar.monthrange(current_chunk_start.year, current_chunk_start.month)[1]
            month_end = current_chunk_start.replace(day=last_day, hour=23, minute=59, second=59)
            chunk_end_date = min(month_end, end_date_limit)

            page = 1
            while True:
                payload = {
                    "per_page": 100,
                    "page": page,
                    "start_date": current_chunk_start.strftime('%Y-%m-%dT%H:%M:%S-06:00'),
                    "end_date": chunk_end_date.strftime('%Y-%m-%dT%H:%M:%S-06:00')
                }
                sales_url = f"{API_BASE_URL_V2}/sales/sale"
                print(f"Extracting sales page {page} for period: {payload['start_date']} to {payload['end_date']}")

                try:
                    sale_response = requests.get(sales_url, headers=headers, params=payload)
                    sale_response.raise_for_status()
                    sales_data = sale_response.json()
                    sales_batch = sales_data.get("data", [])

                    for record in sales_batch:
                        sale_id = record.get("id")
                        record["paid_at"] = convert_to_utc6(record.get("paid_at"))

                        if sale_id:
                            details_url = f"{API_BASE_URL_V2}/sales/sale/{sale_id}"
                            print(f"Extracting details: {details_url}")
                            try:
                                detail_response = requests.get(details_url, headers=headers)
                                detail_response.raise_for_status()
                                detail_data = detail_response.json()
                                detail_data["paid_at"] = convert_to_utc6(detail_data.get("paid_at"))

                                for tx in detail_data.get("transactions", []):
                                    tx["paid_at"] = convert_to_utc6(tx.get("paid_at"))

                                record["sales_detail"] = detail_data
                                time.sleep(0.3)

                            except Exception as e:
                                print(f"❌ Error fetching page {page}: {e}")
                                break

                    for sale in sales_batch:
                        detail = sale.get('sales_detail', sale)
                        ext_client_id = detail.get('client_id')
                        print(f"External Client ID: {ext_client_id}")
                        int_client_id = None

                        # 1. Safely check the database for missing clients and add if needed
                        if ext_client_id:
                            int_client_id = check_and_add_client(cursor, db_conn, ext_client_id, headers)

                        # Extract information to input into DB:
                        paid_at = detail.get('paid_at') or sale.get('paid_at')
                        total_amount = float(sale.get('total_amount', 0))
                        ext_sale_id = sale.get('id')
                        status = sale.get('status')
                        location_id = str(sale.get('location_id'))
                        location_name = sale.get('location_name')

                        # Insert Sale Data:
                        sale_query = """
                            INSERT INTO sales (external_sales_id, client_id, paid_at, status, total_amount, location_id, location_name)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            client_id=VALUES(client_id), total_amount=VALUES(total_amount),
                            paid_at=VALUES(paid_at), status=VALUES(status)
                        """
                        cursor.execute(sale_query, (ext_sale_id, int_client_id, paid_at, status, total_amount, location_id, location_name))

                        cursor.execute("SELECT sale_id FROM sales WHERE external_sales_id = %s", (ext_sale_id,))
                        result = cursor.fetchone()
                        if not result:
                            continue
                        internal_sale_id = result[0]

                        # Wipe existing items & transactions to prevent duplicates on update
                        cursor.execute("DELETE FROM sales_items WHERE sale_id = %s", (internal_sale_id,))
                        cursor.execute("DELETE FROM transactions WHERE sale_id = %s", (internal_sale_id,))

                        cursor.execute("DELETE FROM sales_items WHERE sale_id = %s", (internal_sale_id,))

                        for item in detail.get('items', []):
                            name = item.get('name')
                            subtotal = float(item.get('subtotal', 0))
                            total = float(item.get('total', 0))
                            quantity = item.get('quantity', 1)
                            item_type = item.get('item_type')
                            category_label = get_category(name)

                            # Extract employee id:
                            ext_provider_id = None
                            instances = item.get('instances', [])
                            if instances and isinstance(instances, list):
                                provider_info = instances[0].get('provider', {})
                                ext_provider_id = provider_info.get('id')

                            int_provider_id = None
                            if ext_provider_id:
                                cursor.execute("SELECT provider_id FROM providers WHERE external_provider_id = %s", (ext_provider_id,))
                                prov_result = cursor.fetchone()
                                if prov_result:
                                    int_provider_id = prov_result[0]

                            item_query = """
                                INSERT INTO sales_items (sale_id, category, name, item_type, quantity, subtotal, total, provider_id)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(item_query, (internal_sale_id, category_label, name, item_type, quantity, subtotal, total, int_provider_id))

                            for tx in detail.get('transactions', []):
                                ext_tx_id = tx.get('id')
                                amount = float(tx.get('total', 0)) # Updated to target 'total' based on JSON
                                payment_method = tx.get('payment_method')
                                trans_query = """
                                    INSERT INTO transactions (external_transaction_id, sale_id, payment_method, amount)
                                    VALUES (%s, %s, %s, %s)
                                    ON DUPLICATE KEY UPDATE amount=VALUES(amount), payment_method=VALUES(payment_method)
                                """
                                cursor.execute(trans_query, (ext_tx_id, internal_sale_id, payment_method, amount))

                    db_conn.commit()

                    # Pagination logic
                    pagination = sales_data.get("pagination", {})
                    next_page = pagination.get("next_page")
                    if not next_page:
                        break

                    page = next_page
                    time.sleep(0.5)

                except Exception as e:
                    print(f"❌ Error fetching page {page}: {e}")
                    break

            # Update end date:
            current_chunk_start = chunk_end_date + timedelta(seconds=1)

        print("Data sync completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    agenda_pro_credentials = [AGENDA_USER, AGENDA_PASS]
    sync_sales_data(agenda_pro_credentials)