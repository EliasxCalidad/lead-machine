"""
Main orchestrator: runs the full lead machine pipeline.
Can be run as a cron job daily.

Usage:
  python main.py              # Full pipeline run
  python main.py --scrape     # Only scrape
  python main.py --find-emails  # Only find email addresses
  python main.py --generate   # Only generate emails
  python main.py --send       # Only send
"""

import sys
import logging
from datetime import datetime, timezone
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log"),
    ],
)
log = logging.getLogger(__name__)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def run_pipeline(
    do_scrape: bool = True,
    do_find_emails: bool = True,
    do_generate: bool = True,
    do_send: bool = True,
):
    """Run the full lead machine pipeline."""
    run_start = datetime.now(timezone.utc).isoformat()
    log.info("=" * 60)
    log.info("LEAD MACHINE PIPELINE STARTING")
    log.info("=" * 60)

    # Create pipeline run record
    run_result = supabase.table("pipeline_runs").insert({
        "started_at": run_start,
        "status": "running",
    }).execute()
    run_id = run_result.data[0]["id"]

    stats = {
        "scraped": 0,
        "emails_found": 0,
        "generated": 0,
        "sent": 0,
        "errors": 0,
    }

    try:
        # Step 1: Scrape
        if do_scrape:
            log.info("\n[1/4] SCRAPING Google Maps...")
            from scraper import run_scraper
            stats["scraped"] = run_scraper(max_new_leads=100)
            log.info(f"Scraped: {stats['scraped']} new leads")

        # Step 2: Find emails
        if do_find_emails:
            log.info("\n[2/4] FINDING email addresses...")
            from email_finder import run_email_finder
            stats["emails_found"] = run_email_finder(limit=200)
            log.info(f"Emails found: {stats['emails_found']}")

        # Step 3: Generate emails
        if do_generate:
            log.info("\n[3/4] GENERATING emails with OpenAI...")
            from ai_processor import run_ai_processor
            stats["generated"] = run_ai_processor(limit=50)
            log.info(f"Generated: {stats['generated']} emails")

        # Step 4: Send
        if do_send:
            log.info("\n[4/4] SENDING emails...")
            from sender import run_sender
            stats["sent"] = run_sender()
            log.info(f"Sent: {stats['sent']} emails")

        # Mark run as complete
        supabase.table("pipeline_runs").update({
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "scraped_count": stats["scraped"],
            "analyzed_count": stats["emails_found"],
            "emails_sent_count": stats["sent"],
            "errors_count": stats["errors"],
            "status": "completed",
            "log": (
                f"Scraped: {stats['scraped']}, "
                f"Emails found: {stats['emails_found']}, "
                f"Generated: {stats['generated']}, "
                f"Sent: {stats['sent']}"
            ),
        }).eq("id", run_id).execute()

        log.info("\n" + "=" * 60)
        log.info("PIPELINE COMPLETE")
        log.info(f"  Scraped:      {stats['scraped']} new leads")
        log.info(f"  Emails found: {stats['emails_found']}")
        log.info(f"  Generated:    {stats['generated']} emails")
        log.info(f"  Sent:         {stats['sent']} emails")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"Pipeline error: {e}", exc_info=True)
        stats["errors"] += 1
        supabase.table("pipeline_runs").update({
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
            "log": str(e),
        }).eq("id", run_id).execute()
        raise

    return stats


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--scrape" in args:
        from scraper import run_scraper
        run_scraper()
    elif "--find-emails" in args:
        from email_finder import run_email_finder
        run_email_finder()
    elif "--generate" in args:
        from ai_processor import run_ai_processor
        run_ai_processor()
    elif "--send" in args:
        from sender import run_sender
        run_sender()
    elif "--send-one" in args:
        from sender import run_sender
        run_sender(batch_size=1)
    else:
        run_pipeline()
