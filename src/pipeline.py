"""Data publishing pipeline — orchestrator.

Usage:
    python src/pipeline.py [--config config/publish_config.json]

Reads the raw extract named in the config, runs the validation gates,
transforms the survivors to the publish schema, and publishes the dataset
with a manifest and DQ report.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate import validate_records, rule_summary
from transform import transform_records
from publish import publish


def main() -> int:
    parser = argparse.ArgumentParser(description="Data publishing pipeline")
    parser.add_argument("--config", default="config/publish_config.json")
    args = parser.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, args.config), encoding="utf-8") as fh:
        config = json.load(fh)

    source_path = os.path.join(root, config["source_file"])
    with open(source_path, newline="", encoding="utf-8") as fh:
        records = list(csv.DictReader(fh))

    batch_id = "BATCH-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    valid, rejects = validate_records(records, config)
    published = transform_records(valid, batch_id)
    manifest = publish(
        published, rejects, rule_summary(rejects),
        source_name=os.path.basename(source_path),
        batch_id=batch_id,
        out_dir=os.path.join(root, config.get("output_dir", "output")),
    )

    print(f"Batch {batch_id}: {manifest['records_in']} in, "
          f"{manifest['records_published']} published, "
          f"{manifest['records_rejected']} rejected")
    print(f"Manifest + DQ report written to {config.get('output_dir', 'output')}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
