#!/usr/bin/env python3
"""Example: push the digest to Telegram after digest.py runs.

Requires a Telegram bot: talk to @BotFather, then set:
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Usage:
    python3 digest.py
    TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python3 examples/notify_telegram.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request

DIGEST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "out", "digest.md")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
    text = open(DIGEST).read()
    # Telegram caps messages at 4096 chars; send the head + thread count.
    if len(text) > 4000:
        first = text.split("## 1.")[0]
        n = text.count("\n## ")
        text = first + f"\n_+{n} threads in the full digest — see digest.md._"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text,
                                   "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage", data=body, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.load(resp)
    if not result.get("ok"):
        raise SystemExit(f"Telegram error: {result}")
    print("digest sent to Telegram")


if __name__ == "__main__":
    main()
