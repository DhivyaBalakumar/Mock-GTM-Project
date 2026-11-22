# 4. Code walkthrough: every file, every important line

Open each file next to this document. Read the file, then the explanation, then explain it back
out loud.

---

## `src/config.py`: all the settings

Every number and list the business might change lives here: the API address, file paths, batch
size, which email domains are "personal", the **ICP** (target industries, countries, size range),
the **scoring weights**, the **tier thresholds** and the **sales teams**.

**Why it matters:** when the Head of GTM says "add Retail to our ICP" or "we hired a new rep",
you change one line here, not the logic. Interviewers like hearing "config in one place".

---

## `src/run_pipeline.py`: the whole story

Read `main()` top to bottom; it's the pipeline in order.

```python
raw = read_leads()
crm = {c["domain"]: c for c in get_all_crm_companies()}
```
Reads the lead CSV, then everything already in the CRM. The CRM list becomes a **dictionary keyed
by domain**, so later "is this company already in the CRM?" is an instant lookup.

```python
cleaned, dropped = clean_leads(raw)
unique = dedupe(cleaned)
```
Adds a domain to every lead, standardises fields, drops non-companies, merges duplicates.

```python
for rec in to_records(unique):
    try:
        extra = enrich(rec["domain"]) or {}
```
Loops over each company as a plain dictionary. `enrich()` returns `None` for unknown companies,
and `or {}` turns that into an empty dictionary so the next lines don't crash.

```python
        if rec.get("employees") is None and extra.get("employees"):
            rec["employees"] = extra["employees"]
```
**Fill gaps only.** If the lead already had an employee count, keep it.

```python
        rec.update(score_company(rec))
        existing = crm.get(rec["domain"], {})
        if existing.get("name"):
            rec["name"] = existing["name"]
        rec["owner"], why = assign_owner(rec, existing.get("owner"))
```
Adds the scores. Looks up the company in the CRM. **Field ownership:** if it exists, keep the CRM's
name and owner (a person may have edited them).

```python
    except Exception as e:
        failed.append(rec["domain"])
        log.error("Failed on %s: %s", rec["domain"], e)
```
**One bad company never stops the run.** It's logged and counted.

```python
result = upsert_companies(rows, dry_run=dry_run)
alerts = send_call_today_alerts(rows)
log.info("SUMMARY ...")
```
Write to the CRM (unless dry run), send alerts, then one **summary line** so a human can see at a
glance what happened.

At the bottom, `argparse` adds the `--dry-run` and `--ai` flags, and the outer `try/except` makes
any crash log the full error, send a **failure alert**, and exit with code 1 (which schedulers
treat as "failed").

---

## `src/http_utils.py`: surviving real APIs

```python
RETRYABLE = {429, 500, 502, 503, 504}
```
Temporary problems: rate limited, or the server is struggling. Worth retrying.

```python
for attempt in range(1, max_tries + 1):
    wait = 0.5 * 2 ** (attempt - 1) + random.uniform(0, 0.25)
```
**Exponential backoff:** 0.5, 1, 2, 4, 8 seconds, plus **jitter** (a small random extra) so many
workers don't retry at the same instant.

```python
    try:
        r = requests.request(method, url, **kwargs)
    except (requests.ConnectionError, requests.Timeout) as e:
        log.warning(...)
```
Network problems (no connection, too slow) are also temporary: log and retry.

```python
    else:
        if r.status_code not in RETRYABLE:
            r.raise_for_status()
            return r.json() if r.content else None
```
`else` runs only if no exception happened. If the status isn't retryable: success (2xx) returns the
data; a permanent error (400, 401, 404) raises immediately, **without retrying**.

```python
        if r.headers.get("Retry-After"):
            wait = float(r.headers["Retry-After"])
```
If the server says how long to wait, obey it.

```python
raise RuntimeError(f"Gave up after {max_tries} tries: {method} {url}")
```
Never loop forever.

---

## `src/extract.py`: getting the data

`read_leads()` reads the CSV with `dtype=str` (everything as text) so pandas doesn't guess types
wrongly; we convert deliberately later.

