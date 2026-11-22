"""
TRANSFORM: turn messy raw leads into clean, unique companies.

These are "pure functions": they only use their inputs and return a result, with no API calls
or files. That makes them easy to test (see tests/test_transform.py).
"""

from urllib.parse import urlparse

import pandas as pd

from config import PERSONAL_DOMAINS

INDUSTRY_MAP = {"saas": "Software", "software": "Software", "fintech": "Fintech",
                "healthtech": "Healthtech", "food & beverage": "Food & Beverage", "f&b": "Food & Beverage"}


def normalize_domain(value):
    """'https://www.PeopleCo.de/about' or 'anna@peopleco.de' -> 'peopleco.de'."""
    if not isinstance(value, str) or not value.strip():
        return ""
    value = value.strip().lower()
    if "@" in value:                                   # an email: keep the part after @
        value = value.split("@", 1)[1]
    if "://" not in value:                             # urlparse needs a scheme to find the host
        value = "http://" + value
    host = urlparse(value).netloc
    return host[4:] if host.startswith("www.") else host


def parse_employees(value):
    """'45' -> 45, '51-200' -> 125 (midpoint), 'abc' or blank -> None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    if "-" in text:
        low, _, high = text.partition("-")
        if low.strip().isdigit() and high.strip().isdigit():
            return (int(low) + int(high)) // 2
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def normalize_industry(value):
    if not isinstance(value, str) or not value.strip():
        return ""
    return INDUSTRY_MAP.get(value.strip().lower(), value.strip().title())


def clean_leads(df):
    """Add a domain to every lead, standardise fields, drop leads that aren't companies."""
    df = df.copy()
    # Prefer the website; fall back to the email's domain when the website is missing
    df["domain"] = [normalize_domain(w) or normalize_domain(e)
                    for w, e in zip(df["website"], df["contact_email"])]
    df["employees"] = df["employees"].apply(parse_employees)
    df["industry"] = df["industry"].apply(normalize_industry)
    df["country"] = df["country"].fillna("").str.strip().str.upper()
    df["name"] = df["name"].fillna("").str.strip()

    personal = df["domain"].isin(PERSONAL_DOMAINS)
    no_domain = df["domain"] == ""
    dropped = df[personal | no_domain]
    return df[~(personal | no_domain)], dropped


def to_records(df):
    """DataFrame -> list of plain dictionaries, ready for APIs.

    Lesson learned the hard way: pandas stores missing numbers as NaN ("not a number"),
    and NaN is NOT valid JSON, so sending it to an API crashes. Convert NaN to None,
    and whole-number floats like 45.0 back to int 45.
    """
    records = []
    for rec in df.to_dict(orient="records"):
        clean = {}
        for k, v in rec.items():
            if isinstance(v, float) and pd.isna(v):
                v = None
            elif isinstance(v, float) and v.is_integer():
                v = int(v)
            clean[k] = v
        records.append(clean)
    return records


def dedupe(df):
    """Keep ONE row per domain: the most complete one (most filled-in fields)."""
    df = df.copy()
    df["_filled"] = df.notna().sum(axis=1) + (df.astype(str) != "").sum(axis=1)
    df = df.sort_values("_filled", ascending=False).drop_duplicates(subset="domain", keep="first")
    return df.drop(columns="_filled").sort_values("name").reset_index(drop=True)
