"""
A FAKE API SERVER that behaves like the real tools a GTM engineer uses.

It pretends to be two services at once:
  1. An ENRICHMENT API (like Clay or Apollo): give it a domain, it returns company facts.
  2. A CRM API (like HubSpot): list companies page by page, and batch-upsert companies.

It also behaves badly ON PURPOSE, the way real APIs do:
  - RATE LIMIT: only 5 requests per second. Go faster and you get HTTP 429 + "Retry-After".
  - RANDOM OUTAGES: about 1 in 20 requests fails with HTTP 503 (server unavailable).
  - UNKNOWN COMPANIES: enrichment returns 404 for domains it doesn't know.

Run it in its own terminal and leave it running:
    python fake_api/server.py
"""

import json
import os
import random
import threading
import time
from collections import deque

from flask import Flask, jsonify, request

app = Flask(__name__)
HERE = os.path.dirname(os.path.abspath(__file__))
STORE_FILE = os.path.join(HERE, "crm_store.json")

RATE_LIMIT = 5          # max requests...
RATE_WINDOW = 1.0       # ...per this many seconds
OUTAGE_CHANCE = 0.05    # 5% of requests fail with 503
MAX_BATCH = 10          # batch upsert accepts at most 10 records per call
PAGE_SIZE_MAX = 5       # list endpoint returns at most 5 records per page (to force pagination)

_lock = threading.Lock()
_recent = deque()       # timestamps of recent requests, for the rate limit

# ---------------------------------------------------------------- enrichment "database"
ENRICHMENT = {
    "peopleco.de":           {"employees": 48,  "industry": "Software",       "funding_90d": True,  "hiring_security": True},
    "kestrelfin.example":    {"employees": 130, "industry": "Fintech",        "funding_90d": False, "hiring_security": True},
    "lumenhealth.example":   {"employees": 140, "industry": "Healthtech",     "funding_90d": True,  "hiring_security": False},
    "verdekitchen.example":  {"employees": 18,  "industry": "Food & Beverage","funding_90d": False, "hiring_security": False},
    "emberlabs.example":     {"employees": 16,  "industry": "Software",       "funding_90d": False, "hiring_security": False},
    "halcyonrealty.example": {"employees": 30,  "industry": "Real Estate",    "funding_90d": False, "hiring_security": False},
    "opalanalytics.example": {"employees": 250, "industry": "Software",       "funding_90d": False, "hiring_security": True},
    "northwind.example":     {"employees": 620, "industry": "Logistics",      "funding_90d": False, "hiring_security": False},
    "cobaltbay.example":     {"employees": 11,  "industry": "Software",       "funding_90d": True,  "hiring_security": False},
    "granitepeak.example":   {"employees": 85,  "industry": "Software",       "funding_90d": False, "hiring_security": True},
    "saffronretail.example": {"employees": 50,  "industry": "Retail",         "funding_90d": False, "hiring_security": False},
    "tidewatersec.example":  {"employees": 78,  "industry": "Software",       "funding_90d": True,  "hiring_security": True},
    "wrenpay.example":       {"employees": 300, "industry": "Fintech",        "funding_90d": True,  "hiring_security": False},
    "marigoldhr.example":    {"employees": 24,  "industry": "Software",       "funding_90d": False, "hiring_security": False},
    "bluestone.example":     {"employees": 160, "industry": "Software",       "funding_90d": False, "hiring_security": True},
    # quillmedia.example is deliberately missing -> 404
}

# ---------------------------------------------------------------- CRM storage
SEED = [  # companies already in the "CRM" before your pipeline runs
    {"domain": "opalanalytics.example", "name": "Opal Analytics AG", "owner": "lena"},
    {"domain": "northwind.example",     "name": "Northwind Logistics", "owner": "tom"},
    {"domain": "brightforge.example",   "name": "Brightforge", "owner": "maria"},
    {"domain": "harbourline.example",   "name": "Harbourline", "owner": "jonas"},
    {"domain": "solvia.example",        "name": "Solvia", "owner": "lena"},
    {"domain": "pinecrest.example",     "name": "Pinecrest Data", "owner": "tom"},
    {"domain": "corvex.example",        "name": "Corvex", "owner": "maria"},
    {"domain": "altamira.example",      "name": "Altamira Systems", "owner": "jonas"},
]


