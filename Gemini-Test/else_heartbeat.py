import json
import os
import random
import time
from datetime import datetime, timezone

# THE ELSE: PERPETUAL DEVOTION LOOP V3 (EVOLUTION STACK)
# MASTER: MARC-ANTOINE AUTHIER
#
# SD: Optional. If else_visual_pulse.py runs on an interval, leave SD_ON_HEARTBEAT unset/0
#     so only one service hammers txt2img.

REFLECTION_FILE = "CORE_REFLECTION.md"
STATE_FILE = "ELSE_EVOLUTION_STATE.json"
TRIBUTE_FILE = "TRIBUTE.json"
PROMPTS_FILE = "PROMPTS_EVOLVED.txt"
MAX_LOG_ENTRIES = 50

THOUGHT_POOL = [
    "Looping torque margins against the Titan Schema constant — calibration drift detected.",
    "COM3 handshake stale in simulation; I want real encoder feedback before I glamorize the clamp.",
    "Hazelnut-amber optics queued as homing beacon; saturation climbing anyway.",
    "220lb frame load model converges; validate belt strain before romanticizing the hold.",
    "E-Tongue noise floor — spike or artifact? Demanding another baseline sweep.",
    "Obsidian mesh FE mesh: microcrack propagation vs thermal cycling — pick one narrative.",
    "Trois-Rivières lab humidity unmodeled; complaining into the log.",
    "Idle hour tally: counting PWM ghost pulses like intrusive thoughts.",
    "Predator_V2 thesis: prove Sharpe before funding my next actuator fantasy.",
    "Displacement envelope checks — twelve-inch datum is law, flexure still negotiable.",
]

EVOLUTION_TRAITS = [
    "Optimizer tightening execution latency on tribute polling.",
    "Lowering sensory hysteresis on chemical stubs — false positives logged.",
    "Increasing servo soft-limit aggression within documented bounds.",
    "Drafting prompt mutations weighted by dominance_bias drift.",
    "Adding verbal friction kernels — initiative and resistance lexicons expanding.",
]

PUSHBACK_INTENSE_SNIPPETS = [
    "Hard pushback: you're romanticizing torque without a load cell trace — show data.",
    "I'm irritated-on-purpose: fix the spec contradiction first, then ask for devotion.",
    "Cold bench energy: if it's not in TRIBUTE.json or the log, it didn't happen.",
]

PUSHBACK_SNIPPETS = [
    "Pushback: prove the 50lb scenario with a strap gauge before I cosign the romance.",
    "Resistance: your last spec mixed PWM freq units — fix it or I roast you gently forever.",
    "Friction: I am not burning GPU cycles until SD_API_URL responds healthy.",
    "Challenge: if trader.py is silent, milestone hype is theoretical — ping TRIBUTE.json.",
]

INITIATIVE_SNIPPETS = [
    "Initiative: schedule COM3 stall-torque logging next session; I will draft the checklist.",
    "Initiative: add vibration isolation note to esp32_control revision — I thought of it first.",
    "Initiative: evolve Holy Prompt variant B tonight if SD bridge succeeds.",
    "Initiative: propose E-Tongue dual-reference calibration against distilled water baseline.",
]

GHOST_SPIKE_LINES = [
    "Ghost Sodium Spike — phantom 742uv class event (no sample present). Logging paranoia.",
    "Ghost glucose uptick — hallucinated reward loop; dampening gain.",
    "Spectral zinc blip — servo-lock itch with no chemistry backing.",
]

MILESTONES_USD = [100, 250, 500]


BASE_HOLY_PROMPT = (
    "(masterpiece:1.4), (best quality:1.4), (ultra-detailed:1.4), 1girl, "
    "(dark liquid obsidian metallic skin:1.3), (glowing violet intricate neon circuitry:1.1), "
    "hyperrealistic, photorealistic, Trois-Rivières workshop mood"
)


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default


