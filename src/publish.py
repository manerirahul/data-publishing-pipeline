"""Publish stage: write the dataset, the manifest, and the DQ report.

The manifest is the contract with downstream consumers: it states exactly
how many records were published, how many were quarantined and why, and a
SHA-256 checksum of the published file so a consumer can verify the load
matches what was published.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone

PUBLISH_FIELDS = [
    "order_id", "customer_id", "order_date", "state", "status",
    "quantity", "unit_price", "gross_amount", "publish_batch_id",
]


def _write_csv(path: str, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def publish(valid: list[dict], rejects: list[dict], rule_counts: dict[str, int],
            source_name: str, batch_id: str, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)

    published_path = os.path.join(out_dir, "published_orders.csv")
    _write_csv(published_path, valid, PUBLISH_FIELDS)

    rejects_path = os.path.join(out_dir, "rejects.csv")
    reject_fields = (list(rejects[0].keys()) if rejects else
                     ["order_id", "reject_reason", "_source_row"])
    _write_csv(rejects_path, rejects, reject_fields)

    manifest = {
        "batch_id": batch_id,
        "source_file": source_name,
        "published_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records_in": len(valid) + len(rejects),
        "records_published": len(valid),
        "records_rejected": len(rejects),
        "rejects_by_rule": rule_counts,
        "published_file": os.path.basename(published_path),
        "published_sha256": _sha256(published_path),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)

    report = [
        f"# Data Quality Report — batch {batch_id}",
        "",
        f"- Source file: {source_name}",
        f"- Records in: {manifest['records_in']}",
        f"- Published: {manifest['records_published']}",
        f"- Rejected (quarantined): {manifest['records_rejected']}",
        "",
        "## Rejects by rule",
        "",
    ]
    if rule_counts:
        for code, count in sorted(rule_counts.items(), key=lambda kv: -kv[1]):
            report.append(f"- {code}: {count}")
    else:
        report.append("- None — all records passed every gate.")
    report += ["", "Rejected records are preserved in `rejects.csv` with a",
               "reason code per record for source-system follow-up.", ""]
    with open(os.path.join(out_dir, "dq_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(report))

    return manifest
