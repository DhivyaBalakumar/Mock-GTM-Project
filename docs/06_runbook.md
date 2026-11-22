# 6. Runbook: operating the system

A **runbook** is the document a teammate uses to run, check and fix a system without you. Writing
one is part of the job ("document it so nothing depends on one person").

## Normal operation

| What | How | Expected |
| --- | --- | --- |
| Run the pipeline | `python src/run_pipeline.py` | Ends with a `SUMMARY` line, `failed=0` |
| Safe test run | `python src/run_pipeline.py --dry-run` | Same, but `CRM created=0 updated=0` |
| Check data quality | `python src/reports.py` | "Duplicate domains" shows no rows |
| Run tests | `pytest` | All pass |
| Reset the fake CRM | `curl -X POST localhost:5050/admin/reset` | 8 companies |

## Scheduling it (making it run by itself)

**Windows Task Scheduler:** Create Basic Task → Daily, repeat every 6 hours → Action: Start a
program → Program: `C:\Users\User\mock-gtm-project\.venv\Scripts\python.exe` → Arguments:
`src\run_pipeline.py` → Start in: `C:\Users\User\mock-gtm-project`. (The fake server must be
running too; in real life the APIs are always on.)

**Linux/Mac cron:** `0 */6 * * * cd /path/mock-gtm-project && .venv/bin/python src/run_pipeline.py`

**In a company:** GitHub Actions on a schedule, a cloud scheduler, or an orchestrator like Airflow,
with API keys stored as secrets, never in code.

## How to read the summary line

```
SUMMARY raw=19 unique=16 scored=16 failed=0 | tiers A=8 B=1 C=7 | CRM created=0 updated=16 | alerts=8 | dry_run=False | 5.6s
```

| Field | Healthy | Worry if |
| --- | --- | --- |
| `raw` vs `unique` | A few duplicates merged | `unique` is tiny: normalisation broke? |
| `failed` | 0 | Above 0: read the `Failed on` lines |
| `tiers` | Roughly stable run to run | Everything suddenly tier C: a scoring input is missing |
| `created` | New leads only | Large on a re-run: **dedupe or upsert broke** |
| `updated` | Most records | 0: the CRM write didn't happen |
| `alerts` | Some | 0 for days: thresholds or signals broken |
| time | Seconds | Minutes: heavy rate limiting, maybe a volume spike |

## Troubleshooting

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `Connection refused` on every call | The API (fake server) isn't running | Start `python fake_api/server.py` |
| Many `HTTP 429` lines, run finishes | Normal rate limiting | Nothing; that's the retry working |
| `Gave up after 5 tries` | Sustained rate limit or outage | Check the API status; lower request rate; re-run (it's idempotent) |
| `HTTP 400 ... max 10 records per batch` | `BATCH_SIZE` set above the API limit | Set it back to 10 or less |
| `HTTP 401` (real APIs) | Expired or wrong key | Rotate the key in `.env`; never retry 401 |
| Duplicates in reports | Normalisation changed, or a create-only write was added | Check `normalize_domain` and that load uses upsert |
| A company has the wrong owner | Routing rule order, or an owner changed in the CRM | Check `route.py` order; the CRM owner always wins |
| Webhook handles an event twice | Process restarted (memory set lost) | Production: store processed IDs in a database |
| `ModuleNotFoundError` | Virtual environment not active | `.venv\Scripts\Activate.ps1`, then `pip install -r requirements.txt` |
| `FileNotFoundError: data/new_leads.csv` | Running from the wrong folder | `cd` into the project folder first |

## After an incident: the five-line write-up

```
What broke:   overnight run updated 0 companies (failure alert at 02:14)
Root cause:   3,000 leads imported; enrichment calls exceeded the rate limit for 40 minutes
Fix:          throttled enrichment, only enrich new or stale companies, re-ran (idempotent)
Prevention:   alert when updated count < 50% of the 7-day average; batch size checked in tests
Owner / date: <you>, <date>
```

Next: [08_exercises.md](08_exercises.md)
