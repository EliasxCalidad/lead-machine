"""
Sender: sends generated email drafts via Gmail SMTP.
Rate-limited to avoid spam filters and respect daily sending limits.
"""

import smtplib
import time
import random
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from supabase import create_client
from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
    SUPABASE_URL, SUPABASE_SERVICE_KEY,
    FROM_EMAIL, FROM_NAME, EMAILS_PER_DAY
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def count_emails_sent_today() -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    result = (
        supabase.table("emails")
        .select("id", count="exact")
        .eq("status", "sent")
        .gte("sent_at", f"{today}T00:00:00Z")
        .execute()
    )
    return result.count or 0


def send_email(email_row: dict, lead: dict, smtp: smtplib.SMTP) -> bool:
    to_address = email_row.get("to_email", "")
    if not to_address or "@" not in to_address:
        log.warning(f"  No valid email for {lead.get('company_name')} — skipping")
        supabase.table("emails").update({"status": "no_address"}).eq("id", email_row["id"]).execute()
        supabase.table("leads").update({"status": "no_email_address"}).eq("id", lead["id"]).execute()
        return False

    company_name = lead.get("company_name", "")
    log.info(f"Sending to: {company_name} <{to_address}>")

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email_row["subject"]
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = to_address

        msg.attach(MIMEText(email_row.get("body_text", ""), "plain", "utf-8"))
        msg.attach(MIMEText(email_row.get("body_html", ""), "html", "utf-8"))

        smtp.sendmail(FROM_EMAIL, to_address, msg.as_string())

        now = datetime.now(timezone.utc).isoformat()
        supabase.table("emails").update({
            "status": "sent",
            "sent_at": now,
        }).eq("id", email_row["id"]).execute()
        supabase.table("leads").update({"status": "sent"}).eq("id", lead["id"]).execute()
        log.info(f"  ✓ Sent to {to_address}")
        return True

    except Exception as e:
        log.error(f"  Exception sending to {to_address}: {e}")
        supabase.table("emails").update({"status": "send_error"}).eq("id", email_row["id"]).execute()
        return False


def run_sender(max_emails: int = EMAILS_PER_DAY) -> int:
    already_sent_today = count_emails_sent_today()
    remaining_today = max_emails - already_sent_today

    if remaining_today <= 0:
        log.info(f"Daily limit reached ({already_sent_today}/{max_emails}). Skipping.")
        return 0

    log.info(f"Can send {remaining_today} more emails today ({already_sent_today} already sent)")

    result = (
        supabase.table("emails")
        .select("*, leads(*)")
        .eq("status", "draft")
        .not_.is_("to_email", "null")
        .neq("to_email", "")
        .limit(remaining_today)
        .execute()
    )

    emails = result.data
    log.info(f"Found {len(emails)} emails ready to send")

    sent = 0
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)

        for email_row in emails:
            lead = email_row.pop("leads", {}) or {}
            if send_email(email_row, lead, smtp):
                sent += 1
                # Slumpmässig paus 10–30 min mellan mail för att undvika spam-flaggning
                delay = random.randint(600, 1800)
                log.info(f"  Väntar {delay // 60} min innan nästa mail...")
                time.sleep(delay)

    log.info(f"Sender done: {sent}/{len(emails)} sent")
    return sent


if __name__ == "__main__":
    run_sender()
