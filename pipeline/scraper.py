"""
Scraper: finds service businesses on Google Maps and saves them as leads.
Uses Google Places API (Text Search) to find companies by category + city.
"""

import time
import logging
import requests
from supabase import create_client
from config import (
    GOOGLE_PLACES_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
    TARGET_CATEGORIES, STOCKHOLM_LAT, STOCKHOLM_LNG,
    DEFAULT_RADIUS_METERS, DELAY_BETWEEN_REQUESTS, DEFAULT_CITY
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACES_DETAIL_URL = "https://places.googleapis.com/v1/places/{place_id}"


def search_places(query: str, page_token: str = None) -> dict:
    """Search Google Places API for businesses matching query."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.websiteUri,"
            "places.nationalPhoneNumber,places.formattedAddress,"
            "places.primaryTypeDisplayName,places.businessStatus,"
            "nextPageToken"
        ),
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": STOCKHOLM_LAT, "longitude": STOCKHOLM_LNG},
                "radius": DEFAULT_RADIUS_METERS,
            }
        },
        "languageCode": "sv",
        "maxResultCount": 20,
    }
    if page_token:
        body["pageToken"] = page_token

    resp = requests.post(PLACES_SEARCH_URL, json=body, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_place_email(place_id: str) -> str | None:
    """Try to fetch email from Place details (not always available)."""
    # Google Places API doesn't return emails directly.
    # We'll scrape the website for emails later in the analyzer step.
    return None


def get_existing_place_ids() -> set:
    """Fetch all place IDs already in the database to avoid duplicates."""
    result = supabase.table("leads").select("google_place_id").execute()
    return {row["google_place_id"] for row in result.data if row["google_place_id"]}


def upsert_lead(place: dict) -> bool:
    """Insert a new lead. Returns True if inserted, False if already exists."""
    place_id = place.get("id")
    if not place_id:
        return False

    name = place.get("displayName", {}).get("text", "")
    website = place.get("websiteUri", "")
    phone = place.get("nationalPhoneNumber", "")
    address = place.get("formattedAddress", "")
    category = place.get("primaryTypeDisplayName", {}).get("text", "")
    status = place.get("businessStatus", "")

    # Skip closed businesses
    if status == "CLOSED_PERMANENTLY":
        return False

    # Skip obvious e-commerce / product sites by URL patterns
    skip_domains = ["shopify", "woocommerce", "amazon", "ebay", "etsy"]
    if any(d in (website or "").lower() for d in skip_domains):
        return False

    # Skip businesses whose Google category is clearly not wellness/beauty.
    # Google returns the primary type in Swedish when languageCode=sv.
    REJECTED_CATEGORY_KEYWORDS = [
        "resebyrå", "resor", "flyg", "hotell", "logi", "vandrarhem",
        "restaurang", "café", "kafé", "bar ", "nattklubb", "pub",
        "livsmedel", "mataffär", "apotek", "tandläkare", "läkare",
        "tandvård", "sjukhus", "klinik för ", "veterinär",
        "bilverkstad", "fordonsservice", "däckservice",
        "städfirma", "städservice", "fastighets",
        "bokhandel", "blomsterhandel",
        "gym", "fitness", "crossfit",  # These sell memberships, not our target
    ]
    category_lower = (category.get("text", "") if isinstance(category, dict) else str(category)).lower()
    if any(kw in category_lower for kw in REJECTED_CATEGORY_KEYWORDS):
        log.info(f"  Skipping {name} — wrong category: {category_lower}")
        return False

    data = {
        "company_name": name,
        "website_url": website.rstrip("/"),
        "phone": phone,
        "address": address,
        "city": DEFAULT_CITY,
        "category": category,
        "google_place_id": place_id,
        "status": "pending",
    }

    try:
        supabase.table("leads").insert(data).execute()
        log.info(f"  + Added: {name} ({website})")
        return True
    except Exception as e:
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return False  # Already exists
        log.warning(f"  ! Error inserting {name}: {e}")
        return False


def scrape_category(category: str, existing_ids: set) -> int:
    """Scrape one category and return number of new leads added."""
    query = f"{category} Stockholm"
    log.info(f"Searching: {query}")
    added = 0

    try:
        data = search_places(query)
        places = data.get("places", [])

        for place in places:
            if place.get("id") in existing_ids:
                continue
            if upsert_lead(place):
                added += 1
                existing_ids.add(place.get("id"))
            time.sleep(0.3)

        # Handle pagination (up to 3 pages per category)
        next_token = data.get("nextPageToken")
        pages = 1
        while next_token and pages < 3:
            time.sleep(2)  # Required delay before using page token
            data = search_places(query, page_token=next_token)
            for place in data.get("places", []):
                if place.get("id") in existing_ids:
                    continue
                if upsert_lead(place):
                    added += 1
                    existing_ids.add(place.get("id"))
                time.sleep(0.3)
            next_token = data.get("nextPageToken")
            pages += 1

    except requests.HTTPError as e:
        log.error(f"HTTP error for {category}: {e}")
    except Exception as e:
        log.error(f"Error scraping {category}: {e}")

    return added


def run_scraper(categories: list = None, max_new_leads: int = 200) -> int:
    """
    Main scraper entry point.
    Scrapes given categories (or all) until max_new_leads are added.
    """
    if categories is None:
        categories = TARGET_CATEGORIES

    existing_ids = get_existing_place_ids()
    log.info(f"Starting scraper. Existing leads: {len(existing_ids)}")

    total_added = 0
    for category in categories:
        if total_added >= max_new_leads:
            break
        added = scrape_category(category, existing_ids)
        total_added += added
        log.info(f"  → {category}: {added} new leads (total: {total_added})")
        time.sleep(DELAY_BETWEEN_REQUESTS)

    log.info(f"Scraper done. Total new leads: {total_added}")
    return total_added


if __name__ == "__main__":
    run_scraper()
