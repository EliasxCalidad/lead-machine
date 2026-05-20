"""
Email Finder: visits each lead's website and extracts an email address.
Fast and minimal — no PageSpeed, no full analysis, just email extraction.
"""

import re
import time
import logging
import requests
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY, DELAY_BETWEEN_REQUESTS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

SKIP_EMAILS = [
    "example", "test", "noreply", "wordpress", "woocommerce",
    "schema.org", "sentry", "jquery", "google", "w3.org",
    "domain.com", "yourdomain", "email.com", "skatteverket",
    "placeholder", "your@", "info@example", "name@",
]


def fetch_emails_from_url(url: str) -> str | None:
    """Fetch a webpage and extract the first business email found."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html)
    for email in emails:
        if not any(s in email.lower() for s in SKIP_EMAILS):
            return email.lower()
    return None


# Samma lista som i ai_processor — bolag som köper leads
TARGET_KEYWORDS = [
    "callcenter", "telemarketing", "contact center", "kontaktcenter",
    "försäkring", "mäklare", "fastighetsmäklare",
    "finans", "lån", "kredit", "investering", "bank",
    "rekrytering", "bemanning",
    "larm", "säkerhetsbolag",
    "solcell", "energi", "elbolag",
    "telecom", "tele",
    "bilhandel", "billeasing", "bilförsäljning",
    "sales", "försäljning",
]


BIG_COMPANY_SKIP = [
    "nordea", "swedbank", "handelsbanken", "seb ", "folksam",
    "if försäkring", "trygg-hansa", "länsförsäkringar", "skandia",
    "alecta", "afa ", "amf ", "klarna", "ica bank", "danske bank",
    "jp morgan", "deutsche bank", "blackrock", "ubs ", "nasdaq",
    "carnegie", "bank of america", "tele2", "telia", "telenor",
    "finansinspektionen", "skatteverket", "riksbanken",
    "centerpartiet", "socialdemokraterna",
]


def is_relevant(company_name: str, category: str) -> bool:
    name = company_name.lower()
    text = (name + " " + category.lower())
    if not any(kw in text for kw in TARGET_KEYWORDS):
        return False
    if any(big in name for big in BIG_COMPANY_SKIP):
        return False
    return True


def run_email_finder(limit: int = 500) -> int:
    """
    Loop through pending leads with relevant category that have a website but no email.
    Visits the site, extracts email, saves it.
    Returns number of emails found.
    """
    result = (
        supabase.table("leads")
        .select("id, company_name, website_url, category")
        .eq("status", "pending")
        .not_.is_("website_url", "null")
        .neq("website_url", "")
        .is_("email", "null")
        .limit(limit * 5)  # hämta fler och filtrera
        .execute()
    )

    # Filtrera till rätt målgrupp
    all_leads = result.data
    leads = [l for l in all_leads if is_relevant(l.get("company_name",""), l.get("category",""))][:limit]
    skipped = len(all_leads) - len(leads)
    if skipped:
        log.info(f"  (Skippade {skipped} leads med fel kategori)")
    leads = result.data
    log.info(f"Finding emails for {len(leads)} leads...")

    found = 0
    for lead in leads:
        url = lead.get("website_url", "")
        name = lead.get("company_name", "")
        lead_id = lead["id"]

        email = fetch_emails_from_url(url)
        if email:
            supabase.table("leads").update({"email": email}).eq("id", lead_id).execute()
            log.info(f"  ✓ {name}: {email}")
            found += 1
        else:
            log.debug(f"  - {name}: no email found")

        time.sleep(0.5)

    log.info(f"Email finder done: {found}/{len(leads)} emails found")
    return found


if __name__ == "__main__":
    run_email_finder()
