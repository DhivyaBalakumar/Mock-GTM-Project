"""
THE PIPELINE: runs every step in order and logs what happened.

    python src/run_pipeline.py              # normal run
    python src/run_pipeline.py --dry-run    # everything except writing to the CRM
    python src/run_pipeline.py --ai         # also ask Claude for openers (needs ANTHROPIC_API_KEY)

Steps:
  1. EXTRACT   read new leads (CSV) + existing companies (CRM API, paginated)
  2. TRANSFORM clean, add domains, drop non-companies, deduplicate
  3. ENRICH    fill gaps + get buying signals (enrichment API, rate-limited)
  4. SCORE     fit + intent -> 0-100 and a tier
  5. ROUTE     assign an owner (keep existing owners)
  6. LOAD      batch-upsert into the CRM (safe to re-run)
  7. ALERT     tell owners which tier-A accounts to call today
"""

import argparse
import logging
import os
import sys
import time

import config
from alerts import failure_alert, send_call_today_alerts
from ai_opener import add_ai_openers
from extract import enrich, get_all_crm_companies, read_leads
from load import upsert_companies
from route import assign_owner
from score import score_company
from transform import clean_leads, dedupe, to_records

os.makedirs("data", exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)-8s %(message)s",
                    datefmt="%H:%M:%S",
                    handlers=[logging.FileHandler(config.LOG_FILE, encoding="utf-8"), logging.StreamHandler()])
log = logging.getLogger("pipeline")


def main(dry_run=False, use_ai=False):
    start = time.time()

    # 1. EXTRACT
    raw = read_leads()
    crm = {c["domain"]: c for c in get_all_crm_companies()}

    # 2. TRANSFORM
    cleaned, dropped = clean_leads(raw)
    for _, d in dropped.iterrows():
        log.info("Dropped '%s': %s", d["name"], "personal email" if d["domain"] else "no domain")
    unique = dedupe(cleaned)
    log.info("Cleaned %d -> %d unique companies (%d duplicates merged, %d dropped)",
             len(raw), len(unique), len(cleaned) - len(unique), len(dropped))

    # 3. ENRICH + 4. SCORE + 5. ROUTE, one company at a time
    rows, failed = [], []
    for rec in to_records(unique):
        try:
            extra = enrich(rec["domain"]) or {}
            if rec.get("employees") is None and extra.get("employees"):
                rec["employees"] = extra["employees"]        # fill gaps only; keep what we had
            if not rec.get("industry") and extra.get("industry"):
                rec["industry"] = extra["industry"]
            rec["funding_90d"] = extra.get("funding_90d", False)
            rec["hiring_security"] = extra.get("hiring_security", False)
            rec.update(score_company(rec))
            existing = crm.get(rec["domain"], {})
            if existing.get("name"):
                rec["name"] = existing["name"]               # FIELD OWNERSHIP: the CRM owns the name
            rec["owner"], why = assign_owner(rec, existing.get("owner"))
            rec["in_crm_before"] = bool(existing)
            log.info("%-24s score %3d tier %s owner %-13s (%s)",
                     rec["name"][:24], rec["total_score"], rec["tier"], rec["owner"], why)
            rows.append(rec)
        except Exception as e:                                # one bad company never stops the run
            failed.append(rec["domain"])
            log.error("Failed on %s: %s", rec["domain"], e)

    if use_ai:
        rows = add_ai_openers(rows)

    # 6. LOAD
    result = upsert_companies(rows, dry_run=dry_run)

    # 7. ALERT
    alerts = send_call_today_alerts(rows)

    tiers = {t: sum(1 for r in rows if r["tier"] == t) for t in "ABC"}
    log.info("SUMMARY raw=%d unique=%d scored=%d failed=%d | tiers A=%d B=%d C=%d | "
             "CRM created=%d updated=%d | alerts=%d | dry_run=%s | %.1fs",
             len(raw), len(unique), len(rows), len(failed), tiers["A"], tiers["B"], tiers["C"],
             result["created"], result["updated"], alerts, dry_run, time.time() - start)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="do everything except write to the CRM")
    parser.add_argument("--ai", action="store_true", help="add Claude-written openers (needs ANTHROPIC_API_KEY)")
    args = parser.parse_args()
    try:
        from dotenv import load_dotenv                       # optional: read keys from .env
        load_dotenv()
    except ImportError:
        pass
    try:
        main(dry_run=args.dry_run, use_ai=args.ai)
    except Exception as e:
        log.exception("Pipeline failed")
        failure_alert(str(e))
        sys.exit(1)
