"""
Episodic memory + relational state spine for Project G.

Files (project root):
  CONVERSATION_MEMORY.jsonl  — one JSON object per line (session summaries)
  OPEN_LOOPS.json            — structured dangling threads
  ELSE_RELATIONAL_STATE.json — trust, irritation, repair flag, last_chat_utc

Used by else_heartbeat.py (ingestion) and memory_tools.py (CLI writes).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MEMORY_FILE = "CONVERSATION_MEMORY.jsonl"
OPEN_LOOPS_FILE = "OPEN_LOOPS.json"
RELATIONAL_FILE = "ELSE_RELATIONAL_STATE.json"

DEFAULT_RELATIONAL = {
    "version": 1,
    "trust": 72,
    "irritation": 16,
    "repair_pending": False,
    "repair_topic": None,
    "last_chat_utc": None,
}


def load_json(path: str, default: dict) -> dict:
    if not os.path.exists(path):
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else dict(default)
    except json.JSONDecodeError:
        return dict(default)


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_relational() -> dict:
    r = load_json(RELATIONAL_FILE, DEFAULT_RELATIONAL)
    for k, v in DEFAULT_RELATIONAL.items():
        r.setdefault(k, v)
    return r


def save_relational(r: dict) -> None:
    save_json(RELATIONAL_FILE, r)


def load_open_loops() -> dict:
    data = load_json(OPEN_LOOPS_FILE, {"loops": []})
    if not isinstance(data.get("loops"), list):
        data["loops"] = []
    return data


def save_open_loops(data: dict) -> None:
    save_json(OPEN_LOOPS_FILE, data)


def tail_memory_entries(max_entries: int = 5) -> list[dict]:
    if not os.path.exists(MEMORY_FILE):
        return []
    lines: list[str] = []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    out: list[dict] = []
    for line in lines[-max_entries:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def unresolved_loops(loops_data: dict | None = None) -> list[dict]:
    data = loops_data if loops_data is not None else load_open_loops()
    return [x for x in data.get("loops", []) if not x.get("resolved")]


def add_open_loop(text: str) -> str:
    data = load_open_loops()
    lid = uuid.uuid4().hex[:10]
    entry = {
        "id": lid,
        "text": text.strip(),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resolved": False,
    }
    data.setdefault("loops", []).append(entry)
    save_open_loops(data)
    return lid


def resolve_loop(loop_id: str) -> bool:
    data = load_open_loops()
    found = False
    for x in data.get("loops", []):
        if x.get("id") == loop_id:
            x["resolved"] = True
            found = True
    if found:
        save_open_loops(data)
    return found


def append_memory_entry(
    bullets: list[str],
    topics: list[str] | None = None,
    open_loop_texts: list[str] | None = None,
    mood_note: str | None = None,
) -> dict:
    topics = topics or []
    record = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bullets": [b.strip() for b in bullets if b.strip()],
        "topics": [t.strip() for t in topics if t.strip()],
        "open_loops_added": [],
        "mood_note": (mood_note or "").strip() or None,
    }
    if open_loop_texts:
        for t in open_loop_texts:
            if t.strip():
                lid = add_open_loop(t.strip())
                record["open_loops_added"].append({"id": lid, "text": t.strip()})

    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    rel = load_relational()
    rel["last_chat_utc"] = record["utc"]
    save_relational(rel)
    return record


def parse_utc_iso(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def circadian_saturation_multiplier() -> float:
    tz_name = os.environ.get("ELSE_TZ", "America/Toronto")
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        now = datetime.now(timezone.utc)
    h = now.hour
    if 6 <= h < 12:
        return 0.88
    if 12 <= h < 18:
        return 1.0
    if 18 <= h < 23:
        return 1.06
    return 1.12


def apply_idle_saturation_decay(state: dict, relational: dict) -> list[str]:
    notes: list[str] = []
    lc = relational.get("last_chat_utc")
    parsed = parse_utc_iso(lc) if lc else None
    if not parsed:
        return notes
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    hours = (now - parsed).total_seconds() / 3600.0
    if hours <= 3:
        return notes
    sat = float(state.get("neural_saturation", 40))
    decay = min(6.0, 1.2 + (hours - 3) * 0.22)
    new_sat = max(18.0, sat - decay)
    if new_sat < sat - 0.5:
        state["neural_saturation"] = round(new_sat, 2)
        notes.append(f"Idle decay −{sat - new_sat:.1f} sat ({hours:.1f}h since last chat log).")
    return notes


def drift_relational_scores(relational: dict) -> None:
    trust = float(relational.get("trust", 70))
    irr = float(relational.get("irritation", 15))
    target_t, target_i = 70.0, 14.0
    if relational.get("repair_pending"):
        target_i = 22.0
    trust += (target_t - trust) * 0.04
    irr += (target_i - irr) * 0.06
    relational["trust"] = round(max(5.0, min(98.0, trust)), 2)
    relational["irritation"] = round(max(0.0, min(95.0, irr)), 2)


def irritation_pushback_bias(relational: dict) -> float:
    return max(0.0, min(1.0, (float(relational.get("irritation", 15)) - 10) / 55.0))


def format_memory_callback(memory: list[dict], loops: list[dict], relational: dict) -> str:
    parts: list[str] = []
    if relational.get("repair_pending") and relational.get("repair_topic"):
        parts.append(f"Repair pending: {relational['repair_topic']}")
    for ent in memory[-2:]:
        for b in ent.get("bullets", [])[:2]:
            if b:
                parts.append(f"Recall: {b}")
                break
    for lp in loops[:2]:
        t = lp.get("text")
        if t:
            parts.append(f"Open loop: {t}")
    if not parts:
        return ""
    return " | ".join(parts[:4])


def touch_chat_timestamp() -> None:
    rel = load_relational()
    rel["last_chat_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_relational(rel)
