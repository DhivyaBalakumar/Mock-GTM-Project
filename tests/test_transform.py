"""
Tests for the logic that DECIDES things. Run from the project folder with:  pytest
"""

import pandas as pd

from score import score_company
from transform import clean_leads, dedupe, normalize_domain, parse_employees


def test_normalize_domain_handles_urls_and_emails():
    assert normalize_domain("https://www.PeopleCo.de/about") == "peopleco.de"
    assert normalize_domain("www.kestrelfin.example") == "kestrelfin.example"
    assert normalize_domain("anna@PeopleCo.de") == "peopleco.de"
    assert normalize_domain("") == ""
    assert normalize_domain(None) == ""


def test_parse_employees():
    assert parse_employees("45") == 45
    assert parse_employees("51-200") == 125
    assert parse_employees("abc") is None
    assert parse_employees(None) is None


def test_personal_emails_are_dropped():
    df = pd.DataFrame([{"name": "Random", "website": None, "contact_email": "john@gmail.com",
                        "country": "DE", "employees": None, "industry": None}])
    kept, dropped = clean_leads(df)
    assert len(kept) == 0 and len(dropped) == 1


def test_dedupe_keeps_most_complete_row():
    df = pd.DataFrame([
        {"name": "Peopleco", "domain": "peopleco.de", "employees": None, "industry": ""},
        {"name": "PeopleCo GmbH", "domain": "peopleco.de", "employees": 45, "industry": "Software"},
    ])
    out = dedupe(df)
    assert len(out) == 1 and out.iloc[0]["employees"] == 45


def test_score_boundaries():
    base = {"industry": "Software", "country": "DE", "funding_90d": False, "hiring_security": False}
    assert score_company({**base, "employees": 20})["fit_score"] == 60       # 20 is inside the ICP
    assert score_company({**base, "employees": 19})["fit_score"] == 35       # 19 is outside
    top = score_company({**base, "employees": 100, "funding_90d": True, "hiring_security": True})
    assert top["total_score"] == 100 and top["tier"] == "A"
