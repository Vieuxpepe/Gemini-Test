# Project G — AI assistant orientation (implementation map)

**Purpose:** Give another model a fast, accurate map of what exists in this repo **besides** the immutable baseline in `README.md`. Read `README.md` first for lore, hardware fantasy, trader hook, and persona tone.

This file is **additive documentation only**; it does not replace `README.md`.

---

## 1. Runtime scripts (Python)

| File | Role |
|------|------|
| `else_heartbeat.py` | Hourly loop: mutates `ELSE_EVOLUTION_STATE.json`, compresses `CORE_REFLECTION.md`, optional SD via `SD_ON_HEARTBEAT`, ingests **memory_core** (circadian multiplier, idle saturation decay, relational drift), logs **Memory callback** + **Relational** lines. Imports `memory_core` if present. |
| `else_visual_pulse.py` | Default **30 min** interval (`VISUAL_PULSE_INTERVAL_SEC`): reads evolution state, builds SD prompt from persona + `evolve_prompt_line`, optional **latest bullet** from `CONVERSATION_MEMORY.jsonl`, calls `sd_bridge.txt2img_save`, appends `sd_outputs/visual_manifest.json`. |
| `sd_bridge.py` | HTTP client for Automatic1111 **`/sdapi/v1/txt2img`**: checkpoint override, CLIP skip, DPM++ 2M / Karras, 512×1024 default for SDXL-named checkpoint, `enable_hr` false, env-driven timeouts (`SD_TIMEOUT_SEC` default **1200**), optional `SD_USE_UI_CHECKPOINT`. |
| `memory_core.py` | Episodic + relational spine: `CONVERSATION_MEMORY.jsonl`, `OPEN_LOOPS.json`, `ELSE_RELATIONAL_STATE.json`; tail parsing; append session; circadian (`ELSE_TZ`); idle saturation decay vs `last_chat_utc`; trust/irritation drift. |
| `memory_tools.py` | CLI wrapper around `memory_core` (`session`, `loop-add`, `loop-resolve`, `loops`, `repair-start`, `repair-clear`, `touch`, `show`). |

---

## 2. Data files (truth for “what the system thinks”)

| File | Role |
|------|------|
| `ELSE_EVOLUTION_STATE.json` | Numeric persona knobs: `neural_saturation`, `mesh_integrity_percent`, `dominance_bias`, `ghost_spike_streak`, tribute milestones, `heartbeat_index`, etc. Updated by heartbeat. |
| `ELSE_RELATIONAL_STATE.json` | `trust`, `irritation`, `repair_pending`, `repair_topic`, `last_chat_utc`. Updated by `memory_tools` and drifted each heartbeat. |
| `CONVERSATION_MEMORY.jsonl` | One JSON object per line; append via `memory_tools.py session`. Heartbeat/visual pulse **read tails** for callbacks / prompts. |
| `OPEN_LOOPS.json` | `{ "loops": [ { id, text, created_utc, resolved } ] }`. |
| `TRIBUTE.json` | `usd_profit_total` for milestone logic in heartbeat (stub / trader integration point). |
| `CORE_REFLECTION.md` | Human-readable log of automated “thoughts” + system notes. |
| `PROMPTS_EVOLVED.txt` | Append-only evolved prompt strands from heartbeat. |
| `sd_outputs/` | PNG outputs + `visual_manifest.json` (recent gens with `persona_mode`, state snapshot, optional `memory_note`). |

---

## 3. Persona / Cursor guidance (not executable code)

| File | Role |
|------|------|
| `ELSE_PERSONA.md` | Conversational rules: pushback, initiative, rhythm; documents visual pulse, memory CLI, relational spine. |
| `.cursor/rules/else-visual-context.mdc` | Sometimes **Read** latest manifest image + tie to state (not every reply). |
| `.cursor/rules/else-episodic-memory.mdc` | Use `CONVERSATION_MEMORY.jsonl`, relational + open loops; don’t invent memories; encourage logging substantive sessions via `memory_tools`. |

---

## 4. Environment variables (high-signal)

**Stable Diffusion:** `SD_API_URL`, `SD_CHECKPOINT`, `SD_USE_UI_CHECKPOINT`, `SD_ON_HEARTBEAT`, `SD_EVERY_N_HEARTBEATS`, `SD_STEPS`, `SD_TIMEOUT_SEC`, `SD_WIDTH`/`SD_HEIGHT`, `SD_SAMPLER`, `SD_SCHEDULER`, `SD_CLIP_SKIP`, `SD_ENABLE_HR`, `SD_OUTPUT_DIR`, `SD_OVERRIDE_RESTORE_AFTERWARDS`.

**Scheduling:** `VISUAL_PULSE_INTERVAL_SEC`, `VISUAL_PULSE_DISABLE`.

**Locale / mood:** `ELSE_TZ` (default `America/Toronto`).

---

## 5. How an AI should read this repo quickly

1. **`README.md`** — canon, tone, hardware/trader narrative.
2. **This file** — what code and JSON actually do.
3. **`ELSE_PERSONA.md`** + **`.cursor/rules/*.mdc`** — how to behave in chat vs logs.
4. **Latest lines** of `CORE_REFLECTION.md`, `CONVERSATION_MEMORY.jsonl`, `ELSE_EVOLUTION_STATE.json`, `ELSE_RELATIONAL_STATE.json` for current “mood.”
5. **`sd_outputs/visual_manifest.json`** (+ optional PNG **Read**) for last generated image metadata.

---

## 6. Gotchas

- Two SD drivers exist (**heartbeat** vs **visual pulse**); prefer **one** active so the GPU isn’t double-booked (`SD_ON_HEARTBEAT` off when pulse runs).
- First txt2img after a **checkpoint reload** can exceed older timeouts; default timeout was raised for that reason.
- **Understanding “everything”** still requires opening the cited files; this map is the index, not a full dump of their contents.
