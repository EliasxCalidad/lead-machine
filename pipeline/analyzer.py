"""
Analyzer: fetches and analyzes each lead's website.
Checks for common issues that Calidad can fix.
"""

import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from config import (
    PAGESPEED_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
    DELAY_BETWEEN_REQUESTS
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Booking platforms — these companies have no real website of their own
BOOKING_PLATFORM_DOMAINS = [
    "bokadirekt.se",
    "timma.se",
    "treatwell.se",
    "treatwell.com",
    "fresha.com",
    "wavy.se",
    "wavy.com",
    "bokningssystem.se",
    "boka.nu",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ─── Website fetching ────────────────────────────────────────────────────────

def fetch_website(url: str) -> tuple[str | None, bool]:
    """
    Fetch website HTML. Returns (html, has_ssl).
    Always tries https first — so a site accessible via https is never
    incorrectly flagged as missing SSL just because http:// was stored.
    """
    bare = re.sub(r"^https?://", "", url)

    for scheme in ["https://", "http://"]:
        try_url = scheme + bare
        try:
            resp = requests.get(try_url, headers=HEADERS, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                has_ssl = resp.url.startswith("https://")
                return resp.text, has_ssl
        except Exception:
            continue

    return None, False


def extract_email_from_html(html: str, url: str) -> str | None:
    """Extract first business email from HTML."""
    emails = re.findall(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", html
    )
    # Filter out known non-business emails
    skip = ["example", "test", "noreply", "wordpress", "woocommerce",
            "schema.org", "sentry", "jquery", "google"]
    for email in emails:
        if not any(s in email.lower() for s in skip):
            return email.lower()
    return None


# ─── Website analysis ────────────────────────────────────────────────────────

def analyze_html(html: str, url: str) -> dict:
    """Parse HTML and extract quality signals."""
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # Meta title & description
    title_tag = soup.find("title")
    result["meta_title"] = title_tag.get_text().strip()[:200] if title_tag else None

    desc_tag = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    result["meta_description"] = (
        desc_tag.get("content", "").strip()[:300] if desc_tag else None
    )

    # Google Analytics / GTM
    html_lower = html.lower()
    result["has_google_analytics"] = (
        "google-analytics.com" in html_lower
        or "gtag(" in html_lower
        or "googletagmanager.com" in html_lower
        or "ga(" in html_lower
    )

    # Contact form
    forms = soup.find_all("form")
    has_contact = False
    for form in forms:
        form_text = form.get_text().lower()
        inputs = form.find_all("input")
        has_email_input = any(
            inp.get("type", "").lower() == "email"
            or "email" in inp.get("name", "").lower()
            or "mail" in inp.get("name", "").lower()
            for inp in inputs
        )
        if has_email_input or "kontakt" in form_text or "contact" in form_text:
            has_contact = True
            break
    result["has_contact_form"] = has_contact

    # Social media links
    social_domains = ["facebook.com", "instagram.com", "linkedin.com",
                      "twitter.com", "x.com", "tiktok.com", "youtube.com"]
    links = [a.get("href", "") for a in soup.find_all("a", href=True)]
    result["has_social_links"] = any(
        any(s in link for s in social_domains) for link in links
    )

    # Blog / news section
    blog_signals = ["blog", "nyheter", "news", "inlägg", "artiklar", "aktuellt"]
    all_links_text = " ".join(links + [soup.get_text()]).lower()
    result["has_blog"] = any(s in all_links_text for s in blog_signals)

    # Google Maps embed
    result["has_google_maps_embed"] = (
        "maps.google.com" in html or
        "google.com/maps" in html or
        "maps.googleapis.com" in html
    )

    # Copyright year
    copyright_matches = re.findall(r"©\s*(\d{4})|copyright\s+(\d{4})", html_lower)
    years = [int(y) for match in copyright_matches for y in match if y]
    result["copyright_year"] = max(years) if years else None

    # CMS detection
    cms = None
    if "wp-content" in html or "wp-includes" in html:
        cms = "WordPress"
    elif "shopify" in html_lower:
        cms = "Shopify"
    elif "squarespace" in html_lower:
        cms = "Squarespace"
    elif "wix.com" in html_lower or "wix-code" in html_lower:
        cms = "Wix"
    elif "strikingly" in html_lower:
        cms = "Strikingly"
    elif "webflow" in html_lower:
        cms = "Webflow"
    elif "joomla" in html_lower:
        cms = "Joomla"
    elif "drupal" in html_lower:
        cms = "Drupal"
    result["cms_detected"] = cms

    # Mobile viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    result["has_mobile_viewport"] = bool(viewport)

    # Is this a product site? (e-commerce signals)
    ecommerce_signals = [
        "lägg i kundvagn", "add to cart", "köp nu", "buy now",
        "checkout", "kassan", "woocommerce", "shopify", "produktkatalog"
    ]
    result["is_ecommerce"] = any(s in html_lower for s in ecommerce_signals)

    # Email on site
    result["contact_email"] = extract_email_from_html(html, url)

    return result


def get_pagespeed_score(url: str) -> tuple[int | None, int | None]:
    """Fetch PageSpeed Insights scores for mobile and desktop."""
    scores = {}
    for strategy in ["mobile", "desktop"]:
        try:
            resp = requests.get(
                PAGESPEED_URL,
                params={
                    "url": url,
                    "strategy": strategy,
                    "key": PAGESPEED_API_KEY,
                    "category": "performance",
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                score = data.get("lighthouseResult", {}).get(
                    "categories", {}
                ).get("performance", {}).get("score")
                scores[strategy] = int(score * 100) if score is not None else None
            else:
                scores[strategy] = None
        except Exception as e:
            log.debug(f"PageSpeed error ({strategy}): {e}")
            scores[strategy] = None
        time.sleep(1)

    return scores.get("mobile"), scores.get("desktop")


def build_issues_list(analysis: dict, ps_mobile: int | None, ps_desktop: int | None) -> list[str]:
    """Build a list of identified issues from analysis results."""
    issues = []

    if ps_mobile is not None and ps_mobile < 50:
        issues.append("Hemsidan laddar extremt långsamt på mobilen — de flesta besökare ger upp och lämnar")
    elif ps_mobile is not None and ps_mobile < 70:
        issues.append("Hemsidan är seg på mobilen — kunder tappar tålamodet innan de ens sett vad ni erbjuder")

    if ps_desktop is not None and ps_desktop < 60:
        issues.append("Hemsidan laddar långsamt även på dator — ger ett oprofessionellt intryck")

    if not analysis.get("has_ssl"):
        issues.append("Webbläsaren varnar besökare att sidan 'inte är säker' — många vänder direkt")

    if not analysis.get("has_mobile_viewport"):
        issues.append("Hemsidan ser trasig ut på mobilen — och de flesta söker på telefonen idag")

    if not analysis.get("has_contact_form"):
        issues.append("Det finns inget sätt att kontakta er direkt via hemsidan — kunder som vill höra av sig ger upp")

    if not analysis.get("meta_title"):
        issues.append("Hemsidan saknar en titel i Google — ni syns knappt när folk söker efter er")
    elif analysis.get("meta_title") and len(analysis["meta_title"]) < 10:
        issues.append("Hemsidans titel i Google är för kort — svårt för nya kunder att förstå vad ni gör")

    if not analysis.get("meta_description"):
        issues.append("När folk hittar er i Google syns ingen beskrivning — de klickar på konkurrenten istället")

    if not analysis.get("has_google_analytics"):
        issues.append("Ni har ingen koll på hur många som besöker hemsidan eller var de kommer ifrån")

    if not analysis.get("has_social_links"):
        issues.append("Hemsidan är inte kopplad till era sociala medier — ni missar en enkel väg att bygga förtroende")

    if not analysis.get("has_google_maps_embed"):
        issues.append("Det finns ingen karta på hemsidan — kunder som ska hitta till er får leta på egen hand")

    year = analysis.get("copyright_year")
    if year and year < 2020:
        issues.append(f"Hemsidan ser gammal ut och har inte uppdaterats på länge — ger intrycket att ni inte är aktiva")

    cms = analysis.get("cms_detected")
    if cms in ["Wix", "Strikingly", "Weebly"]:
        issues.append(f"Hemsidan är byggd på ett gratisverktyg ({cms}) — det syns, och det begränsar vad ni kan göra")

    return issues


# ─── Main analyzer ────────────────────────────────────────────────────────────

def _save_no_website_analysis(lead_id: str, status: str):
    """Save a placeholder analysis for leads with no real website."""
    issues = [
        "Företaget har ingen egen hemsida — kunder som googlar hittar dem inte",
        "Helt beroende av bokningsplattformens regler, utseende och avgifter",
        "Ingen möjlighet att visa upp sitt arbete eller bygga förtroende online",
        "Missar alla kunder som söker på Google efter deras tjänst i närheten",
    ]
    analysis_data = {
        "lead_id": lead_id,
        "pagespeed_mobile": None,
        "pagespeed_desktop": None,
        "has_ssl": None,
        "has_contact_form": False,
        "has_google_analytics": False,
        "has_social_links": False,
        "has_blog": False,
        "has_google_maps_embed": False,
        "meta_title": None,
        "meta_description": None,
        "copyright_year": None,
        "cms_detected": None,
        "issues": issues,
        "recommended_package": "Liten (4 500 kr)",
    }
    supabase.table("analyses").insert(analysis_data).execute()
    supabase.table("leads").update({"status": status}).eq("id", lead_id).execute()


def analyze_lead(lead: dict) -> bool:
    """Analyze a single lead's website. Returns True on success."""
    lead_id = lead["id"]
    url = lead.get("website_url", "")
    name = lead.get("company_name", "")

    if not url:
        log.info(f"  {name} — ingen hemsida alls")
        _save_no_website_analysis(lead_id, "no_website")
        return True

    # Check if URL is a booking platform profile (not a real website)
    if any(domain in url.lower() for domain in BOOKING_PLATFORM_DOMAINS):
        platform = next(d for d in BOOKING_PLATFORM_DOMAINS if d in url.lower())
        log.info(f"  {name} — bara bokningsprofil ({platform})")
        _save_no_website_analysis(lead_id, "bokadirekt_only")
        return True

    log.info(f"Analyzing: {name} ({url})")

    # Mark as analyzing
    supabase.table("leads").update({"status": "analyzing"}).eq("id", lead_id).execute()

    try:
        # Fetch website
        html, has_ssl = fetch_website(url)
        if not html:
            log.warning(f"  Could not fetch {url}")
            supabase.table("leads").update({"status": "fetch_error"}).eq("id", lead_id).execute()
            return False

        # Skip e-commerce sites early
        analysis = analyze_html(html, url)
        if analysis.get("is_ecommerce"):
            log.info(f"  Skipping {name} — detected as e-commerce")
            supabase.table("leads").update({"status": "skipped_ecommerce"}).eq("id", lead_id).execute()
            return False

        # Save email if found
        contact_email = analysis.get("contact_email")
        if contact_email:
            supabase.table("leads").update({"email": contact_email}).eq("id", lead_id).execute()

        # PageSpeed scores
        ps_mobile, ps_desktop = get_pagespeed_score(url)

        # Build issues list
        issues = build_issues_list(analysis, ps_mobile, ps_desktop)

        # Determine recommended package based on issues
        if len(issues) >= 6:
            recommended = "Stor (9 500 kr)"
        elif len(issues) >= 3:
            recommended = "Medium (6 500 kr)"
        else:
            recommended = "Liten (4 500 kr)"

        # Save analysis
        analysis_data = {
            "lead_id": lead_id,
            "pagespeed_mobile": ps_mobile,
            "pagespeed_desktop": ps_desktop,
            "has_ssl": has_ssl,
            "has_contact_form": analysis.get("has_contact_form", False),
            "has_google_analytics": analysis.get("has_google_analytics", False),
            "has_social_links": analysis.get("has_social_links", False),
            "has_blog": analysis.get("has_blog", False),
            "has_google_maps_embed": analysis.get("has_google_maps_embed", False),
            "meta_title": analysis.get("meta_title"),
            "meta_description": analysis.get("meta_description"),
            "copyright_year": analysis.get("copyright_year"),
            "cms_detected": analysis.get("cms_detected"),
            "issues": issues,
            "recommended_package": recommended,
        }
        supabase.table("analyses").insert(analysis_data).execute()

        # Update lead status
        supabase.table("leads").update({"status": "analyzed"}).eq("id", lead_id).execute()
        log.info(f"  ✓ {name}: {len(issues)} issues found → {recommended}")
        return True

    except Exception as e:
        log.error(f"  Error analyzing {name}: {e}")
        supabase.table("leads").update({"status": "analyze_error"}).eq("id", lead_id).execute()
        return False


def run_analyzer(limit: int = 50) -> int:
    """Analyze pending leads. Returns number successfully analyzed."""
    result = supabase.table("leads").select("*").in_("status", ["pending"]).limit(limit).execute()
    leads = result.data
    log.info(f"Analyzing {len(leads)} pending leads")

    success = 0
    for lead in leads:
        if analyze_lead(lead):
            success += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    log.info(f"Analyzer done: {success}/{len(leads)} successful")
    return success


if __name__ == "__main__":
    run_analyzer()
