---
name: "heyreach-inbox-digest"
description: "HeyReach LinkedIn inbox workflow: digest unread threads, draft goal-aware replies in the team's voice, send approved replies. Use when the user asks for HeyReach inbox digests, reply drafts, or LinkedIn outreach replies."
---

# HeyReach inbox digest (agent skill)

## Purpose
Run the HeyReach LinkedIn inbox loop: poll unseen conversations, produce a
digest, draft replies **in the team's voice toward the playbook goals**
(book a meeting, sell the upgrade), send only approved replies, mark handled
threads seen.

## Setup
`export HEYREACH_API_KEY=...` (HeyReach: Settings -> Integrations -> API).
Then personalize: `python3 setup.py` (or copy `config.example.yaml` to
`config.yaml` and edit `VOICE.md` / `PLAYBOOK.md` by hand).

## Workflow
1. `python3 digest.py` → `out/digest.md` + `out/threads.json`. Skips threads
   where we sent the last message.
2. Draft: read `PLAYBOOK.md` (triage HOT/WARM/SUPPORT/LUKEWARM/NOISE, pick the
   goal, one CTA) and `VOICE.md` (team style), or use `DRAFT_PROMPT.md` with
   an LLM. Output per thread: triage, goal, draft or `no_reply` + reason.
3. Approve: user copies approved drafts into `approvals.json`
   (see `approvals.example.json`).
4. `python3 send.py` → sends each approval **once**, then marks it seen.
   `out/sent.json` tracks what's sent.
5. Speed: `watch.py --interval 120 --notify-cmd ...` for near-instant alerts;
   HeyReach `MESSAGE_REPLY_RECEIVED` webhooks for true real-time.

## Operating Rules
- Draft-first: never send a message the user has not approved.
- `send_message` is NOT idempotent — never retry a send that did not raise.
  An empty, no-error response means queued, not failed.
- Copy conversation ids, account ids, and profile URLs exactly from
  `out/threads.json`.
- Never invent product capabilities; offer a walkthrough when unsure.
- Deliver the digest wherever the user reads it (chat, Telegram example in
  `examples/`, email). WhatsApp delivery needs the WhatsApp Business API —
  see README.
