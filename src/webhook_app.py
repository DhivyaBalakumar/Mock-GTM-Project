"""
WEBHOOK RECEIVER: the CRM calls this URL the moment something changes.

Run it:                python src/webhook_app.py
Send it test events:   python src/send_test_events.py   (in another terminal)

What it demonstrates:
  - reply 200 fast (slow replies count as failures and get retried)
  - the same event can arrive twice -> remember event IDs and skip repeats (idempotency)
  - only react to the events you care about
"""

import logging

from flask import Flask, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s webhook  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("webhook")
app = Flask(__name__)
processed = set()            # in production: a database table, so it survives restarts


@app.post("/crm/webhook")
def crm_webhook():
    events = request.get_json(silent=True) or []
    for e in events:
        key = (e.get("eventId"), e.get("subscriptionType"), e.get("occurredAt"))
        if key in processed:
            log.info("Duplicate event %s skipped", e.get("eventId"))
            continue
        processed.add(key)
        if e.get("propertyName") == "deal_stage" and e.get("propertyValue") == "demo_booked":
            log.info("Demo booked for %s -> would notify owner and refresh enrichment now",
                     e.get("domain"))
        else:
            log.info("Event %s (%s) ignored: not one we act on", e.get("eventId"), e.get("propertyName"))
    return "", 200


if __name__ == "__main__":
    app.run(port=5051)
