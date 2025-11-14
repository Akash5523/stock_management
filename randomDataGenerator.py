import requests
import random
import json
from datetime import datetime, timedelta
import time

# ---------------- CONFIG ----------------
API_URL = "http://127.0.0.1:5000/api/add"  # ✅ matches your Flask route
TOTAL_ITEMS = 2000
BATCH_SIZE = 100
RETRY_LIMIT = 3
# ----------------------------------------

def generate_item(index):
    """Generate one fake stock item."""
    base_date = datetime(2025, 11, 1)
    inward_date = base_date + timedelta(days=random.randint(0, 15))
    outward_date = inward_date + timedelta(days=random.randint(1, 6))

    inward_qty = random.randint(20, 500)
    outward_qty = random.randint(0, max(inward_qty - 1, 1))
    inward_unit_price = round(random.uniform(25, 90), 2)
    outward_unit_price = round(inward_unit_price * random.uniform(1.05, 1.25), 2)

    return {
        "item_code": f"ITM{index:05d}",
        "item_description": f"Widget {chr(65 + (index % 26))}{index}",
        "inward_invoice_no": f"INV{1000 + index}",
        "inward_date": inward_date.strftime("%Y-%m-%d"),
        "uom": "Nos",
        "inward_qty": inward_qty,
        "inward_unit_price": inward_unit_price,
        "outward_qty": outward_qty,
        "outward_unit_price": outward_unit_price,
        "outward_invoice_no": f"OUT{2000 + index}",
        "outward_date": outward_date.strftime("%Y-%m-%d"),
        "eway_bill_number": f"EWB{7000 + index}",
        "vehicle_number": f"MH12AA{1000 + index}",
        "po_number": f"PO{9000 + index}"
    }


def send_batch(batch_data, attempt=1):
    """Send one batch safely with retries."""
    try:
        response = requests.post(API_URL, json=batch_data, timeout=30)
        if response.status_code == 201:
            print(f"✅ Uploaded {len(batch_data)} items successfully.")
        else:
            print(f"⚠️  Batch failed [{response.status_code}]: {response.text}")
    except requests.exceptions.RequestException as e:
        if attempt <= RETRY_LIMIT:
            print(f"⚠️  Retry {attempt}/{RETRY_LIMIT} after error: {e}")
            time.sleep(3)
            send_batch(batch_data, attempt + 1)
        else:
            print(f"❌ Failed to send batch after {RETRY_LIMIT} attempts.")


def main():
    all_items = [generate_item(i) for i in range(1, TOTAL_ITEMS + 1)]
    total_batches = (TOTAL_ITEMS // BATCH_SIZE) + (1 if TOTAL_ITEMS % BATCH_SIZE else 0)

    print(f"🚀 Starting upload of {TOTAL_ITEMS} inventory records ({total_batches} batches)...")

    for batch_index in range(total_batches):
        start = batch_index * BATCH_SIZE
        end = start + BATCH_SIZE
        batch = all_items[start:end]
        print(f"\n📦 Sending batch {batch_index + 1}/{total_batches} (items {start + 1}–{end})")
        send_batch(batch)
        time.sleep(1)  # avoid overloading the server

    print("\n✅ Upload completed successfully!")


if __name__ == "__main__":
    main()
