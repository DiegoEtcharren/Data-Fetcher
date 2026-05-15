# Agenda Pro Data Fetcher

Agenda Pro Data Fetcher is a Python-based utility designed to automate the synchronization of sales and client data from AgendaPro into a local MySQL database. As a secondary feature, it also includes a tool for processing, categorizing, and importing bank account statements from CSV files directly into the database.

## Features

* **Primary: AgendaPro Data Sync (`local_sync.py`)**
  * Automates login to AgendaPro to extract session cookies using Selenium.
  * Fetches sales data, client details, and transactions through AgendaPro's internal APIs.
  * Automatically handles pagination and date-range chunking to prevent API limits.
  * Synchronizes data directly into a MySQL database (Aiven/Local), preventing duplicate entries by updating existing records.
* **Secondary: Bank Movements Importer (`bank_account_movements.py`)**
  * Parses bank account statements in CSV format.
  * Cleans text and standardizes date formatting.
  * Categorizes transactions automatically using a customizable keyword dictionary (e.g., Payroll, Services, Suppliers).
  * Inserts the cleaned and categorized data directly into the local MySQL database.

## Prerequisites

Before running the scripts, ensure you have the following installed:

* **Python 3.x**: Recommended 3.8 or higher.
* **MySQL Server**: A running instance of MySQL to store the synchronized data.
* **Google Chrome**: Required by Selenium for headless browser automation (used to fetch login cookies).

## Installation

1. Clone or download this repository.
2. Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Both scripts rely on environment variables to handle sensitive database and API credentials. You must create a `.env` file in the root directory of the project.

Create a `.env` file with the following template:

```env
# Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASS=your_database_password
DB_NAME=Nailkery # Or your preferred local database name

# AgendaPro Credentials
AGENDA_USER=your_agendapro_email@example.com
AGENDA_PASS=your_agendapro_password
```

## Usage

### 1. Synchronize AgendaPro Sales Data
To fetch the latest sales and client data from AgendaPro and sync it with your database, run:

```bash
python local_sync.py
```

### 2. Process Bank Account Movements
If you want to process a bank account statement, ensure the target CSV file path is properly set inside `bank_account_movements.py` (near the bottom in the `__main__` block), then run:

```bash
python bank_account_movements.py
```
