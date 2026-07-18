# Nailkery Scraping & Sync Automation Project

This document serves as a comprehensive migration, containerization, and automation log for the `data-fetcher-Nailkery` engine running on a Raspberry Pi (ARM64 architecture). It details the configuration architecture, challenges resolved, and deployment strategies required to run headlessly under Docker.

---

## 1. Project Architecture & Environment Overview

The production system architecture separates web applications/APIs from scheduled background data collection processes. The layout structured on the host engine is organized as follows:

```text
~/projects/Nailkery/
├── docker-compose.yml       # Orchestrates core service nodes
├── .env                     # Global environment variables & database secrets
├── data-fetcher-Nailkery/   # Isolated repository folder for Python scrapers
│   ├── Dockerfile           # Tailored Debian-ARM64 environment build definition
│   ├── requirements.txt     # Python tracking and driver dependency modules
│   ├── local_sync.py        # Central data-sync entry point (3:00 AM Cron Target)
│   └── bank_account_movements.py
```

### Key Technical Specs:
* **Host Hardware Architecture:** Linux `arm64` / `aarch64` (Raspberry Pi).
* **Base Container Image:** Debian-based system explicitly structured to accommodate native compiled binaries for ARM64.
* **Orchestration Matrix:** Docker Compose isolating engine operations to ensure dependencies don't drift on the system core.

---

## 2. Docker Architecture Configuration

To avoid dependency mismatches across Python package versions and host-level binaries, the entire runtime footprint is packaged inside a custom image context.

### The ARM64 Dockerfile Setup
The core challenge of automated web scraping on ARM64 platforms is the lack of official Google-compiled pre-packaged binaries for Chrome/Chromedriver. This setup circumvents this problem by using Debian’s natively compiled distribution packages via `apt`.

```dockerfile
FROM python:3.11-slim-bullseye

# System layer configuration: Install native ARM64 Chromium and Chromedriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency Optimization Layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Project Source Copy
COPY . .

CMD ["python", "local_sync.py"]
```

### Docker Compose Service Definition
The service is mapped within the primary multi-container landscape file (`docker-compose.yml`):

```yaml
version: '3.8'

services:
  data_fetcher:
    build:
      context: ./data-fetcher-Nailkery
      dockerfile: Dockerfile
    volumes:
      - ./data-fetcher-Nailkery:/app
    env_file:
      - .env
    restart: "no"
```
*Note: Using `env_file: - .env` bubbles global values (like database connections, passwords, and target APIs) safely inside the execution context without hardcoding strings into repository commits.*

---

## 3. Core Technical Resolutions & Fixes

### Issue 1: Missing Driver Version for Linux-ARM64
* **Symptom:** Scripts using `webdriver_manager` or standard `Selenium Manager` crashed with:
  `An error occurred: No such driver version 151.0.7922.34 for linux-arm64`
* **Root Cause:** Auto-download tools look up x86_64 pre-compiled repositories maintained by Google, which completely lack compatible ARM64 versions for Raspberry Pi platforms.
* **Resolution Implementation:** The initialization routine in `local_sync.py` was altered to skip internet resolution checks and force explicit links directly to the local system binaries provided by the base container build:

```python
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Force execution via native ARM64 Chromium build
chrome_options.binary_location = "/usr/bin/chromium"

# Directly reference native system driver binary pathway 
chrome_service = Service(executable_path="/usr/bin/chromedriver")

# Initialize isolated instance
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
```

### Issue 2: Absolute Container Path Context Contexts
* **Symptom:** System run command executions like `docker compose run --rm data_fetcher python main.py` returned file system execution errors (`python: can't open file '/app/main.py': [Errno 2] No such file or directory`).
* **Resolution:** Root project structures map inside `/app`. Code maps mapped files seamlessly directly to standard scripts like `local_sync.py` or `bank_account_movements.py`.

---

## 4. Production Cron Automation Workflow

To guarantee system synchronization daily without interactive terminal commands, a standard Unix system cron profile handles native invocation directly on the host OS. This bypasses Docker sandbox constraints on the 1GB RAM Raspberry Pi 3.

### Target Automation Rule
The script runs automatically at **3:00 AM** every single morning:

```text
0 3 * * * cd ~/projects/Nailkery/data-fetcher-Nailkery && /usr/bin/python3 local_sync.py >> ~/projects/Nailkery/data-fetcher-Nailkery/local_sync.log 2>&1
```

### Breakdown of Automated Properties:
1. `0 3 * * *`: Precise trigger matrix mapping to the third hour of the day.
2. `cd ~/projects/Nailkery/data-fetcher-Nailkery`: Switches context to the script directory.
3. `/usr/bin/python3 local_sync.py`: Executes the sync scraper natively using the host's Python interpreter and Pi-optimized Chromium build, avoiding container sandbox memory crashes.
4. `>> .../local_sync.log 2>&1`: Redirects standard output (`stdout`) and error arrays (`stderr`) down into tracking files for rapid debugging.
