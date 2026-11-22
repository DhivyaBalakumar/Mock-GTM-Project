"""
OPTIONAL: use the Claude API to write a one-line outreach opener for each tier-A account.

Runs only if you pass --ai AND have ANTHROPIC_API_KEY set (in a .env file or your environment).
Shows the must-have skill safely:
  - asks for a fixed JSON format
  - VALIDATES the answer before using it
  - falls back to nothing (never junk) if the answer is bad
"""

import json
import logging
import os

log = logging.getLogger("ai")

SYSTEM = """You write the first line of a cold email for a company that helps European software
companies get ISO 27001 and SOC 2 certified in weeks. Use ONLY the facts given.
Return ONLY JSON: {"opener": "<one sentence, max 25 words, no greeting>"}"""


def add_ai_openers(rows):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.info("AI step skipped: no ANTHROPIC_API_KEY set")
        return rows
    import anthropic                                   # only needed when this step runs
    client = anthropic.Anthropic()
    for r in rows:
        if r["tier"] != "A":
            continue
        facts = {"company": r["name"], "industry": r["industry"], "employees": r["employees"],
                 "signals": r["reasons"]}
        try:
            msg = client.messages.create(model="claude-haiku-5-5", max_tokens=120, system=SYSTEM,
                                         messages=[{"role": "user", "content": json.dumps(facts)}])
            data = json.loads(msg.content[0].text.strip())
            opener = data.get("opener", "")
            if isinstance(opener, str) and 0 < len(opener.split()) <= 30:
                r["ai_opener"] = opener
            else:
                log.warning("AI answer failed validation for %s", r["domain"])
        except Exception as e:                         # bad JSON, API error: skip, never crash
            log.warning("AI step failed for %s: %s", r["domain"], e)
    return rows
