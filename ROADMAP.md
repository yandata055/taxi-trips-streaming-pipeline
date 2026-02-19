---
noteId: "90a666a00d5d11f1aab8b5fb1cd2812e"
tags: []

---

# Roadmap

Planned improvements. Status: **Planned** | **In Progress** | **Done**.

| Priority | Item | Status |
|----------|------|--------|
| 1 | Fix Glue replay job: correct `sqs_url` variable and pass DynamoDB Table resource instead of table name string | Planned |
| 2 | Add unit tests for producer utilities (`df_to_kinesis_records`, `chunked`) and Lambda validation/update logic | Planned |
| 3 | Add `scripts/`: e.g. `run_producer_local.py`, `deploy_infra.sh`, `fetch_sample_data.sh` for consistent local/CI usage | Planned |
| 4 | Fix producer typo: `zip[tuple[Dict, Any]]` to `zip(...)` and correct "strip" → "trip" in log messages | Planned |
| 5 | Document data contract (e.g. `data/taxi-trip-event-attributes.md`) and ensure Parquet paths are configurable | Planned |

See [CHANGELOG](CHANGELOG.md) for what has been shipped.
