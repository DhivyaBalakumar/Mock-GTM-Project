"""
Pretend to be the CRM and send webhook events to src/webhook_app.py.
Event 101 is sent TWICE on purpose, like real CRMs sometimes do.
"""

import requests

events = [
    {"eventId": 101, "subscriptionType": "company.propertyChange", "occurredAt": 1764000000000,
     "domain": "peopleco.de", "propertyName": "deal_stage", "propertyValue": "demo_booked"},
    {"eventId": 102, "subscriptionType": "company.propertyChange", "occurredAt": 1764000005000,
     "domain": "wrenpay.example", "propertyName": "phone", "propertyValue": "+43 1 234"},
]

url = "http://localhost:5051/crm/webhook"
print("First delivery:", requests.post(url, json=events, timeout=10).status_code)
print("Duplicate delivery of event 101:", requests.post(url, json=events[:1], timeout=10).status_code)
print("Check the webhook terminal: 101 should be handled once, then skipped as a duplicate.")