`get_all_crm_companies()` is **pagination**:

```python
while True:
    data = request_with_retry("GET", url, params=params)
    companies.extend(data.get("results", []))
    after = data.get("paging", {}).get("next", {}).get("after")
    if not after:
        break
    params["after"] = after
```
Ask for a page, keep the results, look for a "next page" pointer, repeat until there isn't one.
The chained `.get(..., {})` safely reaches into nested JSON that might be missing.

`enrich()` treats **404 as normal** (the provider simply doesn't know this company) and returns
`None`; any other error is re-raised.

---

## `src/transform.py`: cleaning

`normalize_domain()`: lowercase, take the part after `@` if it's an email, add `http://` so
`urlparse` can find the host, strip `www.`. Result: `https://www.PeopleCo.de/about`,
`www.peopleco.de` and `anna@peopleco.de` all become `peopleco.de`.

`parse_employees()`: `"45"` → 45, `"51-200"` → 125 (midpoint), `"abc"` → `None`.

`clean_leads()`:
```python
df["domain"] = [normalize_domain(w) or normalize_domain(e)
                for w, e in zip(df["website"], df["contact_email"])]
```
Website first; if that's empty, the email's domain. Then drop personal-email and no-domain rows,
returning both the kept and the dropped rows (so the run can log why each was dropped).

`dedupe()`:
```python
df["_filled"] = df.notna().sum(axis=1) + (df.astype(str) != "").sum(axis=1)
df = df.sort_values("_filled", ascending=False).drop_duplicates(subset="domain", keep="first")
```
Count how filled-in each row is, sort most complete first, keep the first row per domain.
**"Sort so the best is first, then keep first"** is the standard dedupe trick.

`to_records()`: converts the table to dictionaries and fixes the **NaN problem** (pandas' "missing
number" isn't valid JSON, and crashed the first real run).

---

## `src/score.py` and `src/route.py`: business rules

`score_company()` adds points for each ICP match (fit) and each signal (intent), keeps a list of
**reasons**, and picks a tier. Simple, readable rules are a feature: the sales team can understand
and challenge them.

`assign_owner()` runs rules **in priority order**: keep an existing owner; tier C goes to nurture;
otherwise round-robin within the right team using `itertools.cycle`, which hands out names in turn
forever.

---

## `src/load.py`: writing safely

Builds one upsert input per company: `{"idProperty": "domain", "id": <domain>, "properties": {...}}`,
then sends them in **batches of 10** (the CRM's limit). Each batch is one API call; the response
says how many were created vs updated. The second run shows `created 0`: proof of **idempotency**.

---

## `src/alerts.py` and `src/ai_opener.py`

Alerts: one line per tier-A account, addressed to its owner, with the **why**. Written to a file
here; a Slack message in real life.

AI opener (optional): asks Claude for a fixed JSON format, **validates** it (a string, under 30
words), and skips the company on any problem. It never writes unvalidated AI text anywhere.

---

## `src/webhook_app.py`: reacting instantly

A tiny Flask server. For each event: build a key from its ID, type and timestamp; skip it if seen
(duplicates happen); act only on the event types you care about; reply `200` quickly.

---

## `src/reports.py`: asking questions with SQL

Reads all companies from the CRM (paginated), loads them into an in-memory SQLite database with
`df.to_sql`, and runs five queries, including one proving there are **no duplicate domains**.

---

## `fake_api/server.py`: the "real world"

Read this last. `misbehave()` runs before every request: it counts requests in the last second
(**rate limit** → 429 + `Retry-After`) and randomly fails 5% (**outages** → 503). The CRM endpoints
show **pagination** (5 per page) and **batch upsert** with a 10-record limit that **never writes
blank values**. Changing the numbers at the top is how you run the experiments in
[08_exercises.md](08_exercises.md).

---

## `tests/test_transform.py`

Tests the decisions that matter: domains from URLs and emails, employee ranges, dropping personal
emails, keeping the most complete duplicate, and **score boundaries** (20 employees is inside the
ICP, 19 is outside). Run with `pytest`.

Next: [05_concepts_explained.md](05_concepts_explained.md)
