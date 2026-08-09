#!/usr/bin/env python3
"""
Send the synthetic HFCL alert email that was already analyzed & stored.

Loads the most recent HFCL alert (with groq_analysis + email_body) from Supabase
and sends it via SMTP using the configured credentials in .env.
"""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("send_hfcl")

from config import settings
from db import DB
from analyzer import send_email

ALERT_ID = "326d4ce2-0162-4040-8062-b609f4b17b95"


def main():
    alert = DB.get_alert(ALERT_ID)
    if not alert:
        log.error("Alert %s not found.", ALERT_ID)
        sys.exit(1)

    instrument = DB.get_instruments()
    inst = next((i for i in instrument if i["id"] == alert["instrument_id"]), None)
    name = inst["name"] if inst else "Unknown"
    symbol = inst["symbol"] if inst else ""

    subject = (
        f"\u26a0\ufe0f Drop Alert: {name} ({symbol}) "
        f"-{float(alert['drop_pct']):.2f}% [STOCK]"
    )
    body = alert.get("email_body") or alert.get("groq_analysis") or ""
    if not body:
        log.error("No email body stored for alert.")
        sys.exit(1)

    log.info("Sending email to %s ...", settings.EMAIL_TO)
    sent = send_email(subject, body)
    if sent:
        try:
            DB.update_alert(ALERT_ID, {"status": "email_sent"})
            log.info("Marked alert as email_sent in Supabase.")
        except Exception as e:
            log.warning("Could not update alert status: %s", e)
        print("\nEMAIL SENT ✓")
        print(f"To: {settings.EMAIL_TO}")
        print(f"Subject: {subject}")
    else:
        log.error("Email was NOT sent (check SMTP credentials / network).")
        sys.exit(1)


if __name__ == "__main__":
    main()
