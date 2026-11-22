"""
LOAD: write companies into the CRM safely.

UPSERT = update if the company exists, create it if not, matched on the unique "domain".
Running the pipeline twice therefore never creates duplicates (it is IDEMPOTENT).

BATCHING: the CRM accepts at most 10 records per call, so we send groups of 10.
One call with 10 records uses 1 request of our rate limit instead of 10.
"""

import datetime as dt
import logging

from config import API_BASE, BATCH_SIZE
from http_utils import request_with_retry

log = logging.getLogger("load")

FIELDS = ["name", "country", "employees", "industry", "fit_score", "intent_score",
          "total_score", "tier", "reasons", "owner"]


def upsert_companies(rows, dry_run=False):
    today = dt.date.today().isoformat()
    inputs = []
    for r in rows:
        props = {f: r.get(f) for f in FIELDS}
        props["score_updated_at"] = today
        inputs.append({"idProperty": "domain", "id": r["domain"], "properties": props})

    if dry_run:
        log.info("DRY RUN: would upsert %d companies in %d batches",
                 len(inputs), -(-len(inputs) // BATCH_SIZE))
        return {"created": 0, "updated": 0}

    totals = {"created": 0, "updated": 0}
    for i in range(0, len(inputs), BATCH_SIZE):
        batch = inputs[i:i + BATCH_SIZE]
        result = request_with_retry("POST", f"{API_BASE}/crm/companies/batch/upsert",
                                    json={"inputs": batch}, timeout=30)
        totals["created"] += result["created"]
        totals["updated"] += result["updated"]
        log.info("Batch %d: %d records -> created %d, updated %d",
                 i // BATCH_SIZE + 1, len(batch), result["created"], result["updated"])
    return totals
