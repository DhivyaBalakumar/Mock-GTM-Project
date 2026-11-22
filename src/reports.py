"""
SQL REPORTS: pull everything from the CRM API into a SQL database and ask questions.
This is the "question-asker" side of the job.

    python src/reports.py
"""

import sqlite3

import pandas as pd

from extract import get_all_crm_companies

QUERIES = {
    "Companies per tier":
        "SELECT COALESCE(tier, 'not scored') AS tier, COUNT(*) AS companies "
        "FROM companies GROUP BY tier ORDER BY tier",
    "Tier A accounts per owner (who has calls to make)":
        "SELECT owner, COUNT(*) AS tier_a FROM companies WHERE tier = 'A' "
        "GROUP BY owner ORDER BY tier_a DESC",
    "Average score by country (scored companies only)":
        "SELECT country, ROUND(AVG(total_score), 1) AS avg_score, COUNT(*) AS n "
        "FROM companies WHERE total_score IS NOT NULL GROUP BY country ORDER BY avg_score DESC",
    "Top 5 accounts":
        "SELECT name, domain, total_score, tier, owner FROM companies "
        "WHERE total_score IS NOT NULL ORDER BY total_score DESC LIMIT 5",
    "Duplicate domains (should be none)":
        "SELECT LOWER(domain) AS d, COUNT(*) AS copies FROM companies "
        "GROUP BY LOWER(domain) HAVING COUNT(*) > 1",
}

if __name__ == "__main__":
    df = pd.DataFrame(get_all_crm_companies())
    con = sqlite3.connect(":memory:")                 # a temporary database in memory
    df.to_sql("companies", con, index=False)
    for title, sql in QUERIES.items():
        print(f"\n== {title} ==\n{sql}\n")
        result = pd.read_sql(sql, con)
        print(result.to_string(index=False) if len(result) else "(no rows)")
