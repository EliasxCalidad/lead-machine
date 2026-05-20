import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GOOGLE_PLACES_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
SMTP_USER = os.environ["SMTP_USER"]        # e.g. elias@calidad.se or gmail address
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]  # Gmail App Password
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
PAGESPEED_API_KEY = os.environ.get("PAGESPEED_API_KEY", GOOGLE_PLACES_API_KEY)

# Email settings
FROM_EMAIL = "elias.ivanoff@gmail.com"
FROM_NAME = "Elias | NextLead"
UNSUBSCRIBE_URL = "https://nextlead.se/avregistrera"

# Scraping settings
DEFAULT_CITY = "Stockholm"
DEFAULT_RADIUS_METERS = 30000  # 30km radius around Stockholm center
STOCKHOLM_LAT = 59.3293
STOCKHOLM_LNG = 18.0686

# Companies that buy leads — säljdrivna bolag med behov av kundkontakter
TARGET_CATEGORIES = [
    # Callcenters & telemarketing
    "callcenter Stockholm",
    "telemarketing företag Stockholm",
    "contact center Stockholm",
    "outbound sales Stockholm",
    # Försäkring
    "försäkringsbolag Stockholm",
    "försäkringsmäklare Stockholm",
    # Finans & lån
    "låneförmedlare Stockholm",
    "kreditbolag Stockholm",
    "finansbolag Stockholm",
    "investeringsrådgivare Stockholm",
    # Fastighet
    "fastighetsmäklare Stockholm",
    "mäklarfirma Stockholm",
    # Energi & sol
    "solcellsföretag Stockholm",
    "elbolag Stockholm",
    "energibolag Stockholm",
    # Bemannings- & rekryteringsbolag
    "rekryteringsföretag Stockholm",
    "bemanningsföretag Stockholm",
    # Säkerhet & larm
    "larmföretag Stockholm",
    "säkerhetsbolag Stockholm",
    # Telecom
    "telekomföretag Stockholm",
    # Bil
    "bilhandlare Stockholm",
    "billeasing Stockholm",
]

# Pipeline settings
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAILS_PER_DAY = 10          # Börja försiktigt — öka till 20 nästa vecka, 35 veckan efter
MAX_LEADS_PER_RUN = 50       # Per pipeline run
DELAY_BETWEEN_REQUESTS = 2   # seconds

# NextLead's offer (for AI context)
NEXTLEAD_OFFER = """
NextLead säljer verifierade B2B- och B2C-leads till svenska säljteam och callcenters.

Erbjudande:
- 50 gratis provleads utan krav eller bindning
- Leads matchas mot kundens exakta målgrupp och bransch
- Varje lead innehåller: namn, e-post, telefon, stad, bransch/intresse
- GDPR-säkrade och redo för direkt bearbetning
- Leverans inom 24 timmar efter beställning

Syfte med gratiserbjudandet: Låt kunden testa kvaliteten — om de konverterar blir de betalande kunder.
"""
