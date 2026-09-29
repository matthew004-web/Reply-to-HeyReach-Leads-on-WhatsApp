"""Minimal HeyReach Public API client using only the Python standard library.

Auth: API key from the ``HEYREACH_API_KEY`` environment variable, sent as the
``X-API-KEY`` header. Get a key in HeyReach: Settings -> Integrations -> API.

Endpoint reference (verified against the public API surface):
  GET  /auth/CheckApiKey
  POST /inbox/GetConversationsV2   {offset, limit, filters: {...}}
  GET  /inbox/GetChatroom/{accountId}/{conversationId}
  POST /inbox/SendMessage           {message, conversationId, linkedInAccountId, subject?}
  POST /inbox/SetSeenStatus         {conversationId, linkedInAccountId, seen}
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://api.heyreach.io/api/public"


class HeyReachError(RuntimeError):
    """Transport failure or HeyReach API error response."""


class HeyReachClient:
    def __init__(self, api_key: str | None = None, base_url: str = BASE_URL) -> None:
        key = api_key or os.environ.get("HEYREACH_API_KEY")
        if not key:
            raise HeyReachError(
                "No API key. Set the HEYREACH_API_KEY environment variable "
                "(HeyReach: Settings -> Integrations -> API)."
            )
        self.api_key = key
        self.base_url = base_url.rstrip("/")

    def _call(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("X-API-KEY", self.api_key)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace")
            raise HeyReachError(f"{method} {path} -> HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise HeyReachError(f"{method} {path} -> connection failed: {exc}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}

    # ------------------------------------------------------------------ auth
    def check_key(self):
        """GET /auth/CheckApiKey. HTTP 200 (even with an empty body) = valid."""
        return self._call("GET", "/auth/CheckApiKey")

    # ----------------------------------------------------------------- inbox
    def list_conversations(self, *, unseen: bool | None = None, limit: int = 100,
                           offset: int = 0, account_ids=None, campaign_ids=None,
                           search: str | None = None, tags=None):
        filters: dict = {}
        if account_ids:
            filters["linkedInAccountIds"] = [int(a) for a in account_ids]
        if campaign_ids:
            filters["campaignIds"] = [int(c) for c in campaign_ids]
        if search:
            filters["searchString"] = search
        if tags:
            filters["tags"] = list(tags)
        if unseen is not None:
            filters["seen"] = bool(unseen)
        return self._call("POST", "/inbox/GetConversationsV2",
                          {"offset": offset, "limit": limit, "filters": filters})

    def get_thread(self, account_id: int, conversation_id: str):
        cid = urllib.parse.quote(conversation_id, safe="")
        return self._call("GET", f"/inbox/GetChatroom/{int(account_id)}/{cid}")

    def send_message(self, account_id: int, conversation_id: str, message: str,
                     subject: str | None = None):
        """POST /inbox/SendMessage.

        NOT idempotent: never retry a send that did not raise an error. An
        empty, no-error response means the message is queued, not failed —
        re-firing creates a duplicate message on LinkedIn.
        """
        body = {"message": message, "conversationId": conversation_id,
                "linkedInAccountId": int(account_id)}
        if subject:
            body["subject"] = subject
        return self._call("POST", "/inbox/SendMessage", body)

    def set_seen(self, account_id: int, conversation_id: str, seen: bool = True):
        return self._call("POST", "/inbox/SetSeenStatus",
                          {"conversationId": conversation_id,
                           "linkedInAccountId": int(account_id),
                           "seen": bool(seen)})
