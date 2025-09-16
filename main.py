from datetime import datetime
from config import CONFIG_DEFAULTS
from driver import build_driver
from scraper import scrape_products, URL
from sheets import write_google_sheet


def run():
    class Cfg:  # simple namespace
        pass
    cfg = Cfg()
    for k, v in CONFIG_DEFAULTS.items():
        setattr(cfg, k, v)
    if not hasattr(cfg, "no_headless"):
        cfg.no_headless = False
    if not hasattr(cfg, "deep"):
        cfg.deep = True
    driver = build_driver(headless=not cfg.no_headless)
    run_ts = datetime.utcnow().isoformat(timespec="seconds")
    try:
        driver.get(URL)
        products = scrape_products(driver, cfg.max, deep=cfg.deep)
        if cfg.sheet_id:
            try:
                write_google_sheet(
                    products,
                    sheet_id=cfg.sheet_id,
                    sheet_tab=cfg.sheet_tab,
                    creds_arg=getattr(cfg, "gcp_creds", None),
                    run_ts=run_ts,
                    mode=cfg.sheet_mode,
                )
                print(f"Uploaded {len(products)} rows to Google Sheet {cfg.sheet_id} (mode={cfg.sheet_mode})")
            except Exception as e:
                print(f"Failed to write Google Sheet: {e}")
        for p in products:
            if getattr(cfg, "timestamp", False):
                print(f"{p.price}\t{p.name}\t{p.description}\t{run_ts}")
            else:
                print(f"{p.price}\t{p.name}\t{p.description}")
    finally:
        driver.quit()


if __name__ == "__main__":
    run()
