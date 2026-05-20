"""
Exporterar wellness-företag i Stockholm utan hemsida till CSV.
För säljare att ringa kallt.
"""

import csv
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

API_KEY = os.environ["GOOGLE_PLACES_API_KEY"]
STOCKHOLM_LAT = 59.3293
STOCKHOLM_LNG = 18.0686
RADIUS = 30000

CATEGORIES = [
    "nagelsalong",
    "frisör",
    "hårsalong",
    "skönhetssalong",
    "skönhetsklinik",
    "ansiktsbehandling",
    "hudvård",
    "hudklinik",
    "vaxning",
    "laserhårborttagning",
    "permanent makeup",
    "browbar",
    "lashstudio",
    "fransar",
    "massagesalong",
    "spa",
    "wellnessklinik",
    "yogastudio",
    "pilatesstudio",
    "kroppsvård",
    "makeupstudio",
    "hårstudio",
    "solarium",
    "skönhetsterapeut",
    "frisörsalong",
    # Stadsdelar
    "nagelsalong Södermalm",
    "frisör Södermalm",
    "skönhetssalong Södermalm",
    "nagelsalong Östermalm",
    "frisör Östermalm",
    "skönhetssalong Östermalm",
    "nagelsalong Vasastan",
    "frisör Vasastan",
    "nagelsalong Kungsholmen",
    "frisör Kungsholmen",
    "nagelsalong Sundbyberg",
    "nagelsalong Solna",
    "frisör Solna",
    "nagelsalong Nacka",
    "frisör Nacka",
    "nagelsalong Huddinge",
    "skönhetssalong Huddinge",
    "nagelsalong Haninge",
    "nagelsalong Järfälla",
    "frisör Järfälla",
    "nagelsalong Täby",
    "frisör Täby",
    "skönhetssalong Täby",
    "nagelsalong Lidingö",
    "nagelsalong Botkyrka",
    "massagesalong Södermalm",
    "massage Stockholm",
    "thaimassage Stockholm",
    "thaimassage Södermalm",
    "reflexologi Stockholm",
    "akupunktur Stockholm",
    "beauty salon Stockholm",
    "nail salon Stockholm",
    "hair salon Stockholm",
]

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def search(query, page_token=None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.websiteUri,"
            "places.nationalPhoneNumber,places.formattedAddress,"
            "places.businessStatus,nextPageToken"
        ),
    }
    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": STOCKHOLM_LAT, "longitude": STOCKHOLM_LNG},
                "radius": RADIUS,
            }
        },
        "languageCode": "sv",
        "maxResultCount": 20,
    }
    if page_token:
        body["pageToken"] = page_token
    resp = requests.post(SEARCH_URL, json=body, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    results = {}  # place_id -> data, för att undvika dubletter

    for category in CATEGORIES:
        query = f"{category} Stockholm"
        print(f"Söker: {query}...")
        try:
            data = search(query)
            places = data.get("places", [])
            page_token = data.get("nextPageToken")

            for p in places:
                pid = p.get("id")
                if not pid or pid in results:
                    continue
                if p.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue
                if p.get("websiteUri"):
                    continue  # Har hemsida — hoppa över
                phone = p.get("nationalPhoneNumber", "").strip()
                if not phone:
                    continue  # Inget telefonnummer — hoppa över
                results[pid] = {
                    "Företag": p.get("displayName", {}).get("text", ""),
                    "Telefon": phone,
                    "Adress": p.get("formattedAddress", ""),
                    "Kategori": category,
                }

            # Sida 2
            pages = 1
            while page_token and pages < 3:
                time.sleep(2)
                data = search(query, page_token=page_token)
                for p in data.get("places", []):
                    pid = p.get("id")
                    if not pid or pid in results:
                        continue
                    if p.get("businessStatus") == "CLOSED_PERMANENTLY":
                        continue
                    if p.get("websiteUri"):
                        continue
                    phone = p.get("nationalPhoneNumber", "").strip()
                    if not phone:
                        continue
                    results[pid] = {
                        "Företag": p.get("displayName", {}).get("text", ""),
                        "Telefon": phone,
                        "Adress": p.get("formattedAddress", ""),
                        "Kategori": category,
                    }
                page_token = data.get("nextPageToken")
                pages += 1

        except Exception as e:
            print(f"  Fel för {category}: {e}")

        time.sleep(1)
        print(f"  Totalt utan hemsida hittills: {len(results)}")

        if len(results) >= 150:
            break

    # Exportera till CSV
    output_path = os.path.expanduser("~/Desktop/leads_utan_hemsida.csv")
    rows = list(results.values())[:100]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Företag", "Telefon", "Adress", "Kategori"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✓ {len(rows)} leads exporterade till: {output_path}")


if __name__ == "__main__":
    main()
