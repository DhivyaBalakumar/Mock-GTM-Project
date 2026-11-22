"""
ALERTS: tell the right rep which account to call today, and why.
In a real company this would post to Slack; here it writes to data/alerts.txt and the log.
"""

import logging

from config import ALERTS_FILE

log = logging.getLogger("alerts")


def send_call_today_alerts(rows):
    lines = []
    for r in rows:
        if r["tier"] != "A":
            continue
        lines.append(f"@{r['owner']}: CALL TODAY -> {r['name']} ({r['domain']}), "
                     f"score {r['total_score']}. Why: {r['reasons']}.")
        if r.get("ai_opener"):
            lines.append(f"    Suggested opener: {r['ai_opener']}")
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    for line in lines:
        log.info("ALERT %s", line)
    return len([l for l in lines if l.startswith("@")])


def failure_alert(message):
    # Real version: requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    log.critical("PIPELINE FAILURE ALERT: %s", message)
