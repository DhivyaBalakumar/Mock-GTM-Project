"""
EXTRACT: get raw data from each source.
  Source 1: a CSV file of new leads.
  Source 2: the CRM API (what we already have), read page by page (PAGINATION).
  Source 3: the enrichment API (missing facts + buying signals), one call per domain.
"""

import logging

import pandas as pd
import requests

from config import API_BASE, LEADS_FILE
from http_utils import request_with_retry

log = logging.getLogger("extract")


def read_leads():
    df = pd.read_csv(LEADS_FILE, dtype=str)           # read everything as text; we convert later
    log.info("Read %d raw leads from %s", len(df), LEADS_FILE)
    return df


def get_all_crm_companies():
    """The CRM returns at most 5 companies per page. Keep asking until there is no next page."""
    url = f"{API_BASE}/crm/companies"
    params = {"limit": 5}
    companies, pages = [], 0
    while True:
        data = request_with_retry("GET", url, params=params)
        companies.extend(data.get("results", []))
        pages += 1
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
        params["after"] = after
    log.info("Read %d existing CRM companies across %d pages", len(companies), pages)
    return companies


def enrich(domain):
    """Return enrichment data for a domain, or None if the provider doesn't know it (404)."""
    try:
        return request_with_retry("GET", f"{API_BASE}/enrich", params={"domain": domain})
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            log.info("No enrichment data for %s (404) - keeping what we have", domain)
            return None
        raise