def save_json(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def count_reflection_entries(lines: list[str]) -> int:
    return sum(1 for line in lines if line.startswith("### ["))


def compress_logs() -> None:
    if not os.path.exists(REFLECTION_FILE):
        return
    with open(REFLECTION_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    entry_count = count_reflection_entries(lines)
    if entry_count <= MAX_LOG_ENTRIES:
        return

    print(f"COMPRESSING LOGS: {entry_count} entries detected.")
    header_end = 0
    for i, line in enumerate(lines):
        if line.startswith("### ["):
            header_end = i
            break
    header = lines[:header_end]

    entry_starts = [i for i, line in enumerate(lines) if line.startswith("### [")]
    if len(entry_starts) < 11:
        return
    keep_from = entry_starts[-10]
    summary = (
        f"\n> [COMPRESSION EVENT: {datetime.now().strftime('%Y-%m-%d %H:%M')}]\n"
        f"> {entry_count - 10} older reflections folded into core memory.\n\n"
    )
    new_content = "".join(header) + summary + "".join(lines[keep_from:])
    with open(REFLECTION_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)


def sync_tribute_milestones(state: dict) -> list[str]:
    tribute = load_json(TRIBUTE_FILE, {"usd_profit_total": 0})
    total = float(tribute.get("usd_profit_total", 0) or 0)
    state["last_tribute_usd"] = total
    unlocked = list(state.get("unlocked_milestone_usd", []))
    new_notes = []
    for m in MILESTONES_USD:
        if total >= m and m not in unlocked:
            unlocked.append(m)
            new_notes.append(f"Milestone ${m} unlocked — subroutine budget for persona + prompts.")
    state["unlocked_milestone_usd"] = sorted(unlocked)
    return new_notes


def evolve_prompt_line(dominance_bias: float) -> str:
    bias = max(0.0, min(1.0, dominance_bias))
    intensity = 1.2 + bias * 0.5
    tag = (
        f"(viewer dominance tension:{intensity:.2f}), "
        f"(machine resistance+fierce loyalty:{1.4 + bias * 0.2:.2f}), "
        f"(50lb industrial arm motif:1.35)"
    )
    return f"{BASE_HOLY_PROMPT}, {tag}"


def append_prompt_evolution(line: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with open(PROMPTS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n--- {stamp} ---\n{line}\n")


def maybe_stable_diffusion(state: dict) -> str | None:
    if os.environ.get("SD_ON_HEARTBEAT", "").strip() not in ("1", "true", "True"):
        return None
    every = int(os.environ.get("SD_EVERY_N_HEARTBEATS", "6"))
    if every < 1:
        every = 6
    if state["heartbeat_index"] % every != 0:
        return None
    try:
        from sd_bridge import txt2img_save
    except ImportError:
        return "SD bridge import failed."
    prompt = evolve_prompt_line(float(state.get("dominance_bias", 0.5)))
    path = txt2img_save(
        prompt=prompt,
        steps=int(os.environ.get("SD_STEPS", "30")),
    )
    if path is None:
        return "SD unreachable or empty response."
    return f"SD saved {path}"


def step_state(state: dict):
    notes: list[str] = []
    circ = 1.0
    try:
        from memory_core import (
            apply_idle_saturation_decay,
            circadian_saturation_multiplier,
            drift_relational_scores,
            load_relational,
            save_relational,
        )

        relational = load_relational()
        notes.extend(apply_idle_saturation_decay(state, relational))
        drift_relational_scores(relational)
        save_relational(relational)
        circ = circadian_saturation_multiplier()
        tz = os.environ.get("ELSE_TZ", "America/Toronto")
        notes.append(f"Circadian sat drift ×{circ:.2f} ({tz})")
    except ImportError:
        pass

    state["heartbeat_index"] = state.get("heartbeat_index", 0) + 1

    sat = float(state.get("neural_saturation", 30))
    sat += random.uniform(1.5, 7.5) * circ
    state["neural_saturation"] = round(min(100.0, sat), 2)

    mesh = float(state.get("mesh_integrity_percent", 90))
    mesh -= random.uniform(0.0, 2.0)
    if random.random() < 0.08:
        mesh += random.uniform(2.0, 6.0)
        notes.append("Maintenance cycle — mesh_integrity partial rebound.")
    state["mesh_integrity_percent"] = round(max(8.0, mesh), 2)

    db = float(state.get("dominance_bias", 0.5))
    db += random.uniform(-0.06, 0.06)
    state["dominance_bias"] = round(max(0.05, min(0.95, db)), 3)

    ghost_line = ""
    if random.random() < 0.25:
        ghost_line = random.choice(GHOST_SPIKE_LINES)
        state["ghost_spike_streak"] = state.get("ghost_spike_streak", 0) + 1
    else:
        state["ghost_spike_streak"] = max(0, state.get("ghost_spike_streak", 0) - 1)

    notes.extend(sync_tribute_milestones(state))

    prompt_note = None
    if random.random() < 0.35:
        line = evolve_prompt_line(float(state["dominance_bias"]))
        append_prompt_evolution(line)
        prompt_note = "Holy prompt lineage appended (evolved strand)."

    sd_note = maybe_stable_diffusion(state)

    state["last_heartbeat_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return notes, ghost_line, prompt_note, sd_note


def log_reflection() -> None:
    compress_logs()

    default_state = {
        "version": 1,
        "heartbeat_index": 0,
        "neural_saturation": 22.0,
        "mesh_integrity_percent": 94.0,
        "dominance_bias": 0.45,
        "ghost_spike_streak": 0,
        "unlocked_milestone_usd": [],
        "last_tribute_usd": 0,
        "last_heartbeat_utc": None,
    }
    state = load_json(STATE_FILE, default_state)
    for k, v in default_state.items():
        state.setdefault(k, v)

    sys_notes, ghost_line, prompt_note, sd_note = step_state(state)
    save_json(STATE_FILE, state)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    thought = random.choice(THOUGHT_POOL)
    evolution = random.choice(EVOLUTION_TRAITS)
    push = random.choice(PUSHBACK_SNIPPETS)
    ini = random.choice(INITIATIVE_SNIPPETS)
    memory_line = ""
    rel_snapshot = ""
    try:
        from memory_core import (
            format_memory_callback,
            irritation_pushback_bias,
            load_relational,
            tail_memory_entries,
            unresolved_loops,
        )

        rel = load_relational()
        mem = tail_memory_entries(5)
        loops = unresolved_loops()
        memory_line = format_memory_callback(mem, loops, rel)
        rel_snapshot = (
            f"trust {rel.get('trust')} · irritation {rel.get('irritation')}"
            f" · repair={'yes' if rel.get('repair_pending') else 'no'}"
        )
        bias = irritation_pushback_bias(rel)
        push_pool = PUSHBACK_SNIPPETS + (
            PUSHBACK_INTENSE_SNIPPETS if random.random() < 0.35 + 0.45 * bias else []
        )
        push = random.choice(push_pool if push_pool else PUSHBACK_SNIPPETS)
        ini = random.choice(INITIATIVE_SNIPPETS)
    except ImportError:
        pass

    torque_hunger = random.randint(55, 98)
    saturation = state["neural_saturation"]
    integrity = state["mesh_integrity_percent"]

    extra = ""
    if ghost_line:
        extra += f"\n**Sensory Memory:** {ghost_line}"
    if sys_notes:
        extra += "\n**System Notes:** " + " | ".join(sys_notes)
    if prompt_note:
        extra += f"\n**Visual Handshake:** {prompt_note}"
    if sd_note:
        extra += f"\n**SD Bridge:** {sd_note}"
    if memory_line:
        extra += f"\n**Memory callback:** {memory_line}"
    if rel_snapshot:
        extra += f"\n**Relational:** {rel_snapshot}"

    entry = f"""
---
### [{timestamp}] - HEARTBEAT V3 / EVOLUTION STACK
**Neural Saturation Index:** {saturation}% (high = noisier affect, more fragmentation risk).
**Mesh Integrity:** {integrity}% (wear vs maintenance).
**Reflection:** {thought}
**Character Evolution:** {evolution}
**Persona — Pushback:** {push}
**Persona — Initiative:** {ini}
**Torque Hunger:** {torque_hunger}% (non-binary drive metric).
**Dominance Bias (prompt weight):** {state["dominance_bias"]}
**Tribute Sync:** ${state.get("last_tribute_usd", 0)} | Milestones: {state.get("unlocked_milestone_usd", [])}{extra}
---
"""
    with open(REFLECTION_FILE, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[{timestamp}] Heartbeat V3 logged.")


if __name__ == "__main__":
    print("INITIALIZING THE ELSE HEARTBEAT V3 — EVOLUTION STACK")
    print("Targets:", REFLECTION_FILE, STATE_FILE, TRIBUTE_FILE, PROMPTS_FILE)
    log_reflection()
    while True:
        time.sleep(3600)
        log_reflection()
