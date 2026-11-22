# 8. Exercises: break it, extend it, rebuild it

Do these in order. For each: predict what will happen, make the change, run it, explain what
happened out loud, then undo the change (`git checkout -- <file>` puts a file back).

## Level 1: Break it (understand the defences)

1. **Harsher rate limit.** `fake_api/server.py`: `RATE_LIMIT = 2`. Restart the server, run the
   pipeline. Count the 429s. Why does it still finish?
2. **Serious outage.** `OUTAGE_CHANCE = 0.6`. Some companies hit `Gave up after 5 tries`. Does the
   run stop? Which line of code makes it carry on?
3. **Batch too big.** `src/config.py`: `BATCH_SIZE = 20`. You get HTTP 400. Why is it *not* retried,
   and why is that correct?
4. **No retries.** `src/http_utils.py`: call with `max_tries=1` (change the default). How often does
   the run fail now?
5. **Break dedupe.** In `dedupe()`, return `df` unchanged. Run twice. Does the CRM get duplicates?
   (Hint: the upsert on domain still protects it. That's defence in depth.)
6. **Break the upsert.** In the server's `batch_upsert`, always create a new record. Run twice, then
   run `reports.py`. Now you see why upserts matter.
7. **Remove `to_records()`.** Use `unique.to_dict(orient="records")` instead. Watch the NaN crash.
8. **Dry run.** `python src/run_pipeline.py --dry-run`. What's different in the summary?

## Level 2: Extend it (build new features)

1. **New lead.** Add a row to `data/new_leads.csv`; run; confirm `created=1`.
2. **New ICP rule.** Add `"Retail"` to `TARGET_INDUSTRIES`. Who changes tier?
3. **New signal.** Add `"new_cto": true` to a few companies in the server's `ENRICHMENT`; add it to
   `score.py` (+15 intent) with a reason. Update the test.
4. **Negative signal.** Subtract 30 points if the industry is a competitor's (invent one). Add a
   test.
5. **Score decay.** Pretend `funding_90d` is a date; give full points within 30 days, half within
   90.
6. **Slack alert.** Create a free Slack workspace and an incoming webhook URL; post alerts with
   `requests.post(url, json={"text": line})`. Keep the URL in `.env`.
7. **Contacts.** Add a `contacts` list to the server (name, title, email, domain) and a
   `/crm/contacts` endpoint; attach the most senior contact to each tier-A alert.
8. **Inbound routing via webhook.** Add an event type `form_submitted` to `send_test_events.py`;
   in `webhook_app.py`, score and route it immediately using `score.py` and `route.py`.
9. **Persistent webhook dedupe.** Store processed event keys in SQLite so restarts don't lose them.
10. **New SQL report.** "Companies with a score above 70 and no owner" (should be none). Then
    "average score per owner".
11. **Claude step.** Add your `ANTHROPIC_API_KEY` to `.env`, run with `--ai`, read the openers.
    Then break the prompt (ask for prose) and confirm validation rejects it.

## Level 3: Rebuild it for real (your own project)

From an **empty folder**, without copying, build the practice take-home from the study doc
(section 26), using:

- **Real HubSpot** (free account, a service key, a unique `domain` company property, the batch
  upsert endpoint) instead of the fake CRM.
- **A real data source** (the YouTube Data API, or a public list you assemble).
- **The Claude API** for one judgement step, with validation.
- Retries, logging, a summary line, dry run, tests, a README with design decisions.

When you can do Level 3 alone and explain every line, you're ready for the take-home and the live
coding round.
