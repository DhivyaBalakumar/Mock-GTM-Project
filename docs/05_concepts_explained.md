# 5. Concepts explained, using this project

Each concept: what it is in plain words, where it is in this code, and why it matters on the job.

| Concept | Plain meaning | Where in this project | Why it matters |
| --- | --- | --- | --- |
| **API** | A way for one program to ask another for data or actions over the internet | Every call to `localhost:5050` | Every tool a GTM team uses connects through APIs |
| **HTTP method** | GET reads, POST creates/sends, PATCH updates, DELETE removes | `GET /enrich`, `POST /crm/companies/batch/upsert` | You must use the right one for each action |
| **Status code** | The server's 3-digit verdict: 200 OK, 404 not found, 429 slow down, 503 unavailable | Handled in `http_utils.py` | Decides whether to continue, retry or stop |
| **JSON** | Labelled text data; becomes dictionaries and lists in Python | Every API response | APIs speak JSON |
| **Rate limit** | A cap on requests per time window | Server: 5 per second | Real APIs all have one; ignoring it crashes pipelines |
| **Retry with exponential backoff** | Wait longer after each failure, then try again | `request_with_retry` | Turns temporary failures into successes |
| **Jitter** | A small random extra wait | `random.uniform(0, 0.25)` | Stops many workers retrying at the same instant |
| **Retry-After** | The server telling you how long to wait | Header on 429 responses | Obeying it is polite and effective |
| **Temporary vs permanent errors** | 429/5xx might work later; 400/401/404 won't | `RETRYABLE` set | Retrying permanent errors wastes calls and hides bugs |
| **Timeout** | Give up on a request that takes too long | `timeout=10` | Stops a stuck server freezing your job |
| **Pagination** | Big lists come a page at a time | `get_all_crm_companies` | Without it you silently get only the first page |
| **Batching** | Many records in one request | `BATCH_SIZE = 10` | Fewer calls, stays under rate limits |
| **Normalisation** | Putting values into one consistent format | `normalize_domain`, `normalize_industry` | Required before you can compare or dedupe |
| **Deduplication / entity resolution** | Deciding which records are the same real company | `dedupe()` on domain | Duplicates are the #1 CRM complaint |
| **Unique key** | A value that identifies one real thing | Domain for companies | What makes dedupe and upserts possible |
| **Enrichment** | Filling missing facts from a data provider | `enrich()` | Leads arrive incomplete |
| **Signals / intent** | Visible events suggesting a need now | `funding_90d`, `hiring_security` | Tells reps *when* to reach out |
| **ICP** | The type of company that fits best | `config.py` | Basis of fit scoring |
| **Lead scoring** | A number for how good a lead is: fit + intent | `score.py` | Decides where reps spend time |
| **Routing** | Assigning leads to the right rep automatically | `route.py` | Speed and fairness; no lead lost |
| **Round-robin** | Handing out work in turn | `itertools.cycle` | Spreads leads evenly |
| **CRM** | The shared database of companies, contacts, deals | Fake CRM in the server | The single source of truth |
| **Upsert** | Update if exists, create if not | `batch/upsert` with `idProperty: domain` | Re-runs don't duplicate |
| **Idempotency** | Running twice = running once | Second run: `created=0` | Lets you re-run safely after any failure |
| **Field ownership** | Each field has one system allowed to set it | CRM keeps `name`, `owner` | Stops code undoing people's edits |
| **Never write blanks** | Empty values don't overwrite real ones | Server's upsert + gap-filling | Protects good data |
| **Webhook** | A system calling your URL the moment something happens | `webhook_app.py` | Real-time reactions (inbound leads) |
| **Event idempotency** | Process each event once even if sent twice | `processed` set | Webhooks do get delivered twice |
| **Logging** | Timestamped notes of what happened | Every module's `log` | How you know what happened at 3 am |
| **Summary line** | One line describing the whole run | `SUMMARY ...` | Spot problems at a glance |
| **Failure alert** | Tell a human when a run fails | `failure_alert()` | No silent failures |
| **Dry run** | Do everything except the final write | `--dry-run` | Safe testing on real data |
| **Pure function** | Uses only its inputs, returns a result, no side effects | `transform.py`, `score.py` | Easy to test |
| **Unit test** | Small automatic check of one piece of logic | `tests/` | Change code without fear |
| **Config** | Settings separate from logic | `config.py` | Business changes = one-line edits |
| **NaN** | pandas' "missing number"; not valid JSON | `to_records()` fix | A classic real bug |
| **SQL** | The language for asking questions of tables | `reports.py` | Answering the GTM team's questions |
| **ETL** | Extract, transform, load | The pipeline's shape | The standard pattern for data pipelines |
| **AI guardrails** | Rules that stop bad AI output being used | Validation in `ai_opener.py` | AI can be wrong; your system mustn't be |

## Three ideas to explain especially well

**1. Why idempotency is the most important property of a pipeline.** Pipelines fail halfway,
get re-run by schedulers, and get run twice by humans. If running twice creates duplicates or
double-sends alerts, every failure becomes a data-cleaning project. Upserting on a unique key makes
re-running safe, so recovery is just "run it again".

**2. Why you don't retry everything.** A 429 means "too fast, try later": retrying works. A 400
means "your request is wrong": it will fail the same way forever, and retrying just burns your rate
limit and hides the bug. Sorting errors into temporary and permanent is the core of reliable code.

**3. Why scores need reasons.** Reps ignore numbers they don't understand. "Score 100: 45
employees, Software, in DE, raised funding recently, hiring for security" tells them why to call
and what to say.

Next: [06_runbook.md](06_runbook.md)
