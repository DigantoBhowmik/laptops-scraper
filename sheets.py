import json
import os
import sys
from typing import List, Optional
from models import Product
import gspread
from google.oauth2.service_account import Credentials


def _load_creds(creds_arg: Optional[str]):
    def load_path(path: str):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    if creds_arg:
        if os.path.exists(creds_arg):
            return load_path(creds_arg)
        return json.loads(creds_arg)
    env_file = os.getenv("GCP_SERVICE_ACCOUNT_FILE")
    if env_file and os.path.exists(env_file):
        return load_path(env_file)
    env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if env_json:
        return json.loads(env_json)
    raise FileNotFoundError(
        "No Google credentials provided. Use config gcp_creds or environment variables GCP_SERVICE_ACCOUNT_FILE / GCP_SERVICE_ACCOUNT_JSON."
    )


def write_google_sheet(
    products: List[Product],
    sheet_id: str,
    sheet_tab: str,
    creds_arg: Optional[str],
    run_ts: str,
    mode: str = "replace",
) -> None:
    data = _load_creds(creds_arg)
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(data, scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)

    if mode == "new-sheet":
        suffix = run_ts.replace(":", "-")
        final_title = f"{sheet_tab}-{suffix}"[:95]
        worksheet = sheet.add_worksheet(title=final_title, rows=str(len(products) + 20), cols="6")
    else:
        try:
            worksheet = sheet.worksheet(sheet_tab)
        except Exception:
            worksheet = sheet.add_worksheet(title=sheet_tab, rows=str(len(products) + 20), cols="6")

    header = ["Product Name", "Price", "Description", "Extraction Timestamp"]
    data_rows = [[p.name, p.price, p.description, run_ts] for p in products]

    if mode in {"replace", "new-sheet"}:
        try:
            worksheet.clear()
        except Exception as e:
            print(f"Warning: could not clear worksheet: {e}", file=sys.stderr)
        try:
            worksheet.update("A1", [header] + data_rows, value_input_option="RAW")
        except Exception as e:
            raise RuntimeError(f"Worksheet update failed: {e}")
    elif mode == "append":
        try:
            existing_first = worksheet.row_values(1)
        except Exception:
            existing_first = []
        rows_to_write = []
        if not existing_first:
            rows_to_write.append(header)
        rows_to_write.extend(data_rows)
        try:
            next_row = len(worksheet.get_all_values()) + 1
        except Exception:
            next_row = 1
        try:
            worksheet.update(f"A{next_row}", rows_to_write, value_input_option="RAW")
        except Exception as e:
            raise RuntimeError(f"Append failed: {e}")
    else:
        raise ValueError(f"Unknown sheet mode: {mode}")

    try:
        first_row = worksheet.row_values(1)
        if first_row and first_row[0] != "Product Name":
            print("Warning: unexpected header after write.", file=sys.stderr)
    except Exception as e:
        print(f"Post-write verification failed: {e}", file=sys.stderr)
