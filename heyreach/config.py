"""Minimal YAML-subset reader for config.yaml (stdlib only).

Supports exactly the shapes used in config.example.yaml:
  - nested maps via 2-space indentation
  - lists via '- ' items (including '- key: value' maps)
  - scalars (strings, ints, booleans), '#' comments
Not a general YAML parser — keep your config shaped like the example.
"""

from __future__ import annotations

import os


def _scalar(val: str):
    v = val.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if v.isdigit():
        return int(v)
    return v


def _parse_list(items, i, child_ind):
    lst, j = [], i
    n = len(items)
    while j < n and items[j][0] == child_ind and items[j][1].startswith("- "):
        first = items[j][1][2:].strip()
        entry: dict = {}
        if first:
            if ":" in first:
                k, _, v = first.partition(":")
                entry[k.strip()] = _scalar(v)
            else:
                lst.append(_scalar(first))
                j += 1
                continue
        j += 1
        while j < n and items[j][0] > child_ind:
            t = items[j][1]
            if ":" in t:
                k, _, v = t.partition(":")
                entry[k.strip()] = _scalar(v)
            j += 1
        lst.append(entry)
    return lst, j


def _build(items, idx, indent):
    node, i, n = {}, idx, len(items)
    while i < n:
        ind, text = items[i]
        if ind < indent:
            break
        if ind > indent or text.startswith("- ") or ":" not in text:
            i += 1
            continue
        key, _, val = text.partition(":")
        key, val = key.strip(), val.strip()
        if i + 1 < n and items[i + 1][0] > ind:
            child_ind = items[i + 1][0]
            if items[i + 1][1].startswith("- "):
                node[key], i = _parse_list(items, i + 1, child_ind)
            else:
                node[key], i = _build(items, i + 1, child_ind)
        else:
            node[key] = _scalar(val)
            i += 1
    return node, i


def load_config(path: str = "config.yaml") -> dict:
    """Load config.yaml (relative to repo root). Returns {} if absent."""
    if not os.path.exists(path):
        return {}
    items = []
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if " #" in line:  # inline comment (URLs never contain ' #')
            line = line[:line.index(" #")]
            s = line.strip()
            if not s:
                continue
        items.append((len(line) - len(line.lstrip(" ")), s))
    node, _ = _build(items, 0, 0)
    return node


def sender_names(config: dict) -> dict:
    """Map HeyReach LinkedIn account id -> human name from config team list."""
    out = {}
    for t in config.get("team", []) or []:
        aid, name = t.get("heyreach_account_id"), t.get("name")
        if aid and name:
            out[int(aid)] = name
    return out
