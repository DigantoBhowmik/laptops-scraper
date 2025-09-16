import argparse
import csv
import json
import sys
from dataclasses import dataclass
from typing import List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


URL = "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops"

# When you want to run the script without passing any command-line arguments,
# edit these values. If the script is invoked with arguments, they override
# these defaults via argparse. If invoked with no arguments, these are used.
CONFIG_DEFAULTS = {
    "max": 100,
    "out": "laptops.csv",
    "no_headless": False,
    "tsv": False,
    "deep": True,
    "sheet_id": "12QpdYmm5QrLfWlLxcst06H_MRQCTekUdNKgu-QhX_w0",
    "sheet_tab": "Sheet1",
    "gcp_creds": "credentials.json",
}


@dataclass
class Product:
    name: str
    price: str
    description: str


def build_driver(headless: bool = True) -> webdriver.Chrome:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def write_csv(products: List[Product], out_path: str, delimiter: str = ",") -> None:
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["name", "price", "description"])
        for p in products:
            writer.writerow([p.name, p.price, p.description])


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape laptop names and prices")
    parser.add_argument("--max", type=int, default=100, help="Max items to scrape")
    parser.add_argument("--out", type=str, default="laptops.csv", help="CSV output path")
    parser.add_argument("--no-headless", action="store_true", help="Run browser non-headless")
    parser.add_argument("--tsv", action="store_true", help="Write tab-separated output instead of CSV")
    parser.add_argument("--deep", action="store_true", help="Open each product page and scrape details from there")
    parser.add_argument("--sheet-id", type=str, help="Google Sheet ID to write results (optional)")
    parser.add_argument("--sheet-tab", type=str, default="Sheet1", help="Worksheet title (default Sheet1)")
    parser.add_argument(
        "--gcp-creds",
        type=str,
        help="Path to a Google service account JSON credentials file (or inline JSON string).",
    )
    return parser.parse_args(argv)


def scrape_products(driver: webdriver.Chrome, max_items: int, deep: bool = False) -> List[Product]:
    products: List[Product] = []

    def scrape_detail_from_url(url: str) -> Product:
        original = driver.current_window_handle
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        driver.switch_to.window(driver.window_handles[-1])
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
            # Try multiple selectors for robustness across pages
            try:
                price_el = driver.find_element(By.CSS_SELECTOR, "h4.price, h4.pull-right.price, .price")
            except Exception:
                price_el = None
            try:
                # Prefer product title within the product caption over generic page headers
                name_el = driver.find_element(By.CSS_SELECTOR, ".caption h4:not(.pull-right):not(.price)")
            except Exception:
                try:
                    name_el = driver.find_element(By.CSS_SELECTOR, ".caption h4, h4.title, .title")
                except Exception:
                    name_el = None
            try:
                desc_el = driver.find_element(By.CSS_SELECTOR, "#description, p.description, .description, .caption p")
            except Exception:
                desc_el = None
            raw_name = (name_el.text.strip() if name_el else "")
            # Avoid using site-level headers like "Test Sites" as product names
            clean_name = "" if raw_name.lower() in {"test sites", "test site"} else raw_name
            return Product(
                name=clean_name,
                price=(price_el.text.strip() if price_el else ""),
                description=(desc_el.text.strip() if desc_el else ""),
            )
        finally:
            driver.close()
            driver.switch_to.window(original)

    def collect_from_page() -> None:
        cards = driver.find_elements(By.CSS_SELECTOR, "div.thumbnail")
        for card in cards:
            if len(products) >= max_items:
                break
            try:
                price_el = card.find_element(By.CSS_SELECTOR, "h4.price, h4.pull-right.price, .price")
            except Exception:
                price_el = None
            try:
                name_el = card.find_element(By.CSS_SELECTOR, "a.title, h4 a")
            except Exception:
                name_el = None
            try:
                desc_el = card.find_element(By.CSS_SELECTOR, "p.description, .description, .caption p")
            except Exception:
                desc_el = None
            if name_el is not None:
                href = name_el.get_attribute("href")
                if href:
                    detail = scrape_detail_from_url(href)
                    # Fallback to list values if detail page misses something
                    products.append(
                        Product(
                            name=detail.name or name_el.text.strip(),
                            price=detail.price or (price_el.text.strip() if price_el else ""),
                            description=detail.description or (desc_el.text.strip() if desc_el else ""),
                        )
                    )
                    continue
            if name_el and price_el:
                products.append(
                    Product(
                        name=name_el.text.strip(),
                        price=price_el.text.strip(),
                        description=(desc_el.text.strip() if desc_el else ""),
                    )
                )

    while len(products) < max_items:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.thumbnail"))
        )
        visible_cards = driver.find_elements(By.CSS_SELECTOR, "div.thumbnail")
        first_card = visible_cards[0] if visible_cards else None
        collect_from_page()
        if len(products) >= max_items:
            break
        try:
            pagination = driver.find_element(By.CSS_SELECTOR, "ul.pagination")
            next_li_candidates = pagination.find_elements(By.CSS_SELECTOR, "li")
            next_li = next_li_candidates[-1] if next_li_candidates else None
            if not next_li:
                break
            classes = next_li.get_attribute("class") or ""
            if "disabled" in classes:
                break
            next_link = next_li.find_element(By.CSS_SELECTOR, "a")
            driver.execute_script("arguments[0].click();", next_link)
            if first_card is not None:
                WebDriverWait(driver, 10).until(EC.staleness_of(first_card))
        except Exception:
            break

    return products[:max_items]


