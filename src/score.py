"""
SCORE: how good is each company for us?
  FIT    (who they are):        size, industry, country      -> max 60
  INTENT (what they're doing):  recent funding, security hiring -> max 40
Total 0-100, then a tier: A (call today), B (sequence), C (nurture).
Every score comes with REASONS, so a rep knows why.
"""

import config as c


def score_company(row):
    fit, intent, reasons = 0, 0, []
    emp = row.get("employees")
    if emp is not None and c.SIZE_MIN <= emp <= c.SIZE_MAX:
        fit += c.W_SIZE
        reasons.append(f"{emp} employees")
    if row.get("industry") in c.TARGET_INDUSTRIES:
        fit += c.W_INDUSTRY
        reasons.append(row["industry"])
    if row.get("country") in c.TARGET_COUNTRIES:
        fit += c.W_COUNTRY
        reasons.append(f"in {row['country']}")
    if row.get("funding_90d"):
        intent += c.W_FUNDING
        reasons.append("raised funding recently")
    if row.get("hiring_security"):
        intent += c.W_HIRING
        reasons.append("hiring for security")
    total = fit + intent
    tier = "A" if total >= c.TIER_A else "B" if total >= c.TIER_B else "C"
    return {"fit_score": fit, "intent_score": intent, "total_score": total,
            "tier": tier, "reasons": ", ".join(reasons)}
