from __future__ import annotations

import argparse
import os
import re
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from tqdm import tqdm

TEXT_SEARCH_ENDPOINT = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_ENDPOINT = "https://maps.googleapis.com/maps/api/place/details/json"


# ──────────────────────────────────────────────────────────────────────────────
# Cleaning Utility
# ──────────────────────────────────────────────────────────────────────────────

def clean_input_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Strip junk columns and normalize useful fields."""
    junk_patterns = [r'flex', r'truncate', r'font', r'dark:border', r'inline', r'text-', r'block href']
    cleaned_columns = []
    for col in df.columns:
        if any(re.search(pattern, col, re.IGNORECASE) for pattern in junk_patterns):
            continue
        cleaned_columns.append(col)

    df = df[cleaned_columns].copy()

    rename_map = {
        "Company": "Company Name",
        "flex 2": "City"
    }
    df.rename(columns=rename_map, inplace=True)

    if "Country" not in df.columns:
        df["Country"] = ""

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Google Places Utilities
# ──────────────────────────────────────────────────────────────────────────────

def build_query(row: pd.Series, company_col: str, context_cols: List[str]) -> str:
    parts = [str(row.get(company_col, "")).strip()]
    for col in context_cols:
        val = str(row.get(col, "")).strip()
        if val:
            parts.append(val)
    return ", ".join(parts)


def text_search(query: str, api_key: str, region: Optional[str] = None) -> Optional[str]:
    params = {"query": query, "key": api_key}
    if region:
        params["region"] = region
    data = requests.get(TEXT_SEARCH_ENDPOINT, params=params, timeout=10).json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    return data["results"][0]["place_id"]


def extract_address_components(components: List[dict]) -> Dict[str, str]:
    address = {"street": "", "city": "", "zip_code": "", "country": ""}
    street_number = route = None

    for comp in components:
        types = comp.get("types", [])
        if "street_number" in types:
            street_number = comp["long_name"]
        elif "route" in types:
            route = comp["long_name"]
        elif "locality" in types:
            address["city"] = comp["long_name"]
        elif "postal_code" in types:
            address["zip_code"] = comp["long_name"]
        elif "country" in types:
            address["country"] = comp["long_name"]

    if street_number or route:
        address["street"] = " ".join(part for part in [street_number, route] if part)

    return address


def place_details(place_id: str, api_key: str) -> Tuple[Optional[str], Optional[str], Dict[str, str]]:
    params = {
        "place_id": place_id,
        "fields": "international_phone_number,website,address_components",
        "key": api_key,
    }
    result = requests.get(DETAILS_ENDPOINT, params=params, timeout=10).json().get("result", {})
    phone = result.get("international_phone_number")
    website = result.get("website")
    domain = None
    if website:
        domain = urllib.parse.urlparse(website).netloc.removeprefix("www.")
    address = extract_address_components(result.get("address_components", []))
    return phone, domain, address


# ──────────────────────────────────────────────────────────────────────────────
# Main Logic
# ──────────────────────────────────────────────────────────────────────────────

def enrich_file(
    input_path: Path,
    output_path: Path,
    api_key: str,
    region: Optional[str] = None,
    sleep_seconds: float = 0.1,
    context_cols: List[str] | None = None,
) -> None:
    context_cols = context_cols or []

    ext = input_path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(input_path, encoding="utf-8-sig")
    elif ext in [".xlsx", ".xls"]:
        df = pd.read_excel(input_path)
    else:
        raise SystemExit("❌ Unsupported input file type. Use .csv or .xlsx")

    df = clean_input_dataframe(df)

    company_col = "Company Name"
    if company_col not in df.columns:
        raise SystemExit("❌ Could not detect a valid 'Company Name' column after cleaning.")

    for col in ["phone_number", "domain", "street", "city", "zip_code", "country", "status"]:
        if col not in df.columns:
            df[col] = ""

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Enriching companies"):
        query = build_query(row, company_col, context_cols)
        if not query:
            df.at[idx, "status"] = "EMPTY_NAME"
            continue

        try:
            pid = text_search(query, api_key, region)
            if pid:
                phone, domain, address = place_details(pid, api_key)
                df.at[idx, "phone_number"] = phone or ""
                df.at[idx, "domain"] = domain or ""
                df.at[idx, "street"] = address.get("street", "")
                df.at[idx, "city"] = address.get("city", "")
                df.at[idx, "zip_code"] = address.get("zip_code", "")
                df.at[idx, "country"] = address.get("country", "")
                df.at[idx, "status"] = "OK" if phone or domain or any(address.values()) else "PARTIAL"
            else:
                df.at[idx, "status"] = "NOT_FOUND"
        except Exception as exc:
            df.at[idx, "status"] = f"ERROR:{exc}"[:250]
        time.sleep(sleep_seconds)

    if output_path.suffix.lower() == ".csv":
        df.to_csv(output_path, index=False, encoding="utf-8")
    elif output_path.suffix.lower() in [".xlsx", ".xls"]:
        df.to_excel(output_path, index=False)
    else:
        raise SystemExit("❌ Unsupported output file type. Use .csv or .xlsx")


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk enrich a company list with Google Places contact data.")
    parser.add_argument("--input", required=True, type=Path, help="Input CSV/XLSX path")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV/XLSX path")
    parser.add_argument("--api-key", default=os.getenv("GOOGLE_API_KEY"), help="Google Places API key")
    parser.add_argument("--region", help="Two‑letter region bias, e.g. 'de' or 'us'")
    parser.add_argument("--sleep", type=float, default=0.1, help="Delay between requests (s)")
    parser.add_argument("--context", help="Comma‑separated extra columns (e.g. 'City,Country')")

    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("❌ Provide an API key via --api-key or $GOOGLE_API_KEY.")

    context_cols = [c.strip() for c in args.context.split(",")] if args.context else []

    try:
        enrich_file(args.input, args.output, args.api_key, args.region, args.sleep, context_cols)
    except KeyboardInterrupt:
        sys.exit("⏹️ Interrupted by user.")
    else:
        print(f"✅ Done → {args.output}")


if __name__ == "__main__":
    main()
