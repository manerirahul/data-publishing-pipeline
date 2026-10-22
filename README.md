# Data Publishing Pipeline

An end-to-end Python pipeline that takes raw operational data records, runs them
through **data-quality gates**, transforms them to a publish-ready standard, and
**publishes** them with a manifest and quality report — the same pattern used to
feed BI reporting (Power BI / Tableau) from warehouse and operational sources.

> Raw records in → validated, standardized records out → published dataset +
> manifest + DQ report. Nothing reaches the publish folder without passing the gates.

## Pipeline stages

1. **Ingest** — read raw CSV extract (orders) plus the publish config
2. **Validate** — schema checks, not-null rules, domain/range checks,
   duplicate detection, and cross-field rules; failures are quarantined
   to a rejects file with a reason code, never silently dropped
3. **Transform** — type coercion, code standardization (state codes,
   status values), derived fields (gross amount, publish batch id)
4. **Publish** — write the published dataset, a `manifest.json`
   (row counts, reject counts, SHA-256 checksum, batch id, timestamp),
   and a human-readable data-quality report

## Run it

```bash
python -m src.pipeline
# or
python src/pipeline.py --config config/publish_config.json
```

Outputs land in `output/`:

- `published_orders.csv` — clean, publish-ready records
- `rejects.csv` — quarantined records with `reject_reason`
- `manifest.json` — batch metadata and checksum for downstream verification
- `dq_report.md` — pass/fail counts per rule

## Sample data

`data/source/customer_orders_raw.csv` is synthetic and deliberately contains
defects — duplicate order ids, a negative quantity, an invalid state code,
a missing customer id, and a bad date — so the validation gates have
something real to catch.

## Layout

```
config/   publish rules (required fields, domains, ranges)
data/     synthetic source extracts
src/      validate.py · transform.py · publish.py · pipeline.py
tests/    unit tests for the validation rules
```

## Design notes

- **Standard library only** — runs anywhere Python 3.10+ runs, no installs.
- **Config-driven rules** — the gates live in `config/publish_config.json`,
  not in code, so a new dataset means a new config, not a rewrite.
- **Quarantine, don't drop** — every rejected record is preserved with a
  reason code so source-system owners can fix data at the origin.
- **Manifest as contract** — downstream consumers verify row counts and the
  checksum before loading, which is what makes a publish *trusted*.

In production this shape maps to S3 landing → Glue/Lambda validation →
curated zone → Athena/Redshift → BI, with the manifest driving the load.
See `aws-data-pipeline-samples` in my profile for that variant.

## License

MIT
