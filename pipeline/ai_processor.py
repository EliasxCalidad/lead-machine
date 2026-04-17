"""
AI Processor: uses OpenAI to analyze website issues and generate personalized emails.
"""

import logging
from openai import OpenAI
from supabase import create_client
from config import (
    OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY,
    CALIDAD_OFFER, FROM_NAME, FROM_EMAIL
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = f"""Du är Elias, grundare av Calidad — ett svenskt webbyrå.
Du skriver ett kort, personligt mail i FÖRSTA PERSON direkt till en småföretagare.

ABSOLUTA REGLER:
1. Skriv BARA utifrån den information du får — hitta INGENTING på
2. Nämn ALDRIG telefonnummer, adresser eller uppgifter du inte fått
3. Skriv ALLTID "jag" — aldrig "Elias" eller tredje person
4. INGEN signatur, hälsning eller "Mvh" i slutet — avsluta bara brödtexten
5. Max 120 ord i brödtexten
6. Inga buzzwords, inget corporate-speak

Strukturen:
- Rad 1: Berätta att du kollade deras hemsida
- Rad 2-3: Nämn 2 konkreta problem du hittade (använd BARA problemen du får)
- Rad 4: Koppla till förlorade kunder — kort och enkelt
- Rad 5: Presentera att du på Calidad kan hjälpa — utan att vara säljig
- Sista raden: Uppmana dem att svara direkt på mailet

Ämnesraden:
- Referera till ett SPECIFIKT problem från listan du får
- Max 8 ord, känns som från en bekant
- Exempel: "Såg att ni saknar SSL", "Ingen hittar er på Google"
- INTE generisk

Format:
ÄMNE: [ämnesrad]
---
[mailtext]
"""


def generate_email(
    company_name: str,
    website_url: str,
    category: str,
    issues: list[str],
    recommended_package: str,
    pagespeed_mobile: int | None,
    has_ssl: bool,
    meta_title: str | None,
) -> tuple[str, str]:
    """
    Generate personalized email subject + body using Claude.
    Returns (subject, body_text).
    """
    issues_text = "\n".join(f"- {issue}" for issue in issues[:5])

    user_message = f"""Företag: {company_name}
Bransch: {category or "tjänsteföretag"}
Hemsida: {website_url}
Rekommenderat paket: {recommended_package}

Problem vi hittade på deras hemsida:
{issues_text}

Skriv nu ett personligt cold email till detta företag."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=600,
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
        # Fallback parsing
        lines = full_text.split("\n")
        subject = lines[0].replace("ÄMNE:", "").strip()
        body = "\n".join(lines[1:]).strip()

    signature = f"\n\nVänliga hälsningar,\nElias | Calidad\n{FROM_EMAIL}\nhttps://calidad.agency/sv"

    # Strip any AI-generated signature attempt before appending ours
    for marker in ["Vänliga hälsningar", "Med vänliga hälsningar", "Mvh", "Bästa hälsningar", "Hälsningar", "Med vänlig hälsning", "Varma hälsningar", "Varmt"]:
        if marker in body:
            body = body[:body.index(marker)].rstrip()
            break

    body = body + signature
    return subject, body


def wrap_in_html(body_text: str, company_name: str) -> str:
    """Wrap plain text email in simple HTML with unsubscribe footer."""
    # Convert newlines to paragraphs
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
    Du får detta mail eftersom vi hittade {company_name}s hemsida och tror att vi kan hjälpa er.
    <a href="https://calidad.se/avprenumerera" style="color: #999;">Avprenumerera</a>
  </p>
</body>
</html>"""


def process_lead(lead: dict, analysis: dict) -> bool:
    """Generate email for one lead. Returns True on success."""
    lead_id = lead["id"]
    company_name = lead.get("company_name", "")

    log.info(f"Generating email for: {company_name}")

    # Mark as generating
    supabase.table("leads").update({"status": "generating"}).eq("id", lead_id).execute()

    try:
        subject, body_text = generate_email(
            company_name=company_name,
            website_url=lead.get("website_url", ""),
            category=lead.get("category", ""),
            issues=analysis.get("issues", []),
            recommended_package=analysis.get("recommended_package", "Medium"),
            pagespeed_mobile=analysis.get("pagespeed_mobile"),
            has_ssl=analysis.get("has_ssl", True),
            meta_title=analysis.get("meta_title"),
        )

        body_html = wrap_in_html(body_text, company_name)

        # Save email draft
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

        # Update lead status
        new_status = "email_ready" if to_email else "email_ready_no_address"
        supabase.table("leads").update({"status": new_status}).eq("id", lead_id).execute()

        log.info(f"  ✓ Email generated for {company_name}")
        return True

    except Exception as e:
        log.error(f"  Error generating email for {company_name}: {e}")
        supabase.table("leads").update({"status": "ai_error"}).eq("id", lead_id).execute()
        return False


def run_ai_processor(limit: int = 50) -> int:
    """Process all analyzed leads. Returns number of emails generated."""
    # Get leads that are analyzed but not yet email_ready
    result = supabase.table("leads").select("*").eq("status", "analyzed").limit(limit).execute()
    leads = result.data
    log.info(f"Generating emails for {len(leads)} analyzed leads")

    success = 0
    for lead in leads:
        # Get analysis for this lead
        analysis_result = (
            supabase.table("analyses")
            .select("*")
            .eq("lead_id", lead["id"])
            .limit(1)
            .execute()
        )
        if not analysis_result.data:
            log.warning(f"No analysis found for lead {lead['id']}")
            continue

        analysis = analysis_result.data[0]

        # Skip if no issues found (site looks fine)
        if not analysis.get("issues"):
            supabase.table("leads").update({"status": "skipped_good_site"}).eq("id", lead["id"]).execute()
            continue

        if process_lead(lead, analysis):
            success += 1

    log.info(f"AI Processor done: {success}/{len(leads)} emails generated")
    return success


if __name__ == "__main__":
    run_ai_processor()
