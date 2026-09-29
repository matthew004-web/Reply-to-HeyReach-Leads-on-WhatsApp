#!/usr/bin/env python3
"""Example: send alerts/digests to WhatsApp via Twilio.

WhatsApp has no API for personal accounts — this uses Twilio's WhatsApp
Business API (stdlib only):

  1. Create a Twilio account and get a WhatsApp-enabled number
     (the sandbox number works for testing).
  2. The recipient opts in (WhatsApp requires it — sandbox: send the join
     code to Twilio's sandbox number once).
  3. Set env vars and run:

     TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... \\
     TWILIO_WHATSAPP_FROM=whatsapp:+14155238886 WHATSAPP_TO=whatsapp:+15551234567 \\
     python3 examples/notify_whatsapp_twilio.py [file]

With no file argument it sends out/alert.md if present, else out/digest.md.
Pair with the instant watcher:

    python3 watch.py --interval 120 --notify-cmd "python3 examples/notify_whatsapp_twilio.py"
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import urllib.request


def find_default() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("out/alert.md", "out/digest.md"):
        p = os.path.join(root, name)
        if os.path.exists(p):
            return p
    raise SystemExit("nothing to send: run digest.py or watch.py first")


def main() -> None:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    sender = os.environ.get("TWILIO_WHATSAPP_FROM")  # e.g. whatsapp:+14155238886
    to = os.environ.get("WHATSAPP_TO")               # e.g. whatsapp:+15551234567
    if not all([sid, token, sender, to]):
        raise SystemExit("Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
                         "TWILIO_WHATSAPP_FROM and WHATSAPP_TO.")

    text = open(sys.argv[1] if len(sys.argv) > 1 else find_default()).read()
    if len(text) > 1500:  # WhatsApp-friendly: head + pointer to the full file
        text = text[:1400].rsplit("\n", 1)[0] + "\n\n…(full digest in digest.md)"

    creds = base64.b64encode(f"{sid}:{token}".encode()).decode()
    body = urllib.parse.urlencode(
        {"From": sender, "To": to, "Body": text}).encode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data=body, method="POST",
        headers={"Authorization": f"Basic {creds}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    if result.get("status") in ("failed", "undelivered"):
        raise SystemExit(f"Twilio error: {result.get('error_message')}")
    print(f"WhatsApp message queued (sid {result.get('sid')})")


if __name__ == "__main__":
    main()
