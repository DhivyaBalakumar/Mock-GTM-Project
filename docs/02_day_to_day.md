# 2. Day to day: what the work actually looks like

A realistic picture of a GTM engineer's week at a 30–50 person startup, using this project's
system as "the thing you run".

## Every morning (15–30 minutes): check the systems

1. **Did last night's runs succeed?** Open the logs (here: `data/pipeline.log`) and read the
   `SUMMARY` line of each run. Compare with normal: if the pipeline usually updates ~500 companies
   and today it updated 0, something is wrong even if nothing errored.
2. **Any failure alerts?** (Here: `PIPELINE FAILURE ALERT` in the log; at a company, a Slack
   message.) If yes, that's your first job of the day.
3. **Spot-check data quality.** Run the reports (`python src/reports.py`): duplicates should be
   zero, tier counts should look normal, every tier-A account should have an owner.
4. **Glance at the alerts reps received** (`data/alerts.txt`). Do they make sense? Would you call
   these companies?

## A typical week

| Day | What you do |
| --- | --- |
| **Monday** | Review requests from the sales team (a queue in Slack, Notion or Linear). Talk to 2–3 reps: "What wasted your time last week?" Pick the week's priorities by **impact × how often it happens ÷ effort**, and agree them with the Head of GTM. |
| **Tuesday–Wednesday** | Build. Example tasks below. Small, shippable pieces; test with a dry run on a few records first. |
| **Thursday** | QA and rollout: check routing on real leads, check enrichment fallbacks, show reps the new thing, write a short how-to. |
| **Friday** | Measure: did last week's change help? (Meetings from alerts, speed-to-lead, data completeness.) Adjust scoring weights based on which accounts actually converted. Write a short update for the team. |

## Example requests you'll get (and how this project would handle them)

| A rep says | What's really needed | Where it lives in this project |
| --- | --- | --- |
| "I keep getting leads that aren't our customer type." | Better **scoring** / ICP rules | `src/config.py` (ICP), `src/score.py` |
| "Two of us emailed the same company." | **Deduplication** + clear **ownership** | `src/transform.py` (dedupe), `src/route.py` |
| "Inbound demo requests sit for hours." | **Real-time routing** via a **webhook** | `src/webhook_app.py` + `src/route.py` |
| "I spend an hour researching before each call." | An **AI research brief** (Claude) | `src/ai_opener.py` (a small version) |
| "Half the companies have no employee count." | **Enrichment** with fallbacks | `src/extract.py` → `enrich()` |
| "I never know when a target raises money." | **Signal** detection + **alerts** | `funding_90d` / `hiring_security` → `src/alerts.py` |
| "Can you tell me how many tier-A accounts each of us has?" | A **SQL report** | `src/reports.py` |

Notice: reps describe **symptoms**. Your job is to find the **root cause** and fix that. Twenty
requests often point to one bottleneck.

## A bad day: something breaks (realistic incident)

**08:40** Morning check: the overnight run's summary says `CRM created=0 updated=0`.
**08:45** Read the log: hundreds of `HTTP 429` lines, then `Gave up after 5 tries`.
**08:55** Root cause: marketing imported 3,000 new leads yesterday, so the run made 10x more
enrichment calls and blew through the provider's rate limit.
**09:30** Fix: lower the request rate (throttle), make sure CRM writes use batch calls, only enrich
companies that are new or older than 90 days. Re-run with `--dry-run` on 50 records, then for real.
**10:15** Verify: summary looks normal, reports show no duplicates, alerts went out.
**10:30** Write it up in five lines: what broke, root cause, fix, how you'll prevent it (an alert
when the run's update count drops below normal). Post it to the team.

That write-up is what "investigate problems, find the root cause, ship the fix and document it so
nothing depends on one person" means.

## How you spend your time, roughly

- 40% building new things (pipelines, automations, AI helpers)
- 20% keeping existing systems healthy (monitoring, fixing, data quality)
- 20% talking to reps and the Head of GTM (finding problems, showing what you built)
- 10% measuring and tuning (scores, routing, alerts)
- 10% writing (docs, runbooks, updates)

## The skills each part uses

| Activity | Skills |
| --- | --- |
| Pulling and cleaning data | Python, pandas, APIs, JSON |
| Keeping the CRM right | CRM data model, upserts, field ownership |
| Reacting in real time | Webhooks, routing logic |
| Not breaking | Retries, rate limits, logging, tests, idempotency |
| Answering questions | SQL |
| AI helpers | Claude API, prompt design, validation, guardrails |
| Finding the right problem | Talking to salespeople, GTM vocabulary, prioritising |

Next: [03_architecture.md](03_architecture.md)
