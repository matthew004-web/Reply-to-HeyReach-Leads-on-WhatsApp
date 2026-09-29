#!/usr/bin/env python3
"""Send approved replies from ``approvals.json``.

Each entry: {"account_id": 123, "conversation_id": "...", "message": "..."}.
Optional: "subject".

Safety rules (do not change):
- Sends each entry ONCE. SendMessage is not idempotent: an empty, no-error
  response means queued, not failed. Never retry a send that did not raise.
- Stops at the first transport error so you can resume safely; already-sent
  entries are recorded in ``out/sent.json`` and skipped on re-run.
- Marks a conversation seen only after its reply was accepted by the API.
- Nothing is sent unless you put it in approvals.json yourself.

Usage:
    python3 send.py [--approvals approvals.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heyreach.client import HeyReachClient, HeyReachError


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approvals", default="approvals.json")
    ap.add_argument("--out-dir", default="out")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    if not os.path.exists(args.approvals):
        raise SystemExit(f"error: {args.approvals} not found. "
                         "Copy approvals.example.json, fill in your replies, then re-run.")

    approvals = json.load(open(args.approvals))
    sent_path = os.path.join(args.out_dir, "sent.json")
    sent = json.load(open(sent_path)) if os.path.exists(sent_path) else []
    sent_ids = {s["conversation_id"] for s in sent}

    client = HeyReachClient()
    for entry in approvals:
        cid = entry["conversation_id"]
        if cid in sent_ids:
            print(f"skip {cid[:12]}… (already sent)")
            continue
        try:
            client.send_message(entry["account_id"], cid, entry["message"],
                                subject=entry.get("subject"))
            client.set_seen(entry["account_id"], cid, True)
        except HeyReachError as exc:
            print(f"STOPPED at {cid[:12]}…: {exc}", file=sys.stderr)
            print("Fix the issue, then re-run: already-sent entries are skipped.",
                  file=sys.stderr)
            raise SystemExit(1)
        sent.append({"conversation_id": cid, "account_id": entry["account_id"]})
        json.dump(sent, open(sent_path, "w"), indent=2)
        print(f"sent -> {cid[:12]}…")
    print(f"done: {len(sent)} sent total")


if __name__ == "__main__":
    main()
