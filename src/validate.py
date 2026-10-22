"""Validation stage: apply the configured data-quality gates to raw records.

Every record is checked against every rule. A record that fails any rule is
quarantined (returned in the rejects list) with a machine-readable reason
code per failed rule, so source owners can fix data at the origin.
"""
from __future__ import annotations

import re
from datetime import datetime


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def validate_records(records: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    """Split records into (valid, rejects). Rejects carry `reject_reason`."""
    rules = config["validation"]
    required = rules.get("required_fields", [])
    numeric_ranges = rules.get("numeric_ranges", {})
    domains = rules.get("domains", {})
    date_fields = rules.get("date_fields", {})
    key_fields = rules.get("key_fields", [])

    valid: list[dict] = []
    rejects: list[dict] = []
    seen_keys: dict[tuple, int] = {}

    for row_no, rec in enumerate(records, start=2):  # +1 header, 1-based
        reasons: list[str] = []

        for field in required:
            if rec.get(field, "") is None or str(rec.get(field, "")).strip() == "":
                reasons.append(f"MISSING_REQUIRED:{field}")

        for field, (lo, hi) in numeric_ranges.items():
            value = str(rec.get(field, "")).strip()
            if value == "":
                continue
            if not _is_number(value):
                reasons.append(f"NOT_NUMERIC:{field}")
            elif not (lo <= float(value) <= hi):
                reasons.append(f"OUT_OF_RANGE:{field}={value}")

        for field, allowed in domains.items():
            value = str(rec.get(field, "")).strip().upper()
            if value and value not in {a.upper() for a in allowed}:
                reasons.append(f"DOMAIN_VIOLATION:{field}={value}")

        for field, fmt in date_fields.items():
            value = str(rec.get(field, "")).strip()
            if value:
                try:
                    datetime.strptime(value, fmt)
                except ValueError:
                    reasons.append(f"BAD_DATE:{field}={value}")

        if key_fields:
            key = tuple(str(rec.get(f, "")).strip() for f in key_fields)
            if all(key):
                if key in seen_keys:
                    reasons.append(f"DUPLICATE_KEY:first_seen_row_{seen_keys[key]}")
                else:
                    seen_keys[key] = row_no

        if reasons:
            bad = dict(rec)
            bad["reject_reason"] = ";".join(reasons)
            bad["_source_row"] = row_no
            rejects.append(bad)
        else:
            valid.append(rec)

    return valid, rejects


def rule_summary(rejects: list[dict]) -> dict[str, int]:
    """Count rejects per rule code for the DQ report."""
    counts: dict[str, int] = {}
    for rec in rejects:
        for reason in rec.get("reject_reason", "").split(";"):
            code = reason.split(":")[0]
            if code:
                counts[code] = counts.get(code, 0) + 1
    return counts
