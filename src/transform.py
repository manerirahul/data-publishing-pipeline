"""Transform stage: standardize validated records to the publish schema.

Deterministic, side-effect free transformations only: type coercion, code
standardization, and derived fields. Anything ambiguous belongs in
validation (as a reject), not here as a silent guess.
"""
from __future__ import annotations

from datetime import datetime

STATE_NAMES = {
    "TEXAS": "TX", "CALIFORNIA": "CA", "WASHINGTON": "WA",
    "NEW YORK": "NY", "FLORIDA": "FL", "ARIZONA": "AZ",
}

STATUS_MAP = {
    "DELIVERED": "DELIVERED", "SHIPPED": "SHIPPED",
    "PENDING": "PENDING", "CANCELLED": "CANCELLED",
    "CANCELED": "CANCELLED",
}


def standardize_state(value: str) -> str:
    v = (value or "").strip().upper()
    return STATE_NAMES.get(v, v)


def transform_record(rec: dict, batch_id: str) -> dict:
    quantity = int(float(rec["quantity"]))
    unit_price = round(float(rec["unit_price"]), 2)
    order_date = datetime.strptime(rec["order_date"].strip(), "%Y-%m-%d")
    return {
        "order_id": rec["order_id"].strip(),
        "customer_id": rec["customer_id"].strip(),
        "order_date": order_date.strftime("%Y-%m-%d"),
        "state": standardize_state(rec["state"]),
        "status": STATUS_MAP.get(rec["status"].strip().upper(), "UNKNOWN"),
        "quantity": quantity,
        "unit_price": unit_price,
        "gross_amount": round(quantity * unit_price, 2),
        "publish_batch_id": batch_id,
    }


def transform_records(records: list[dict], batch_id: str) -> list[dict]:
    return [transform_record(r, batch_id) for r in records]
