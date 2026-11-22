# 1. The big picture: what a GTM engineer does and why

## The business in one paragraph

Imagine a software company that sells security-compliance automation (it helps other companies
get certificates like ISO 27001 and SOC 2). It sells through a **sales team**:

- **BDRs** (business development reps) find companies that might buy and book demo calls.
- **AEs** (account executives) run the demos and close deals.
- **Marketing** brings in inbound interest (website visits, demo requests, downloads).

Every one of those people depends on **data**: which companies to target, who to contact, what's
happening at those companies right now, and what has already happened with them.

## The problem a GTM engineer is hired to fix

At most growing companies, that data is a mess:

| What's happening | What it costs |
| --- | --- |
| Each rep keeps their own spreadsheet of targets | Two reps email the same company; good companies are missed |
| Lead lists are exported from tools and imported by hand | Duplicates, typos, wrong formats, hours of copy-paste |
| CRM records are half empty or out of date | Reps don't trust the CRM, so they keep private spreadsheets (the loop gets worse) |
| Nobody notices buying signals (a company raised money, posted a security job) | The best moment to reach out passes |
| Inbound demo requests wait hours or days for a reply | Interested buyers go cold or pick a competitor |
| Research before every call is manual | AEs spend an hour per account on Googling |

The GTM engineer's job: **replace all of that with one central, automated, reliable system**, so
that reps spend their time talking to customers instead of wrangling data.

## The system, in five layers

```
SOURCES  ->  PIPELINE  ->  CRM  ->  ACTIONS  ->  (reps close deals)
                \_____________ RELIABILITY underneath _____________/
```

1. **Sources**: where data comes from. Lead lists (CSV exports), data providers (Apollo, Clay,
   ZoomInfo) via APIs, website forms, news and job boards (signals), product usage.
2. **Pipeline**: code (Python) that **extracts** data from sources, **cleans and normalises** it,
   **deduplicates** it so each company exists once, **enriches** missing facts, and **scores**
   each company on fit and intent.
3. **CRM** (HubSpot, Salesforce): the **single source of truth**. One clean, complete, current
   record per company and person, which everyone trusts.
4. **Actions**: what turns data into rep time saved: **routing** new leads to the right rep within
   minutes, **alerts** that say "call this account today, here's why", **AI helpers** (Claude) that
   research accounts and draft emails, and outreach **sequences**.
5. **Reliability**: what makes it a system and not a script: scheduled runs, retries when APIs
   fail, logs, alerts to you when something breaks, tests, documentation.

## Where this project fits

This project is a **small but complete** version of layers 1–5:

| Layer | In this project |
| --- | --- |
| Sources | `data/new_leads.csv` (a lead export), the enrichment API, the CRM API |
| Pipeline | `src/extract.py`, `src/transform.py`, `src/score.py` |
| CRM | The fake CRM inside `fake_api/server.py` (behaves like HubSpot's API) |
| Actions | `src/route.py` (owner assignment), `src/alerts.py` (call-today alerts), `src/ai_opener.py` (Claude), `src/webhook_app.py` (react to CRM events) |
| Reliability | `src/http_utils.py` (retries), logging in `run_pipeline.py`, `--dry-run`, `tests/` |
| Analysis | `src/reports.py` (SQL questions on CRM data) |

## What "good" looks like (how the job is measured)

- **Reps spend less time on manual work**: hours saved per rep per week.
- **More pipeline comes from the systems**: meetings and deals that started with a system-generated
  lead or alert.
- **The CRM is trustworthy**: few duplicates, key fields filled, data fresh.
- **Speed**: inbound leads reach a rep in minutes.
- **Reliability**: things don't break silently; when they break, they're fixed fast and written up.
- **Adoption**: reps actually use what you built. A perfect system nobody uses is a failure.

## What it is NOT

- Not RevOps (configuring tools by clicking settings). You **write code**.
- Not data science (building ML models). You build **reliable plumbing and smart rules**.
- Not a pure software engineer who never talks to users. You **sit with salespeople**, find their
  biggest bottleneck, and build for them.

Next: [02_day_to_day.md](02_day_to_day.md)