def main(argv: List[str]) -> int:
    # If any argv provided, use argparse (explicit override). Otherwise build args from CONFIG_DEFAULTS.
    if argv:
        args = parse_args(argv)
    else:
        class _Args:  # lightweight object to mimic argparse namespace
            pass
        args = _Args()
        for k, v in CONFIG_DEFAULTS.items():
            setattr(args, k, v)
    driver = build_driver(headless=not args.no_headless)
    try:
        driver.get(URL)
        products = scrape_products(driver, args.max, deep=getattr(args, "deep", False))
        delimiter = "\t" if getattr(args, "tsv", False) else ","
        write_csv(products, args.out, delimiter=delimiter)
        if args.sheet_id and args.gcp_creds:
            try:
                write_google_sheet(products, args.sheet_id, args.sheet_tab, args.gcp_creds)
                print(f"Uploaded {len(products)} rows to Google Sheet {args.sheet_id} / {args.sheet_tab}")
            except Exception as e:
                print(f"Failed to write Google Sheet: {e}", file=sys.stderr)
        for p in products:
            print(f"{p.price}\t{p.name}\t{p.description}")
        return 0
    finally:
        driver.quit()


def _load_creds(creds_arg: str):
    # creds_arg can be a file path or a JSON string
    try:
        # Try treat as path
        with open(creds_arg, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fall back to inline JSON string
        return json.loads(creds_arg)


def write_google_sheet(products: List[Product], sheet_id: str, sheet_tab: str, creds_arg: str) -> None:
    import gspread  # imported lazily to avoid requirement if unused
    from google.oauth2.service_account import Credentials

    data = _load_creds(creds_arg)
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(data, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    try:
        worksheet = sheet.worksheet(sheet_tab)
    except Exception:
        # Create with enough rows + buffer
        worksheet = sheet.add_worksheet(title=sheet_tab, rows=str(len(products) + 20), cols="5")
    rows = [["Name", "Price", "Description"]] + [
        [p.name, p.price, p.description] for p in products
    ]
    needed_rows = len(rows)
    try:
        current_rows = worksheet.row_count
        if current_rows < needed_rows:
            worksheet.resize(rows=needed_rows)
    except Exception as e:
        print(f"Could not resize worksheet: {e}", file=sys.stderr)
    # Clear sheet before updating for deterministic content
    try:
        worksheet.clear()
    except Exception as e:
        print(f"Warning: could not clear worksheet: {e}", file=sys.stderr)
    # Use A1 update to avoid size inference issues
    try:
        worksheet.update("A1", rows, value_input_option="RAW")
    except Exception as e:
        raise RuntimeError(f"Worksheet update failed: {e}")
    # Simple post-condition check
    try:
        fetched_first_row = worksheet.row_values(1)
        if fetched_first_row[:3] != ["name", "price", "description"]:
            print("Warning: header row mismatch after update.", file=sys.stderr)
    except Exception as e:
        print(f"Post-update verification failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
