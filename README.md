# Mock GTM Pipeline: learn by running it

> **New here? Start with [docs/00_START_HERE.md](docs/00_START_HERE.md).** It explains the big
> picture (what a GTM Engineer does and why), the day-to-day work, the architecture, every line of
> code, the concepts, how to operate it, how to talk about it in interviews, and exercises.
>
> *This is a practice/learning project with a fake API and invented companies, built for study.*

A small but complete version of the system a GTM Engineer builds. It runs entirely on your
laptop: no API keys, no accounts. A fake API server behaves like real tools (an enrichment
provider and a CRM), including the annoying parts: **rate limits, random outages, missing data,
pagination and batch limits**.

**What it does, end to end:**
reads a messy lead list → cleans it, finds each company's domain, drops personal emails →
merges duplicates → reads what's already in the CRM (page by page) → enriches each company
and finds buying signals (surviving rate limits and outages) → scores fit + intent → assigns an
owner (keeping existing owners) → batch-upserts into the CRM (safe to re-run) → writes
"call this account today" alerts → logs a summary. Plus: a webhook receiver that ignores
duplicate events, SQL reports on the CRM, and tests.

---

## 1. Set up (Windows PowerShell, once)

```powershell
cd C:\Users\User
# unzip mock-gtm-project.zip here, then:
cd mock-gtm-project
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You'll use **three terminals**. In each new one: `cd C:\Users\User\mock-gtm-project` then
`.venv\Scripts\Activate.ps1`.

## 2. Run it (in this order)

| Terminal | Command | Leave it running? |
| --- | --- | --- |
| 1 | `python fake_api/server.py` | Yes. This is the fake enrichment API + CRM |
| 2 | `python src/run_pipeline.py` | No, it finishes in ~6 seconds |
| 2 | `python src/run_pipeline.py` again | Watch: **created 0**, everything is updated, no duplicates |
| 2 | `python src/reports.py` | SQL questions answered from the CRM |
| 3 | `python src/webhook_app.py` | Yes |
| 2 | `python src/send_test_events.py` | Watch terminal 3: event 101 handled once, then skipped |
| 2 | `pytest` | 5 tests pass |

Start fresh any time: `curl -X POST localhost:5050/admin/reset` (or restart the server after
deleting `fake_api/crm_store.json`).

## 3. What to notice in the output

| You'll see | The concept | Doc section |
| --- | --- | --- |
| `Read 8 existing CRM companies across 2 pages` | **Pagination**: the CRM gives 5 per page; the code keeps asking until there's no next page | 13 |
| `Dropped 'Random Person': personal email` | **Data quality**: a gmail address isn't a company | 20 |
| `19 -> 16 unique companies (2 duplicates merged)` | **Deduplication** by normalised domain ("https://www.peopleco.de/about" = "peopleco.de") | 12, 20 |
| `HTTP 429 ... retry 1/5 in 1.0s` | **Rate limit**: too fast, the server said wait 1s (`Retry-After`), code waited and retried | 13 |
| `HTTP 503 ... retry 1/5 in 0.6s` | **Outage**: temporary server error, retried with **backoff** | 13 |
| `No enrichment data for quillmedia.example (404)` | **Permanent error**: not retried; the run carries on | 13 |
| `score 100 tier A ... raised funding recently, hiring for security` | **Scoring** = fit + intent, with **reasons** | 21 |
| `existing owner kept` / `round-robin` | **Routing** | 21 |
| `Batch 1: 10 records -> created 8, updated 2` | **Batching** + **upsert** | 15 |
| Second run: `created=0 updated=16` | **Idempotency**: safe to re-run | 19 |
| `data/alerts.txt` | **Alerts**: who to call today and why | 21 |
| Webhook: `Duplicate event 101 skipped` | **Webhook idempotency** | 14 |
| Reports: `Duplicate domains (should be none) -> (no rows)` | **SQL** proving the CRM is clean | 16 |

## 4. Read the code in this order

1. `src/config.py`: every setting in one place (ICP, weights, teams, batch size)
2. `src/run_pipeline.py`: the whole story in one function, `main()`. Read this first to see the shape.
3. `src/extract.py`: CSV reading, pagination, enrichment with 404 handling
4. `src/http_utils.py`: **the retry function**: backoff, jitter, `Retry-After`, what's retried and what isn't
5. `src/transform.py`: domains, employees ("51-200"), industries, dedupe, and the NaN lesson
6. `src/score.py`, `src/route.py`: business rules
7. `src/load.py`: batch upsert, dry run
8. `src/alerts.py`, `src/ai_opener.py`: rep alerts; optional Claude step with validation
9. `src/webhook_app.py`, `src/send_test_events.py`: webhooks
10. `src/reports.py`: API → pandas → SQL
11. `tests/test_transform.py`: what's worth testing
12. `fake_api/server.py`: how the "real tools" misbehave (rate limit, outages, batch limit)

## 5. A real bug this project hit (a great interview story)

The first run crashed with `Out of range float values are not JSON compliant: nan`. pandas
stores a missing number as `NaN`, and `NaN` isn't valid JSON, so the CRM call failed. The fix
is `to_records()` in `transform.py`: convert `NaN` to `None` before sending data to any API.
The pipeline also overwrote a CRM company's name ("Opal Analytics AG" → "Opal Analytics"); the fix
is **field ownership**: the CRM owns the name, the pipeline only writes the fields it owns.

## 6. Break it on purpose (this is how you learn)

Change one thing, re-run, explain what happened out loud. Put it back after.

1. **Harsher rate limit:** in `fake_api/server.py` set `RATE_LIMIT = 2`, restart the server, run. More 429s; still finishes.
2. **Bad outage:** set `OUTAGE_CHANCE = 0.6`. Some calls give up after 5 tries: see `Failed on ...` and the run still completes.
3. **Too-big batch:** in `src/config.py` set `BATCH_SIZE = 20`. You get HTTP 400, **not retried**. Why is that correct?
4. **Dry run:** `python src/run_pipeline.py --dry-run`. Everything except the CRM write.
5. **New lead:** add a row to `data/new_leads.csv`, run again: `created=1`.
6. **Change the ICP:** add `"Retail"` to `TARGET_INDUSTRIES`. Who moves tier?
7. **Remove the retry:** make `max_tries=1` in `http_utils.py`. What breaks, and how often?
8. **Claude step (optional):** put `ANTHROPIC_API_KEY=...` in a `.env` file and run with `--ai`. Openers appear in `data/alerts.txt`.

## 7. Explain it in 2 minutes (practise out loud)

"The pipeline reads a lead list and the existing CRM, finds each company's domain, drops
non-companies and merges duplicates. It enriches each company through an API that is
rate-limited, so every call goes through a retry function with exponential backoff that respects
Retry-After and doesn't retry permanent errors. It scores fit plus intent with reasons,
assigns owners without stealing existing accounts, and batch-upserts into the CRM on the domain,
so re-running never creates duplicates. Tier-A accounts generate an alert telling the owner
why to call today. It logs a summary every run, alerts on failure, and the decision logic is
unit-tested."

## 8. Next: build your own (Project 2)

After learning the concepts (doc sections 9–22), build the **practice take-home in section 26**
yourself, from an empty folder, with real APIs: real HubSpot (service key) instead of the fake CRM,
and real YouTube or Claude data. Use this project only as a reference, not a template to copy.
