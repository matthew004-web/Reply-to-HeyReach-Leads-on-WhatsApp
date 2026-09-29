#!/usr/bin/env python3
"""Build a digest of unread HeyReach inbox threads.

- Lists unseen conversations (paged, capped).
- Fetches each full thread; skips threads where we sent the last message.
- Writes ``digest.md`` (human-readable overview) and ``threads.json``
  (structured data for draft generation, see DRAFT_PROMPT.md).
- Records processed conversation ids in ``state.json`` so the next run only
  surfaces new activity. Use ``--no-state`` for a one-off run.

Usage:
    export HEYREACH_API_KEY=...
    python3 digest.py [--limit 50] [--max-threads 15] [--out-dir out]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heyreach.client import HeyReachClient, HeyReachError
from heyreach.config import load_config, sender_names


def person(cp: dict) -> dict:
    cp = cp or {}
    name = f"{cp.get('firstName') or ''} {cp.get('lastName') or ''}".strip()
    return {
        "name": name or "(unknown)",
        "headline": cp.get("headline") or "",
        "company": cp.get("companyName") or "",
        "profile_url": cp.get("profileUrl") or "",
    }


def clean_messages(raw: list) -> list:
    out = []
    for m in raw or []:
        text = m.get("text") or m.get("body") or m.get("message") or ""
        sender = m.get("sender") or m.get("senderType") or m.get("from") or ""
        out.append({"sender": sender, "text": text.strip(),
                    "at": m.get("createdAt") or m.get("timestamp") or ""})
    return [m for m in out if m["text"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50, help="conversations to scan")
    ap.add_argument("--max-threads", type=int, default=15, help="threads to include")
    ap.add_argument("--out-dir", default="out")
    ap.add_argument("--no-state", action="store_true")
    ap.add_argument("--state", default="state.json")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    state = {}
    if not args.no_state and os.path.exists(args.state):
        state = json.load(open(args.state))
    seen_ids = set(state.get("processed_ids", []))

    client = HeyReachClient()
    names = sender_names(load_config())
    try:
        page = client.list_conversations(unseen=True, limit=min(args.limit, 100))
    except HeyReachError as exc:
        raise SystemExit(f"error: {exc}")
    items = page.get("items", []) if isinstance(page, dict) else []

    threads, fresh_ids = [], []
    for it in items:
        if len(threads) >= args.max_threads:
            break
        cid, acct = it.get("id"), it.get("linkedInAccountId")
        if not cid or cid in seen_ids:
            continue
        try:
            full = client.get_thread(acct, cid)
        except HeyReachError as exc:
            print(f"warn: could not fetch thread {cid[:12]}…: {exc}", file=sys.stderr)
            continue
        msgs = clean_messages(full.get("messages"))
        if not msgs:
            continue
        if msgs[-1]["sender"] == "ME":
            fresh_ids.append(cid)  # nothing to answer; still mark processed
            continue
        who = person(full.get("correspondentProfile") or it.get("correspondentProfile"))
        threads.append({
            "conversation_id": cid,
            "account_id": acct,
            "sender_name": names.get(int(acct)) if acct else "",
            "last_message_at": it.get("lastMessageAt") or "",
            **who,
            "messages": msgs,
        })
        fresh_ids.append(cid)

    stamp = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    lines = [f"# HeyReach inbox digest — {stamp}",
             f"{len(threads)} thread(s) need a reply.",
             "",
             "> Drafts are yours to write or generate (see DRAFT_PROMPT.md). "
             "Nothing is sent until you approve it in approvals.json and run send.py.",
             ""]
    for i, t in enumerate(threads, 1):
        last = t["messages"][-1]
        lines += [
            f"## {i}. {t['name']}" + (f" — {t['headline']}" if t['headline'] else ""),
            (f"_Replying as {t['sender_name']}_" if t.get("sender_name") else ""),
            (f"_{t['company']}_" if t['company'] else ""),
            f"Profile: {t['profile_url']}" if t["profile_url"] else "",
            "",
            f"**Last message (them):** {last['text']}",
            "",
            f"**Draft:** _[your reply here]_",
            "",
            "---",
            "",
        ]
    digest_path = os.path.join(args.out_dir, "digest.md")
    threads_path = os.path.join(args.out_dir, "threads.json")
    open(digest_path, "w").write("\n".join(lines).strip() + "\n")
    json.dump(threads, open(threads_path, "w"), ensure_ascii=False, indent=2)

    if not args.no_state:
        state["processed_ids"] = sorted(seen_ids | set(fresh_ids))
        state["last_run"] = stamp
        json.dump(state, open(args.state, "w"), indent=2)

    print(f"wrote {digest_path} ({len(threads)} threads needing replies)")


if __name__ == "__main__":
    main()
