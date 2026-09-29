# Reply to HeyReach Leads on WhatsApp

Never miss a hot lead again. This watches your HeyReach LinkedIn inbox and
pings you on **WhatsApp the moment someone replies** — with a reply draft in
your voice, ready for you to approve and send. Nothing goes out on autopilot.

```
HeyReach API ──▶ watch.py ──▶ WhatsApp ping (+ draft)
      │
      └────────▶ digest.py ──▶ digest.md + threads.json
                                     │
            drafts in your voice, toward your goals (PLAYBOOK.md, VOICE.md)
                                     ▼
                              approvals.json ──▶ send.py ──▶ HeyReach API
                                      (your explicit approval)
```

## Quickstart (5 minutes)

1. **Get a HeyReach API key** — HeyReach → Settings → Integrations → **API**.
2. **Make it yours:**
   ```bash
   python3 setup.py
   ```
   Plain questions — your name, product, booking link, #1 goal, tone, one
   example reply. Writes `config.yaml` and personalizes `VOICE.md` /
   `PLAYBOOK.md`. Re-run anytime; it never clobbers your edits.
3. **Connect WhatsApp** (via Twilio — WhatsApp has no API for personal
   accounts, this uses their Business API):
   ```bash
   TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... \
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886 WHATSAPP_TO=whatsapp:+15551234567 \
   python3 watch.py --interval 120 --notify-cmd "python3 examples/notify_whatsapp_twilio.py"
   ```
   Run it persistently (tmux / screen / systemd). A reply lands → WhatsApp
   ping in ~2–3 minutes, draft included.

No dependencies — pure Python standard library.

## The workflow

**1. Get pinged** — `watch.py` polls the inbox and fires your notifier the
moment a reply lands. See "Respond in under a minute" below.

**2. Review the digest** — `python3 digest.py` writes `out/digest.md`
(readable overview) and `out/threads.json` (structured data). Threads where
you sent the last message are skipped. Processed ids go to `state.json`, so
the next run only shows new activity.

**3. Draft replies — in your voice, toward your goals**

`PLAYBOOK.md` encodes the sales motion: triage every thread (HOT / WARM /
SUPPORT / LUKEWARM / NOISE), pick the goal (book a meeting, sell the upgrade,
or resolve-then-convert), one CTA per message, speed wins. `VOICE.md` encodes
how your team sounds — calibrate it with 2–3 replies you're proud of.

Use `DRAFT_PROMPT.md` with your AI assistant / LLM: attach `out/threads.json`
plus the two guides, get back classified threads with drafts. Drafts follow a
Hormozi-style direct voice (`VOICE.md`) and negotiation tactics (`PLAYBOOK.md`:
value equation on the CTA, give value first, risk reversal, specificity) —
swap either guide for your own style. Or write drafts yourself.

**4. Approve**
```bash
cp approvals.example.json approvals.json
# fill in the drafts you approve — only these will be sent
```

**5. Send**
```bash
python3 send.py
```
Sends each approval **once**, then marks the conversation seen. Sent entries
are recorded in `out/sent.json` and skipped on re-runs.

## Respond in under a minute

Two tiers, pick your speed:

- **Polling (simple, no infra):** `watch.py` polls the inbox every ~2 minutes
  and fires your notifier the moment a reply lands:
  ```bash
  python3 watch.py --interval 120 --notify-cmd "python3 examples/notify_whatsapp_twilio.py"
  ```
  Detection-to-ping is ~2–3 min.
- **Webhooks (true real-time):** HeyReach supports a `MESSAGE_REPLY_RECEIVED`
  webhook (`POST /webhooks/CreateWebhook`). Point it at your own endpoint and
  you get pushed the instant a reply arrives — no polling delay. Needs a public
  URL; polling covers everyone else.

## Other delivery channels

The digest is channel-agnostic. WhatsApp is the default path above; alternatives:

- **Telegram** — `examples/notify_telegram.py`
- **Slack / email** — same pattern: post the markdown after `digest.py` /
  `watch.py`.

## As an agent skill

`SKILL.md` adapts this workflow for AI agents (Claude, etc.): digest →
draft → approve → send, with the same safety rules.

## API reference (verified)

Base `https://api.heyreach.io/api/public`, auth header `X-API-KEY`.

| Call | Method & path |
|---|---|
| Validate key | `GET /auth/CheckApiKey` |
| List conversations | `POST /inbox/GetConversationsV2` `{offset, limit, filters:{linkedInAccountIds, campaignIds, searchString, leadProfileUrl, tags, seen}}` |
| Full thread | `GET /inbox/GetChatroom/{accountId}/{conversationId}` |
| Send reply | `POST /inbox/SendMessage` `{message, conversationId, linkedInAccountId, subject?}` |
| Mark seen | `POST /inbox/SetSeenStatus` `{conversationId, linkedInAccountId, seen}` |
| Create webhook | `POST /webhooks/CreateWebhook` |

## Safety

- **Draft-first, always.** Nothing is sent unless you put it in
  `approvals.json`.
- **SendMessage is not idempotent.** Never retry a send that didn't raise an
  error — an empty, no-error response means *queued*, not failed. Re-firing
  creates a duplicate message on LinkedIn. `send.py` stops at the first
  transport error so you can resume safely.
- Keep `HEYREACH_API_KEY` and Twilio credentials out of the repo (gitignored —
  use env vars, never commit them).
