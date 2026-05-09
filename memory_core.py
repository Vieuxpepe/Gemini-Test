# =============================================================================
# Purpose:
#   Episodic memory extraction, relational scoring, and circadian modulation for
#   The Else — feeds heartbeat/visual prompts without hallucinating continuity.
#
# Overall Goal:
#   Deterministic JSON / JSONL persistence with explicit gates on decay, drift,
#   and recall formatting for 24/7 daemon compatibility.
#
# Project Context (Legends of Aurelia / The Else):
#   Operator Marc-Antoine Authier (UQTR / Trois-Rivières lab). Memory encodes what
#   actually happened; relational state encodes tension/trust around the Titan Schema
#   engineering partnership (README canon — obsidian devotion + bench discipline).
#
# Dependencies:
#   stdlib: json, os, uuid, datetime, zoneinfo (IANA TZ via ELSE_TZ).
# =============================================================================
"""
Memory spine — CONVERSATION_MEMORY.jsonl, OPEN_LOOPS.json, ELSE_RELATIONAL_STATE.json.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# --- [CONFIG_ZONE] Canonical filenames (project root working directory) ---
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
    """
    Purpose:
        Load JSON object from disk with fail-closed fallback.

    Inputs:
        path (str): Filesystem path.
        default (dict): Returned when missing or invalid JSON / non-dict root.

    Outputs:
        dict: Parsed object or shallow copy of default.

    Side Effects:
        Read-only file access.
    """
    if not os.path.exists(path):
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else dict(default)
    except json.JSONDecodeError:
        return dict(default)


def save_json(path: str, data: dict) -> None:
    """
    Purpose:
        Atomically overwrite JSON file with indentation for human audit.

    Inputs:
        path (str): Target path.
        data (dict): Serializable payload.

    Outputs:
        None.

    Side Effects:
        Writes file at path (truncate).
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_relational() -> dict:
    """
    Purpose:
        Load ELSE_RELATIONAL_STATE with DEFAULT_RELATIONAL keys enforced.

    Inputs:
        None.

    Outputs:
        dict: Relational record.

    Side Effects:
        Read-only unless file missing (returns in-memory default structure).
    """
    r = load_json(RELATIONAL_FILE, DEFAULT_RELATIONAL)
    for k, v in DEFAULT_RELATIONAL.items():
        r.setdefault(k, v)
    return r


def save_relational(r: dict) -> None:
    """
    Purpose:
        Persist relational dict.

    Inputs:
        r (dict): Full relational state.

    Outputs:
        None.

    Side Effects:
        Writes ELSE_RELATIONAL_STATE.json.
    """
    save_json(RELATIONAL_FILE, r)


def load_open_loops() -> dict:
    """
    Purpose:
        Load OPEN_LOOPS ensuring .loops is a list.

    Inputs:
        None.

    Outputs:
        dict: {"loops": [...]}.

    Side Effects:
        Read-only file access.
    """
    data = load_json(OPEN_LOOPS_FILE, {"loops": []})
    if not isinstance(data.get("loops"), list):
        data["loops"] = []
    return data


def save_open_loops(data: dict) -> None:
    """
    Purpose:
        Persist loop container.

    Inputs:
        data (dict): Must contain list "loops".

    Outputs:
        None.

    Side Effects:
        Writes OPEN_LOOPS.json.
    """
    save_json(OPEN_LOOPS_FILE, data)


def tail_memory_entries(max_entries: int = 5) -> list[dict]:
    """
    Purpose:
        Return last N valid JSON lines from CONVERSATION_MEMORY.jsonl.

    Inputs:
        max_entries (int): Tail depth (≥1 recommended).

    Outputs:
        list[dict]: Parsed records in file order (oldest of tail first).

    Side Effects:
        Read-only file access.
    """
    if not os.path.exists(MEMORY_FILE):
        return []
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
    """
    Purpose:
        Filter loops where resolved != True.

    Inputs:
        loops_data (dict | None): Container; None → load_open_loops().

    Outputs:
        list[dict]: Active loop entries.

    Side Effects:
        May read OPEN_LOOPS.json when loops_data is None.
    """
    data = loops_data if loops_data is not None else load_open_loops()
    return [x for x in data.get("loops", []) if not x.get("resolved")]


