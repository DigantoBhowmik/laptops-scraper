import argparse
import csv
import sys
from dataclasses import dataclass
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


URL = "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops"


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
    args = parse_args(argv)
    driver = build_driver(headless=not args.no_headless)
    try:
        driver.get(URL)
        products = scrape_products(driver, args.max, deep=getattr(args, "deep", False))
        delimiter = "\t" if getattr(args, "tsv", False) else ","
        write_csv(products, args.out, delimiter=delimiter)
        for p in products:
            print(f"{p.price}\t{p.name}\t{p.description}")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