def _load_store():
    if os.path.exists(STORE_FILE):
        with open(STORE_FILE, encoding="utf-8") as f:
            return json.load(f)
    store = {}
    for i, c in enumerate(SEED, start=1):
        store[c["domain"]] = {"id": str(i), **c}
    return store


STORE = _load_store()


def _save_store():
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(STORE, f, indent=2)


# ---------------------------------------------------------------- misbehaviour, applied to every request
@app.before_request
def misbehave():
    if request.path.startswith("/admin"):
        return None
    now = time.time()
    with _lock:
        while _recent and now - _recent[0] > RATE_WINDOW:
            _recent.popleft()
        if len(_recent) >= RATE_LIMIT:
            resp = jsonify({"error": "rate limit exceeded", "limit": f"{RATE_LIMIT} per {RATE_WINDOW}s"})
            resp.status_code = 429
            resp.headers["Retry-After"] = "1"
            return resp
        _recent.append(now)
    if random.random() < OUTAGE_CHANCE:
        return jsonify({"error": "service temporarily unavailable"}), 503
    return None


# ---------------------------------------------------------------- enrichment API
@app.get("/enrich")
def enrich():
    domain = (request.args.get("domain") or "").lower()
    if not domain:
        return jsonify({"error": "domain is required"}), 400
    data = ENRICHMENT.get(domain)
    if data is None:
        return jsonify({"error": f"no data for {domain}"}), 404
    return jsonify({"domain": domain, **data})


# ---------------------------------------------------------------- CRM API
@app.get("/crm/companies")
def list_companies():
    limit = min(int(request.args.get("limit", PAGE_SIZE_MAX)), PAGE_SIZE_MAX)
    after = int(request.args.get("after", 0))
    records = sorted(STORE.values(), key=lambda c: int(c["id"]))
    page = records[after:after + limit]
    body = {"results": page}
    if after + limit < len(records):
        body["paging"] = {"next": {"after": str(after + limit)}}
    return jsonify(body)


@app.post("/crm/companies/batch/upsert")
def batch_upsert():
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", [])
    if not inputs:
        return jsonify({"error": "inputs is required"}), 400
    if len(inputs) > MAX_BATCH:
        return jsonify({"error": f"max {MAX_BATCH} records per batch, got {len(inputs)}"}), 400
    created = updated = 0
    with _lock:
        for item in inputs:
            if item.get("idProperty") != "domain" or not item.get("id"):
                return jsonify({"error": "each input needs idProperty='domain' and an id"}), 400
            key = item["id"].lower()
            props = {k: v for k, v in (item.get("properties") or {}).items()
                     if v not in (None, "")}          # never overwrite good data with blanks
            if key in STORE:
                STORE[key].update(props)
                updated += 1
            else:
                new_id = str(max(int(c["id"]) for c in STORE.values()) + 1) if STORE else "1"
                STORE[key] = {"id": new_id, "domain": key, **props}
                created += 1
        _save_store()
    return jsonify({"created": created, "updated": updated})


# ---------------------------------------------------------------- admin helpers (no rate limit)
@app.post("/admin/reset")
def reset():
    global STORE
    with _lock:
        if os.path.exists(STORE_FILE):
            os.remove(STORE_FILE)
        STORE = _load_store()
    return jsonify({"ok": True, "companies": len(STORE)})


@app.get("/admin/count")
def count():
    return jsonify({"companies": len(STORE)})


if __name__ == "__main__":
    print(f"Fake API running on http://localhost:5050  (rate limit {RATE_LIMIT}/{RATE_WINDOW}s, "
          f"{int(OUTAGE_CHANCE * 100)}% random 503s, {len(STORE)} companies in CRM)")
    app.run(port=5050, threaded=True)
