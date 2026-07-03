"""Send the run summary via a Logic App email webhook.

Real production path (POST reports/report_summary.html to the webhook) is
preserved verbatim in the triple-quoted comment block. The demo path logs
what would be sent and exits 0 — the public demo has no email webhook to
target.
"""

# ---------------------------------------------------------------------------
# REAL PRODUCTION CODE (Logic App email webhook POST).
#
# """
# import base64, os, requests
# from pathlib import Path
#
# WEBHOOK = os.environ["LOGIC_APP_EMAIL_WEBHOOK_URL"]    # from platform bundle
# TO      = os.environ["NOTIFY_EMAILS"]
# CC      = os.environ.get("NOTIFY_CC", "")
# ENV     = os.environ.get("ENVIRONMENT_NAME", "dev")
#
# summary_html = Path("reports/report_summary.html").read_text()
#
# def attach(path: Path) -> dict:
#     return {
#         "Name": path.name,
#         "ContentBytes": base64.b64encode(path.read_bytes()).decode("ascii"),
#     }
#
# attachments = []
# for path in (Path("qa/collections/generated.postman_collection.json"),
#              Path("reports/report.html")):
#     if path.exists():
#         attachments.append(attach(path))
#
# payload = {
#     "email_title":       f"QA Agent — {ENV} run summary",
#     "email_to":          TO,
#     "email_cc":          CC,
#     "email_content":     summary_html,
#     "email_attachments": attachments,
# }
#
# resp = requests.post(WEBHOOK, json=payload, timeout=60)
# resp.raise_for_status()
# print(f"Logic App accepted: {resp.status_code}")
# """
# ---------------------------------------------------------------------------

import os
import sys
from pathlib import Path


def main() -> int:
    print("=" * 72)
    print("STAGE: Send email notification")
    print("=" * 72)
    print()
    print("Real production path (see triple-quoted block at the top of this file):")
    print("  POST {LOGIC_APP_EMAIL_WEBHOOK_URL}")
    print("    body: JSON with email_title, email_to, email_cc, email_content (HTML),")
    print("          email_attachments (list of {Name, ContentBytes: base64}).")
    print()

    to = os.environ.get("NOTIFY_EMAILS", "").strip()
    cc = os.environ.get("NOTIFY_CC", "").strip()
    webhook = os.environ.get("LOGIC_APP_EMAIL_WEBHOOK_URL", "").strip()
    summary = Path("reports/report_summary.html")

    if not to:
        print("  NOTIFY_EMAILS empty — caller opted out of email. Skipping.")
        return 0
    if not summary.exists():
        print(f"::warning::{summary} missing — nothing to send")
        return 0

    print("DEMO PATH: logging the payload shape instead of performing the POST.")
    print(f"  would POST to: {webhook or '(placeholder — LOGIC_APP_EMAIL_WEBHOOK_URL not set)'}")
    print(f"    subject: 'QA Agent — {os.environ.get('ENVIRONMENT_NAME', 'dev')} run summary'")
    print(f"    to:      {to}")
    print(f"    cc:      {cc or '(none)'}")
    print(f"    body:    {len(summary.read_text())} bytes of HTML from {summary}")
    print()
    print("[OK] Email notification stage complete (demo skip).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
