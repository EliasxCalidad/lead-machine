"""
AI Processor: uses OpenAI to generate personalized cold emails for NextLead.
"""

import logging
from openai import OpenAI
from supabase import create_client
from config import (
    OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
    NEXTLEAD_OFFER, FROM_NAME, FROM_EMAIL
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """Du är Elias, försäljningschef på NextLead i Stockholm.
Du skriver ett kort, rakt cold email. Mailtexten ska vara SAMMA struktur varje gång — du anpassar bara hälsningsfrasen till företagsnamnet.

ABSOLUTA REGLER:
1. Skriv "jag" och "mig" — det är ett personligt mail från Elias, inte från ett bolag
2. INGEN avslutande hälsning eller "Mvh" i brödtexten — signaturen läggs till separat
3. Max 80 ord i brödtexten
4. Inga buzzwords, inget corporate-speak
5. Tonen: rak och mänsklig — inte säljig

Fast struktur (följ denna exakt):
- Rad 1: "Hej [företagsnamn],"
- Rad 2: Kort intro — jag heter Elias och är försäljningschef på NextLead. Vi hjälper företag med B2B- och B2C-leads.
- Rad 3: Vi erbjuder just nu 50 gratis leads — antingen B2B eller B2C — helt utan krav. Det är mitt sätt att visa att kvaliteten håller.
- Rad 4: Är ni nyfikna? Hör av er direkt på detta mail eller ring mig på 072 007 33 48.

Ämnesraden:
- Max 8 ord, känns som att den kommer från en bekant
- Exempel på BRA: "50 gratis leads — inga krav", "Gratis leads från NextLead", "Snabbt erbjudande om leads"
- Exempel på DÅLIGA: "Exklusivt erbjudande!", "Boost your sales pipeline"

Format:
ÄMNE: [ämnesrad]
---
[mailtext]
"""


def generate_email(
    company_name: str,
    category: str,
    **kwargs,  # absorb unused legacy params
) -> tuple[str, str]:
    """
    Generate personalized email subject + body using OpenAI.
    Returns (subject, body_text).
    """
    user_message = f"""Företag: {company_name}
Bransch/typ: {category or "säljbolag"}

Skriv ett personligt cold email på svenska till detta företag."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=400,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    full_text = response.choices[0].message.content.strip()

    # Parse subject and body
    if "ÄMNE:" in full_text and "---" in full_text:
        parts = full_text.split("---", 1)
        subject = parts[0].replace("ÄMNE:", "").strip()
        body = parts[1].strip()
    else:
        lines = full_text.split("\n")
        subject = lines[0].replace("ÄMNE:", "").strip()
        body = "\n".join(lines[1:]).strip()

    signature = f"\n\nElias Ivanoff\nFörsäljningschef, NextLead\n{FROM_EMAIL}\n072 007 33 48"

    # Strip any AI-generated signature attempt before appending ours
    for marker in ["Vänliga hälsningar", "Med vänliga hälsningar", "Mvh", "Bästa hälsningar", "Hälsningar", "Med vänlig hälsning", "Varma hälsningar", "Varmt"]:
        if marker in body:
            body = body[:body.index(marker)].rstrip()
            break

    body = body + signature
    return subject, body


def wrap_in_html(body_text: str, company_name: str) -> str:
    """Wrap plain text email in simple HTML with unsubscribe footer."""
    paragraphs = [f"<p>{p.strip()}</p>" for p in body_text.split("\n\n") if p.strip()]
    paragraphs_html = "\n".join(paragraphs)

    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: Arial, sans-serif; font-size: 15px; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  {paragraphs_html}
  <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
  <p style="font-size: 11px; color: #999;">
    Du får detta mail eftersom vi tror att NextLead kan hjälpa {company_name}.
    <a href="https://nextlead.se/avregistrera" style="color: #999;">Avregistrera dig</a>
  </p>
</body>
</html>"""


def process_lead(lead: dict) -> bool:
    """Generate email for one lead. Returns True on success."""
    lead_id = lead["id"]
    company_name = lead.get("company_name", "")

    log.info(f"Generating email for: {company_name}")

    supabase.table("leads").update({"status": "generating"}).eq("id", lead_id).execute()

    try:
        subject, body_text = generate_email(
            company_name=company_name,
            category=lead.get("category", ""),
        )

        body_html = wrap_in_html(body_text, company_name)

        to_email = lead.get("email", "")
        email_data = {
            "lead_id": lead_id,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "to_email": to_email,
            "status": "draft",
        }
        supabase.table("emails").insert(email_data).execute()

        new_status = "email_ready" if to_email else "email_ready_no_address"
        supabase.table("leads").update({"status": new_status}).eq("id", lead_id).execute()

        log.info(f"  ✓ Email generated for {company_name}")
        return True

    except Exception as e:
        log.error(f"  Error generating email for {company_name}: {e}")
        supabase.table("leads").update({"status": "ai_error"}).eq("id", lead_id).execute()
        return False


# Kategorier som är relevanta — bolag som köper leads
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

# Kategorier att alltid skippa — köper inte leads
SKIP_KEYWORDS = [
    "tandläk", "dental", "tandvård",
    "advokat", "jurist", "juridik", "advokatbyrå",
    "läkare", "klinik", "sjukhus", "vårdcentral", "apotek",
    "restaurang", "café", "bageri", "pizzeria",
    "frisör", "skönhet", "spa", "nagel",
    "kyrka", "församling", "religion",
    "skola", "förskola", "gymnasium", "utbildning",
    "museum", "teater", "biograf",
    "fastighetsförvaltning", "bostadsrättsförening", "brf ",
]

# Stora bolag att skippa — de köper inte leads via cold email
BIG_COMPANY_SKIP = [
    "nordea", "swedbank", "handelsbanken", "seb ", "seb\n", "seb,",
    "folksam", "if försäkring", "trygg-hansa", "länsförsäkringar",
    "skandia", "alecta", "afa ", "amf ", "klarna", "ica bank",
    "danske bank", "jp morgan", "deutsche bank", "blackrock",
    "ubs ", "nasdaq", "carnegie", "bank of america",
    "tele2", "telia", "tre ", "comviq", "telenor",
    "ericsson", "volvo", "ikea", "h&m",
    "finansinspektionen", "skatteverket", "riksbanken",
    "centerpartiet", "socialdemokraterna",
]


def is_relevant_lead(lead: dict) -> bool:
    """Return True if lead is relevant category AND not a large corporation."""
    category = (lead.get("category") or "").lower()
    name = (lead.get("company_name") or "").lower()

    # Skippa om kategorin matchar uteslutningslistan
    if any(kw in category or kw in name for kw in SKIP_KEYWORDS):
        return False

    # Kräv att minst ett target-keyword matchar
    if not any(kw in category or kw in name for kw in TARGET_KEYWORDS):
        return False

    # Skippa stora bolag
    if any(big in name for big in BIG_COMPANY_SKIP):
        return False

    return True


def run_ai_processor(limit: int = 50) -> int:
    """Process pending leads with relevant categories. Returns number of emails generated."""
    result = supabase.table("leads").select("*").in_(
        "status", ["pending", "scraped"]
    ).not_.is_("email", "null").neq("email", "").limit(limit * 3).execute()

    # Filter to only relevant companies
    leads = [l for l in result.data if is_relevant_lead(l)][:limit]
    log.info(f"Generating emails for {len(leads)} relevant leads")

    success = 0
    for lead in leads:
        if process_lead(lead):
            success += 1

    log.info(f"AI Processor done: {success}/{len(leads)} emails generated")
    return success


if __name__ == "__main__":
    run_ai_processor()
