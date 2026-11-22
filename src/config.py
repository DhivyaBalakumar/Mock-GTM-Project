"""
All settings live here, in one place. Changing a setting should never mean editing logic.
"""

API_BASE = "http://localhost:5050"          # the fake API server (fake_api/server.py)
LEADS_FILE = "data/new_leads.csv"           # source 1: a CSV export of new leads
ALERTS_FILE = "data/alerts.txt"             # where "call this account today" alerts are written
LOG_FILE = "data/pipeline.log"

BATCH_SIZE = 10                             # the CRM accepts at most 10 records per batch call

# Personal email providers: a lead with only a gmail address is not a company
PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "gmx.de"}

# ---- ICP (Ideal Customer Profile) used for scoring
TARGET_INDUSTRIES = {"Software", "Fintech", "Healthtech"}
TARGET_COUNTRIES = {"DE", "AT", "CH", "NL", "BE", "LU"}     # DACH + Benelux
SIZE_MIN, SIZE_MAX = 20, 500

# ---- Scoring weights (fit max 60 + intent max 40 = 100)
W_SIZE, W_INDUSTRY, W_COUNTRY = 25, 20, 15
W_FUNDING, W_HIRING = 20, 20
TIER_A, TIER_B = 75, 50

# ---- Routing: who gets new leads (round-robin within each team)
DACH_TEAM = ["lena", "jonas"]
OTHER_TEAM = ["maria", "tom"]
NURTURE_OWNER = "nurture-queue"             # tier C leads go to marketing nurture, not a rep