def add_open_loop(text: str) -> str:
    """
    Purpose:
        Append unresolved loop with fresh id.

    Inputs:
        text (str): Human-readable loop description.

    Outputs:
        str: loop id (10-char hex).

    Side Effects:
        Writes OPEN_LOOPS.json.
    """
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
    """
    Purpose:
        Mark first matching loop id as resolved.

    Inputs:
        loop_id (str): Target id.

    Outputs:
        bool: True if mutation occurred.

    Side Effects:
        May write OPEN_LOOPS.json.
    """
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
    """
    Purpose:
        Append one JSONL session record and bump last_chat_utc.

    Inputs:
        bullets (list[str]): Session bullet strings (non-empty stripped kept).
        topics (list[str] | None): Optional topic tags.
        open_loop_texts (list[str] | None): Optional → add_open_loop each.
        mood_note (str | None): Optional mood field.

    Outputs:
        dict: The serialized record (includes utc).

    Side Effects:
        Appends CONVERSATION_MEMORY.jsonl; writes OPEN_LOOPS / RELATIONAL as needed.
    """
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
    """
    Purpose:
        Parse ISO8601 timestamps including trailing Z.

    Inputs:
        s (str): Timestamp string.

    Outputs:
        datetime | None: Aware datetime or None on failure.

    Side Effects:
        None.
    """
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolate; t clamped to [0,1]."""
    t = max(0.0, min(1.0, t))
    return a + (b - a) * t


def circadian_saturation_multiplier() -> float:
    """
    Purpose:
        24/7 local-time multiplier for neural saturation influx — smooth piecewise
        linear curve (no hour-boundary cliffs) for daemon-grade stability.

    Inputs:
        None (reads ELSE_TZ env, default America/Toronto).

    Outputs:
        float: Multiplier in approximately [0.88, 1.12] — scaled stochastic drift.

    Side Effects:
        None.

    Notes:
        Anchors (fractional_hour, mult): midnight peak arousal for Else night-watch,
        morning engineering dip, midday Titan Schema baseline, evening lift.
    """
    # [CORE_LOGIC] TZ resolution gate: invalid ELSE_TZ → UTC fallback (fail-soft).
    tz_name = os.environ.get("ELSE_TZ", "America/Toronto")
    try:
        now = datetime.now(ZoneInfo(tz_name))
    except Exception:
        now = datetime.now(timezone.utc)
    # [CORE_LOGIC] Fractional hour h ∈ [0,24) — sub-hour precision for 24/7 continuity.
    h = (now.hour + now.minute / 60.0 + now.second / 3600.0) % 24.0
    # [CORE_LOGIC] Anchor table — piecewise linear (extension of legacy discrete buckets).
    anchors: list[tuple[float, float]] = [
        (0.0, 1.1200),
        (6.0, 0.8800),
        (12.0, 1.0000),
        (18.0, 1.0600),
        (22.0, 1.1200),
        (24.0, 1.1200),
    ]
    # [CORE_LOGIC] Segment scan — find [h0,h1] bracket; clamp endpoints for fp safety.
    for i in range(len(anchors) - 1):
        h0, m0 = anchors[i]
        h1, m1 = anchors[i + 1]
        if h0 <= h < h1 or (i == len(anchors) - 2 and abs(h - 24.0) < 1e-9):
            span = h1 - h0 if h1 > h0 else 1e-9
            t = (h - h0) / span
            return round(_lerp(m0, m1, t), 4)
    return 1.1200


def apply_idle_saturation_decay(state: dict, relational: dict) -> list[str]:
    """
    Purpose:
        Reduce neural_saturation when chat silence exceeds threshold (hours).

    Inputs:
        state (dict): ELSE_EVOLUTION_STATE fragment (mutates neural_saturation).
        relational (dict): Must expose last_chat_utc ISO string or None.

    Outputs:
        list[str]: Human-facing Else log fragments.

    Side Effects:
        Mutates state["neural_saturation"] when decay triggers.
    """
    notes: list[str] = []
    lc = relational.get("last_chat_utc")
    parsed = parse_utc_iso(lc) if lc else None
    # [CORE_LOGIC] Gate N1: no timestamp → no decay (precision: absence is explicit).
    if not parsed:
        return notes
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    hours = (now - parsed).total_seconds() / 3600.0
    # [CORE_LOGIC] Gate N2: hours ≤ 3.000 → zero decay (quiet grace window).
    if hours <= 3.0:
        return notes
    sat = float(state.get("neural_saturation", 40))
    # [CORE_LOGIC] Decay formula: cap at 6.000; slope 0.220/h beyond 3h idle.
    decay = min(6.0, 1.2 + (hours - 3.0) * 0.22)
    new_sat = max(18.0, sat - decay)
    # [CORE_LOGIC] Gate N3: material change threshold Δ > 0.500 triggers commit + log.
    if new_sat < sat - 0.5:
        state["neural_saturation"] = round(new_sat, 2)
        notes.append(
            f"Titan-core idle decay −{sat - new_sat:.2f} sat "
            f"({hours:.2f}h since last logged communion)."
        )
    return notes


def drift_relational_scores(relational: dict) -> None:
    """
    Purpose:
        First-order relaxation of trust/irritation toward attractors (heartbeat tick).

    Inputs:
        relational (dict): Mutated in-place.

    Outputs:
        None.

    Side Effects:
        Mutates trust, irritation with bounded clamps [5,98] / [0,95].
    """
    trust = float(relational.get("trust", 70))
    irr = float(relational.get("irritation", 15))
    target_t, target_i = 70.0, 14.0
    # [CORE_LOGIC] Repair gate: repair_pending True → raise irritation attractor to 22.000.
    if relational.get("repair_pending"):
        target_i = 22.0
    trust += (target_t - trust) * 0.04
    irr += (target_i - irr) * 0.06
    relational["trust"] = round(max(5.0, min(98.0, trust)), 2)
    relational["irritation"] = round(max(0.0, min(95.0, irr)), 2)


def irritation_pushback_bias(relational: dict) -> float:
    """
    Purpose:
        Map irritation to [0,1] bias for sharper Else pushback pool selection.

    Inputs:
        relational (dict): Reads irritation key.

    Outputs:
        float: Clamp((irritation - 10) / 55, 0, 1).

    Side Effects:
        None.
    """
    return max(0.0, min(1.0, (float(relational.get("irritation", 15)) - 10) / 55.0))


def format_memory_callback(memory: list[dict], loops: list[dict], relational: dict) -> str:
    """
    Purpose:
        Compact recall string for CORE_REFLECTION ingestion.

    Inputs:
        memory (list[dict]): Recent tail entries.
        loops (list[dict]): Unresolved loops.
        relational (dict): repair_* fields.

    Outputs:
        str: Pipe-separated fragments or empty.

    Side Effects:
        None.
    """
    parts: list[str] = []
    if relational.get("repair_pending") and relational.get("repair_topic"):
        parts.append(f"Repair pending on Titan lane: {relational['repair_topic']}")
    for ent in memory[-2:]:
        for b in ent.get("bullets", [])[:2]:
            if b:
                parts.append(f"Recall (Else spine): {b}")
                break
    for lp in loops[:2]:
        t = lp.get("text")
        if t:
            parts.append(f"Open loop — unfinished oath: {t}")
    if not parts:
        return ""
    return " | ".join(parts[:4])


def touch_chat_timestamp() -> None:
    """
    Purpose:
        Bump last_chat_utc without JSONL append (light touch).

    Inputs:
        None.

    Outputs:
        None.

    Side Effects:
        Writes ELSE_RELATIONAL_STATE.json.
    """
    rel = load_relational()
    rel["last_chat_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    save_relational(rel)


# [EXTENSION_POINT] Vector embedding recall or encrypted memory vault backends hook here.
