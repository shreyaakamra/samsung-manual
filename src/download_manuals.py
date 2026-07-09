"""
download_manuals.py

Downloads Samsung product manuals (PDFs) from URLs you provide, saves them
into a local folder, and builds a manifest.json that tags each file with
product metadata. This manifest is what lets Qdrant filter searches later
(e.g. "only search Galaxy S24 chunks").

HOW TO GET THE URLS:
  1. Go to samsung.com -> Support -> your region
  2. Search for the product (e.g. "Galaxy S24")
  3. Open the product's support page -> Manuals & Downloads
  4. Right-click the PDF link -> Copy Link Address
  5. Paste it into MANUALS list below

Run this on YOUR machine (not in a sandboxed environment), since it needs
real internet access to samsung.com.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict

import requests

# ---------------------------------------------------------------------------
# 1. Fill this in with real Samsung manual URLs + metadata.
#    Start with just 5-10 to test the pipeline before scaling up.
# ---------------------------------------------------------------------------

MANUALS = [
    {
        "url": "https://REPLACE_WITH_REAL_SAMSUNG_PDF_URL.pdf",
        "product_name": "Galaxy S24",
        "category": "smartphone",
        "manual_type": "user guide",
    },
    {
        "url": "https://REPLACE_WITH_REAL_SAMSUNG_PDF_URL.pdf",
        "product_name": "Galaxy Tab S9",
        "category": "tablet",
        "manual_type": "user guide",
    },
    # add more entries here...
]

OUTPUT_DIR = Path(__file__).parent.parent / "manuals"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
REQUEST_DELAY_SECONDS = 2  # be polite, don't hammer their servers


@dataclass
class ManualRecord:
    file_name: str
    local_path: str
    source_url: str
    product_name: str
    category: str
    manual_type: str


def safe_filename(product_name: str, manual_type: str) -> str:
    base = f"{product_name}_{manual_type}".lower()
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in base) + ".pdf"


def download_manual(entry: dict, dest_dir: Path) -> ManualRecord | None:
    file_name = safe_filename(entry["product_name"], entry["manual_type"])
    dest_path = dest_dir / file_name

    if dest_path.exists():
        print(f"  [skip] already downloaded: {file_name}")
    else:
        try:
            resp = requests.get(entry["url"], timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (educational RAG project)"
            })
            resp.raise_for_status()
            dest_path.write_bytes(resp.content)
            print(f"  [ok]   downloaded: {file_name}")
        except requests.RequestException as e:
            print(f"  [fail] {entry['url']} -> {e}")
            return None

    return ManualRecord(
        file_name=file_name,
        local_path=str(dest_path),
        source_url=entry["url"],
        product_name=entry["product_name"],
        category=entry["category"],
        manual_type=entry["manual_type"],
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = []

    print(f"Downloading {len(MANUALS)} manuals into {OUTPUT_DIR}...\n")
    for entry in MANUALS:
        if "REPLACE_WITH_REAL_SAMSUNG_PDF_URL" in entry["url"]:
            print(f"  [skip] placeholder URL for {entry['product_name']} — fill this in first")
            continue
        record = download_manual(entry, OUTPUT_DIR)
        if record:
            records.append(asdict(record))
        time.sleep(REQUEST_DELAY_SECONDS)

    MANIFEST_PATH.write_text(json.dumps(records, indent=2))
    print(f"\nDone. {len(records)} manuals recorded in {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
