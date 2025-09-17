# Laptop Scraper
## **1. Overview**

The project is a **headless Selenium-based scraper** that collects **laptop product data** (Name, Price, Description) from the WebScraper test e-commerce site.

Each record is enriched with a **unified Extraction Timestamp** and published directly to a **Google Sheet**.

- Optional **deep scraping** mode visits each product’s detail page.
- Configuration is centralized via **config.py** and environment variables loaded with **python-dotenv**.
- **No local CSV/TSV output** (simplifies workflow). Persistence = Google Sheets + console output.

---

## **2. Tech Stack & Key Components**

- **Selenium + webdriver-manager** → Browser automation (Chrome)
- **gspread + google-auth** → Google Sheets integration
- **python-dotenv** → Environment variable management

**Python modules:**

- config.py → central configuration + env overrides
- models.py → Product dataclass
- driver.py → Chrome WebDriver factory
- scraper.py → scraping logic + source URL
- sheets.py → Google Sheets writer
- main.py → orchestration / entrypoint

---

## **3. How It Works (Flow)**

1. Load .env (if present) and merge with defaults (config.py).
2. Start **headless Chrome** (unless NO_HEADLESS=true).
3. Navigate to laptops category listing.
4. For each page:
    - Collect product cards.
    - If DEEP=true, open each detail page for precise title/description.
5. Accumulate products up to **MAX**.
6. Build a **single UTC ISO timestamp** per run.
7. Write rows to Google Sheet using selected mode:
    - replace (clear + rewrite)
    - append (add rows)
    - new-sheet (timestamped tab)
8. Print each row to console.

---

## **4. Setup Instructions**

### **Prerequisites**

- Python **3.10+** (3.11 recommended)
- Google Cloud service account JSON with Sheets access
- Service account must have **shared edit access** to target Google Sheet

### **Steps**

1. Create a .env file.
2. Place service account JSON at GCP_CREDS_FILE path (default: credentials.json).
3. Run the scraper with Python:

```
python main.py
```

---

## **5. Configuration Reference (Environment Overrides)**

| **Variable** | **Purpose** | **Default** |
| --- | --- | --- |
| SHEET_ID | Target Google Sheet ID | None |
| GCP_CREDS_FILE | Service account JSON path | credentials.json |
| SHEET_TAB | Base worksheet name | Sheet1 |
| SHEET_MODE | replace / append / new-sheet | append |
| MAX | Max products to scrape | 100 (set in code) |
| DEEP | true/false → detail page scraping | True |
| NO_HEADLESS | true/false → run visible browser | False |
| TIMESTAMP | true/false → include timestamp | True |

---

## **6. Running Modes (Sheets)**

- **replace** → Clears SHEET_TAB then writes header + rows.
- **append** → Keeps data, adds new rows (header only if empty).
- **new-sheet** → Creates worksheet <SHEET_TAB>-<timestamp>.

---

## **7. Output Schema (Google Sheets)**

Columns:

1. Product Name
2. Price
3. Extraction Timestamp
4. Description

👉 Timestamp = per run, not per row. Ensures consistent batch identification.

---

## **8. Result Location**

Google Sheet:

If using **new-sheet** mode: Sheet1-2025-09-17T14-32-05.

---

## **9. Assumptions**

- Test site HTML structure remains stable (div.thumbnail, h4.price, .caption h4, etc.).
- Prices are clean (no numeric parsing needed).
- Service account has permissions before script runs.
- Deep pages load within 10s (WebDriverWait).
- One timestamp per run is sufficient.

---

## **10. Challenges & Mitigations**

- **Inconsistent product name elements** → Selector fallbacks + filter out site headers.
- **Stale elements during pagination** → Used staleness_of.
- **Sheet header drift** → Header verification warnings.
- **Credential security** → .env + env vars, no secrets in repo.
- **No CSV** → Single source of truth = Google Sheets.

---

## **11. Quick Troubleshooting**

| **Issue** | **Likely Cause** | **Fix** |
| --- | --- | --- |
| Empty sheet | Wrong SHEET_ID / no sharing | Verify sheet ID & share with service account |
| Auth error | Bad credentials path | Check GCP_CREDS_FILE |
| Browser fails | Missing Chrome / sandbox | Install Chrome, add flags |
| No descriptions | Deep mode off | Ensure DEEP=true |

---

## **12. Minimal Code Entry Points**

- **main.py** → contains run() entrypoint

---

## **13. Example**

## **.env**

```
SHEET_ID=your_google_sheet_id
```

---

## **15. Example Console Output**
