#!/usr/bin/env python3
"""Near-instant reply alerts: tight poll loop over the HeyReach inbox.

Polls unseen conversations every --interval seconds (default 120). When a new
thread appears (or a new message lands in a known thread), it writes an alert
block to --alert-file and runs --notify-cmd with the alert file path, e.g. a
Telegram/WhatsApp-Business notifier. Pair with a process manager or run it in
tmux/screen — this is the "ping me in under a minute" engine.

Faster alternative: HeyReach webhooks (MESSAGE_REPLY_RECEIVED event) push to
your own endpoint with zero polling delay — see README "Real-time options".

Usage:
    export HEYREACH_API_KEY=...
    python3 watch.py --interval 90 --notify-cmd "python3 examples/notify_telegram.py"
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heyreach.client import HeyReachClient, HeyReachError
from heyreach.config import load_config, sender_names


def thread_fingerprint(item: dict) -> str:
    return f"{item.get('id')}|{item.get('lastMessageAt')}|{item.get('totalMessages')}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=120, help="poll seconds")
    ap.add_argument("--state", default="watch_state.json")
    ap.add_argument("--alert-file", default="out/alert.md")
    ap.add_argument("--notify-cmd", default=None,
                    help="shell command run on new activity, gets alert file path appended")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.alert_file) or ".", exist_ok=True)

    state = json.load(open(args.state)) if os.path.exists(args.state) else {}
    known = state.get("fingerprints", {})

    client = HeyReachClient()
    names = sender_names(load_config())
    print(f"watching HeyReach inbox every {args.interval}s (Ctrl-C to stop)", flush=True)
    try:
        while True:
            try:
                page = client.list_conversations(unseen=True, limit=50)
                items = page.get("items", []) if isinstance(page, dict) else []
            except HeyReachError as exc:
                print(f"warn: poll failed: {exc}", flush=True)
                time.sleep(args.interval)
                continue

            fresh = [it for it in items
                     if thread_fingerprint(it) not in known]
            if fresh:
                stamp = dt.datetime.now().astimezone().strftime("%H:%M:%S %Z")
                lines = [f"# New HeyReach activity — {stamp}", ""]
                for it in fresh:
                    cp = it.get("correspondentProfile") or {}
                    name = f"{cp.get('firstName') or ''} {cp.get('lastName') or ''}".strip()
                    acct = it.get("linkedInAccountId")
                    via = names.get(int(acct)) if acct else ""
                    lines += [
                        f"**{name or '(unknown)'}**"
                        + (f" — {cp.get('headline', '')[:80]}" if cp.get("headline") else "")
                        + (f" _(via {via})_" if via else ""),
                        f"> {(it.get('lastMessageText') or '')[:300]}",
                        f"profile: {cp.get('profileUrl') or 'n/a'}",
                        "",
                    ]
                    known[thread_fingerprint(it)] = True
                alert = "\n".join(lines)
                open(args.alert_file, "w").write(alert + "\n")
                json.dump({"fingerprints": known}, open(args.state, "w"))
                print(f"[{stamp}] {len(fresh)} new thread(s) — alert written", flush=True)
                if args.notify_cmd:
                    subprocess.run(args.notify_cmd + f' "{args.alert_file}"',
                                   shell=True, timeout=60)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
