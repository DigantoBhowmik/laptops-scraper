from dotenv import load_dotenv
import os

load_dotenv()  # load values from .env if present

# Central configuration
CONFIG_DEFAULTS = {
    "max": 100,
    "sheet_id": os.getenv("SHEET_ID"),
    "sheet_tab": "Sheet1",
    "sheet_mode": "replace",
    "gcp_creds": "credentials.json",
    "timestamp": True,
    "no_headless": False,
    "deep": True,
}
