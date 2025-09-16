from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from models import Product

URL = "https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops"

def scrape_products(driver: webdriver.Chrome, max_items: int, deep: bool = False) -> List[Product]:
    products: List[Product] = []

    def scrape_detail_from_url(url: str) -> Product:
        original = driver.current_window_handle
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        driver.switch_to.window(driver.window_handles[-1])
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            try:
                price_el = driver.find_element(By.CSS_SELECTOR, "h4.price, h4.pull-right.price, .price")
            except Exception:
                price_el = None
            try:
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
                if href and deep:
                    detail = scrape_detail_from_url(href)
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
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.thumbnail")))
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
