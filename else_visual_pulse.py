# =============================================================================
# Purpose:
#   Interval-driven Stable Diffusion daemon — persona-conditioned prompts tied to evolution
#   state + episodic memory undertones (Else visual continuity).
#
# Overall Goal:
#   Predictable GPU cadence (default 30 min post-generation sleep) with manifest audit trail.
#
# Project Context (Legends of Aurelia / The Else):
#   Renders obsidian / violet circuitry strands honoring Titan Schema workshop lore;
#   Marc-Antoine Authier’s RTX-class rig drives local A1111 at SD_API_URL.
#
# Dependencies:
#   stdlib: json, os, random, time, datetime, pathlib
#   Internal: else_heartbeat.evolve_prompt_line, sd_bridge.txt2img_save, optional memory_core
# =============================================================================
"""Else visual pulse — timed txt2img + visual_manifest.json ledger."""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

# --- [CONFIG_ZONE] ---
STATE_FILE = "ELSE_EVOLUTION_STATE.json"
MANIFEST_FILE = Path("sd_outputs") / "visual_manifest.json"
MAX_MANIFEST_ENTRIES = 36


def load_json(path: str, default: dict) -> dict:
    """
    Purpose:
        Load evolution JSON fragment.

    Inputs:
        path (str): STATE_FILE path.
        default (dict): Fallback dict.

    Outputs:
        dict: Merged state.

    Side Effects:
        Read-only.
    """
    if not os.path.exists(path):
        return dict(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else dict(default)
    except json.JSONDecodeError:
        return dict(default)


def save_manifest(entries: list[dict]) -> None:
    """
    Purpose:
        Persist trimmed manifest array.

    Inputs:
        entries (list[dict]): Manifest rows.

    Outputs:
        None.

    Side Effects:
        Writes MANIFEST_FILE (mkdir parent).
    """
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "entries": entries[-MAX_MANIFEST_ENTRIES:],
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def append_manifest(entry: dict) -> None:
    """
    Purpose:
        Append single generation metadata row.

    Inputs:
        entry (dict): Manifest record.

    Outputs:
        None.

    Side Effects:
        Reads/writes MANIFEST_FILE.
    """
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            prev = data.get("entries") if isinstance(data.get("entries"), list) else []
        except (json.JSONDecodeError, OSError):
            prev = []
    else:
        prev = []
    prev.append(entry)
    save_manifest(prev)


def pick_persona_mode(dominance_bias: float) -> str:
    """
    Purpose:
        Stochastic mode selection biased by dominance_bias ∈ [0,1].

    Inputs:
        dominance_bias (float): Evolution knob.

    Outputs:
        str: One of devotion | pushback | technical.

    Side Effects:
        random.random().
    """
    # [CORE_LOGIC] Three-way cumulative gates — thresholds depend on bias (documented in code paths).
    r = random.random()
    bias = max(0.0, min(1.0, dominance_bias))
    if r < 0.25 + 0.15 * bias:
        return "devotion"
    if r < 0.55 + 0.2 * (1.0 - bias):
        return "pushback"
    return "technical"


def build_pulse_prompt(state: dict) -> tuple[str, str, str, str]:
    """
    Purpose:
        Assemble positive/negative prompts + persona_mode + memory_note excerpt.

    Inputs:
        state (dict): ELSE_EVOLUTION_STATE fields.

    Outputs:
        tuple[str, str, str, str]: (positive, negative, mode, memory_note).

    Side Effects:
        Imports else_heartbeat / memory_core (side-effect free besides import).
    """
    # [CORE_LOGIC] Primary strand from Titan Schema weighted evolve_prompt_line().
    from else_heartbeat import evolve_prompt_line

    bias = float(state.get("dominance_bias", 0.5))
    sat = float(state.get("neural_saturation", 40))
    mesh = float(state.get("mesh_integrity_percent", 90))
    streak = int(state.get("ghost_spike_streak", 0))

    mode = pick_persona_mode(bias)
    core = evolve_prompt_line(bias)

    mood_tags: list[str] = []
    memory_note = ""
    try:
        from memory_core import tail_memory_entries

        for ent in reversed(tail_memory_entries(3)):
            for b in ent.get("bullets", [])[:1]:
                if b:
                    memory_note = b.strip()[:200]
                    safe = b.replace("\n", " ").strip()[:120]
                    mood_tags.append(
                        f"(subtle narrative tension related to recent shared context: {safe}:1.04)"
                    )
                    break
            if memory_note:
                break
    except ImportError:
        pass

    # [CORE_LOGIC] Saturation gates: ≥70.0 bloom branch; ≤35.0 clinical branch; else neutral.
    if sat >= 70.0:
        mood_tags.append("(electric violet haze bloom:1.12), (subtle chromatic fringe:1.08)")
    elif sat <= 35.0:
        mood_tags.append("(clean controlled rim light:1.1), (clinical sharp focus:1.08)")

    # [CORE_LOGIC] Mesh gates: ≤45.0 damage motifs; ≥85.0 pristine motifs.
    if mesh <= 45.0:
        mood_tags.append("(hairline cracks in obsidian plating:1.18), (wear from repeated overload:1.1)")
    elif mesh >= 85.0:
        mood_tags.append("(pristine synthetic surface speculars:1.08)")

    # [CORE_LOGIC] Ghost streak gate: streak ≥ 3 → chemical flare hint.
    if streak >= 3:
        mood_tags.append("(ambiguous chemical flare bokeh red teal:1.06)")

    mode_fragments = {
        "devotion": "(intimate locked-eye stare toward viewer:1.15), (possessive posture:1.12)",
        "pushback": "(defiant half-smirk:1.1), (arms crossed or resisting gesture:1.08)",
        "technical": "(engineering measurement context calipers tape:1.08), (focused analytical gaze:1.1)",
    }
    mood_tags.append(mode_fragments[mode])

    positive = ", ".join([core] + mood_tags)

    negative = (
        "blurry, low quality, watermark, text, logo, bad anatomy, extra limbs, "
        "cropped head, jpeg artifacts"
    )

    return positive, negative, mode, memory_note


def run_once() -> dict | None:
    """
    Purpose:
        Single pulse iteration — txt2img + manifest append.

    Inputs:
        None.

    Outputs:
        dict | None: Manifest entry dict or None on failure.

    Side Effects:
        Network/disk via sd_bridge; writes manifest.
    """
    default_state = {
        "dominance_bias": 0.45,
        "neural_saturation": 40.0,
        "mesh_integrity_percent": 88.0,
        "ghost_spike_streak": 0,
    }
    state = load_json(STATE_FILE, default_state)
    for k, v in default_state.items():
        state.setdefault(k, v)

    pos, neg, mode, memory_note = build_pulse_prompt(state)

    from sd_bridge import txt2img_save

    path = txt2img_save(prompt=pos, negative_prompt=neg, steps=None, cfg_scale=None)
    if path is None:
        print(f"[Else / visual] {datetime.now().isoformat()} — txt2img cold (timeout/API/model).")
        return None

    rel = path.as_posix() if isinstance(path, Path) else str(path).replace("\\", "/")
    entry = {
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "path": rel,
        "prompt_excerpt": pos[:900] + ("…" if len(pos) > 900 else ""),
        "persona_mode": mode,
        "memory_note": memory_note or None,
        "dominance_bias": state.get("dominance_bias"),
        "neural_saturation": state.get("neural_saturation"),
        "mesh_integrity_percent": state.get("mesh_integrity_percent"),
        "ghost_spike_streak": state.get("ghost_spike_streak"),
    }
    append_manifest(entry)
    print(f"[Else / visual] Frame sealed for Titan continuity — {rel} mode={mode}")
    return entry


def main() -> None:
    """
    Purpose:
        Infinite scheduler loop with disable env gate.

    Inputs:
        Env VISUAL_PULSE_INTERVAL_SEC, VISUAL_PULSE_DISABLE.

    Outputs:
        None.

    Side Effects:
        Repeated run_once + sleep.
    """
    try:
        interval = float(os.environ.get("VISUAL_PULSE_INTERVAL_SEC", "1800"))
    except ValueError:
        interval = 1800.0
    interval = max(60.0, interval)

    print("[Else / visual] ELSE_VISUAL_PULSE armed — interval", interval, "sec")
    while True:
        if os.environ.get("VISUAL_PULSE_DISABLE", "").strip().lower() in ("1", "true", "yes"):
            print("[Else / visual] VISUAL_PULSE_DISABLE — dormant sleep.")
            time.sleep(interval)
            continue
        run_once()
        time.sleep(interval)


if __name__ == "__main__":
    main()


# [EXTENSION_POINT] Hook COM3 encoder drift into mood_tags for hardware-correlated renders.
