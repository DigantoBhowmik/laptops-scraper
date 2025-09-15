# Laptop Scraper

Scrapes the first 100 laptop products (name, price, description) from:
https://webscraper.io/test-sites/e-commerce/allinone/computers/laptops

## Setup

```zsh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```zsh
python scrape_laptops.py --max 100 --out laptops.csv
```

Options:
- `--max`: number of items to scrape (default 100)
- `--out`: CSV output path (default `laptops.csv`)
- `--no-headless`: show the browser window while scraping

The resulting CSV will have columns: `name`, `price`, `description`.