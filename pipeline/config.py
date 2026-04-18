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
FROM_NAME = "Elias | Calidad"
UNSUBSCRIBE_URL = "https://calidad.se/avprenumerera"

# Scraping settings
DEFAULT_CITY = "Stockholm"
DEFAULT_RADIUS_METERS = 30000  # 30km radius around Stockholm center
STOCKHOLM_LAT = 59.3293
STOCKHOLM_LNG = 18.0686

# Service business categories to target (Swedish companies selling services, not products)
TARGET_CATEGORIES = [
    "redovisningsbyrå",
    "revisionsbolag",
    "advokatbyrå",
    "juristfirma",
    "tandläkare",
    "kiropraktor",
    "psykolog",
    "fysioterapeut",
    "massageterapeut",
    "frisör",
    "skönhetssalong",
    "nagelsalong",
    "städfirma",
    "hantverkare",
    "elektriker",
    "rörmokare",
    "målare",
    "snickare",
    "bilverkstad",
    "arkitekt",
    "inredningsdesigner",
    "reklambyra",
    "pr-byrå",
    "eventbolag",
    "fotograf",
    "videoproduktion",
    "personlig tränare",
    "gym",
    "yogastudio",
    "barnpassning",
    "djurvård",
    "hundvård",
    "veterinär",
    "resebyra",
    "fastighetsmaklare",
    "konsultbolag",
    "IT-konsult",
    "försäkringsmäklare",
    "begravningsbyrå",
    "körskola",
    "musikskola",
    "tutoring",
    "restaurang",
    "café",
    "catering",
    "trädgårdsservice",
    "låssmed",
    "säkerhetsbolag",
    "flytt firma",
    "städbolag",
    "tolk",
    "översättare",
]

# Pipeline settings
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAILS_PER_DAY = 10          # Börja försiktigt — öka till 20 nästa vecka, 35 veckan efter
MAX_LEADS_PER_RUN = 50       # Per pipeline run
DELAY_BETWEEN_REQUESTS = 2   # seconds

# Calidad's offer (for AI context)
CALIDAD_OFFER = """
Calidad säljer professionella hemsidor och underhållstjänster till svenska småföretag.

ENGÅNGSPAKET:
- Liten (4 500 kr): Upp till 3 undersidor, leverans 2 veckor, mobilanpassad, kontaktformulär,
  Google Maps-synlighet, ren layout, designförslag med ändringar, sociala medier, blogg, egna bilder.
- Medium (6 500 kr): Upp till 6 undersidor, allt i Liten + SEO-anpassning, bildbank.
- Stor (9 500 kr): Upp till 10 undersidor, allt i Medium + SEO-optimering, professionell bildproduktion.

UNDERHÅLLSPAKET (månadsvis):
- Bas (299 kr/mån): Drift, SSL, WordPress-uppdateringar, spam-skydd, månadsbackup.
- Mellan (399 kr/mån): Allt i Bas + veckobackup, månadsändringar, chatbot, integrationer.
- Komplett (599 kr/mån): Allt i Mellan + daglig backup, avancerat säkerhetsskydd, fler ändringar,
  chatbot med löpande optimering.

Skräddarsydda lösningar finns också för större behov.
"""
