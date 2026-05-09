# =============================================================================
# Purpose:
#   HTTP bridge from Project G automation to Automatic1111 txt2img API — renders
#   visual handshake artifacts aligned with The Else persona (README canon).
#
# Overall Goal:
#   Deterministic, observable image generation with explicit tuning knobs for
#   RTX-class GPUs and SDXL checkpoints; zero silent failure modes beyond None.
#
# Project Context (Legends of Aurelia / The Else):
#   Marc-Antoine Authier’s workshop stack (Trois-Rivières): visualization loop
#   supports the Titan Schema / obsidian-machine narrative used in prompts.
#   Godot title *Legends of Aurelia* is engineering continuity for the operator.
#
# Dependencies:
#   stdlib: base64, json, os, urllib (Automatic1111 @ SD_API_URL with --api).
#   External runtime: local Web UI listening on SD_API_URL (default :7860).
# =============================================================================
"""
Stable Diffusion Web UI bridge — configuration surface documented in module header.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# --- [CONFIG_ZONE] Default checkpoint label MUST mirror A1111 dropdown exactly ---
DEFAULT_CHECKPOINT = "waiIllustriousSDXL_v160.safetensors [a5f58eb1c3]"

# --- [CONFIG_ZONE] RTX 4060–class tuned defaults (override via env) ---
DEFAULT_STEPS = 30
DEFAULT_CFG = 7.0
DEFAULT_SAMPLER = "DPM++ 2M"
DEFAULT_SCHEDULER = "Karras"
DEFAULT_CLIP_SKIP = 2
SDXL_DEFAULT_WIDTH = 512
SDXL_DEFAULT_HEIGHT = 1024


def _env_bool(key: str, default: bool = False) -> bool:
    """
    Purpose:
        Parse boolean-like environment variables with explicit token gates.

    Inputs:
        key (str): Environment variable name.
        default (bool): Fallback when unset or unrecognized.

    Outputs:
        bool: Resolved truth value.

    Side Effects:
        None (read-only os.environ).
    """
    # [CORE_LOGIC] Gate 1: strip + lowercase for case-folding (precision: full string match).
    v = os.environ.get(key, "").strip().lower()
    # [CORE_LOGIC] Gate 2: affirmative token set — union of {"1","true","yes","on"}.
    if v in ("1", "true", "yes", "on"):
        return True
    # [CORE_LOGIC] Gate 3: negative token set — union of {"0","false","no","off"}.
    if v in ("0", "false", "no", "off"):
        return False
    # [CORE_LOGIC] Gate 4: default branch — unrecognized → default (no coercion).
    return default


def _default_dims_for_checkpoint(checkpoint: str) -> tuple[int, int]:
    """
    Purpose:
        Resolve (width, height) with SDXL heuristic vs explicit env override.

    Inputs:
        checkpoint (str): Checkpoint dropdown string; "SDXL" substring triggers SDXL bucket.

    Outputs:
        tuple[int, int]: (width, height), both ≥ 64 implicitly by downstream API.

    Side Effects:
        None.
    """
    # [CORE_LOGIC] Gate A: SD_WIDTH & SD_HEIGHT BOTH present → int parse; invalid → fall through.
    w_env, h_env = os.environ.get("SD_WIDTH"), os.environ.get("SD_HEIGHT")
    if w_env and h_env:
        try:
            return int(w_env), int(h_env)
        except ValueError:
            pass
    # [CORE_LOGIC] Gate B: substring "SDXL" (casefold) → SDXL_DEFAULT_* tuple.
    u = checkpoint.upper()
    if "SDXL" in u:
        return SDXL_DEFAULT_WIDTH, SDXL_DEFAULT_HEIGHT
    # [CORE_LOGIC] Gate C: fallback square 512 for non-SDXL-named checkpoints.
    return 512, 512


def txt2img_save(
    prompt: str,
    negative_prompt: str = "",
    steps: int | None = None,
    width: int | None = None,
    height: int | None = None,
    cfg_scale: float | None = None,
    sampler_name: str | None = None,
    checkpoint: str | None = None,
) -> Path | None:
    """
    Purpose:
        POST /sdapi/v1/txt2img and persist first returned image to sd_outputs/.

    Inputs:
        prompt (str): Positive prompt text.
        negative_prompt (str): Negative prompt text.
        steps (int | None): Sampling steps; None → env SD_STEPS or DEFAULT_STEPS.
        width (int | None): Pixel width; None → heuristic/env.
        height (int | None): Pixel height; None → heuristic/env.
        cfg_scale (float | None): CFG; None → env SD_CFG or DEFAULT_CFG.
        sampler_name (str | None): A1111 sampler name; None → env or DEFAULT_SAMPLER.
        checkpoint (str | None): Override checkpoint string; None → env or DEFAULT_CHECKPOINT.

    Outputs:
        pathlib.Path | None: Saved PNG path on success; None on any failure path.

    Side Effects:
        Network I/O to SD_API_URL; writes PNG under SD_OUTPUT_DIR; may mutate A1111
        runtime via override_settings (checkpoint + CLIP layers).
    """
    # [AI_ENTRY_POINT] Primary automation entry for Else visual synthesis loop.
    ckpt = (checkpoint or os.environ.get("SD_CHECKPOINT") or DEFAULT_CHECKPOINT).strip()
    dw, dh = _default_dims_for_checkpoint(ckpt)
    # [CORE_LOGIC] Dimension merge: explicit args beat heuristic resolution.
    width = dw if width is None else width
    height = dh if height is None else height
    # [CORE_LOGIC] Steps merge: env SD_STEPS → int; ValueError → DEFAULT_STEPS (30).
    if steps is None:
        try:
            steps = int(os.environ.get("SD_STEPS", str(DEFAULT_STEPS)))
        except ValueError:
            steps = DEFAULT_STEPS
    # [CORE_LOGIC] CFG merge: env SD_CFG → float; ValueError → DEFAULT_CFG (7.0).
    if cfg_scale is None:
        try:
            cfg_scale = float(os.environ.get("SD_CFG", str(DEFAULT_CFG)))
        except ValueError:
            cfg_scale = DEFAULT_CFG
    # [CORE_LOGIC] Sampler merge: empty env → DEFAULT_SAMPLER ("DPM++ 2M").
    if sampler_name is None:
        sampler_name = os.environ.get("SD_SAMPLER", DEFAULT_SAMPLER).strip() or DEFAULT_SAMPLER
    # [CORE_LOGIC] CLIP skip clamp: domain [1, 12] inclusive (10-bit intent: hard bounds).
    try:
        clip_skip = int(os.environ.get("SD_CLIP_SKIP", str(DEFAULT_CLIP_SKIP)))
    except ValueError:
        clip_skip = DEFAULT_CLIP_SKIP
    clip_skip = max(1, min(12, clip_skip))

    base = os.environ.get("SD_API_URL", "http://127.0.0.1:7860").rstrip("/")
    url = f"{base}/sdapi/v1/txt2img"
    body = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "width": width,
        "height": height,
        "cfg_scale": cfg_scale,
        "sampler_name": sampler_name,
        "enable_hr": _env_bool("SD_ENABLE_HR", False),
    }
    # [CORE_LOGIC] Scheduler injection gate: non-empty SD_SCHEDULER → body["scheduler"].
    sched = os.environ.get("SD_SCHEDULER", DEFAULT_SCHEDULER).strip()
    if sched:
        body["scheduler"] = sched

    override: dict = {"CLIP_stop_at_last_layers": clip_skip}
    # [CORE_LOGIC] Checkpoint override gate: ckpt truthy AND NOT SD_USE_UI_CHECKPOINT → inject sd_model_checkpoint.
    if ckpt and not _env_bool("SD_USE_UI_CHECKPOINT", False):
        override["sd_model_checkpoint"] = ckpt
    body["override_settings"] = override
    body["override_settings_restore_afterwards"] = _env_bool(
        "SD_OVERRIDE_RESTORE_AFTERWARDS", False
    )

    try:
        timeout = float(os.environ.get("SD_TIMEOUT_SEC", "1200"))
    except ValueError:
        timeout = 1200.0

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # [CORE_LOGIC] Network gate: URLError | HTTPError | TimeoutError | JSONDecodeError → None (fail-closed).
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    images = payload.get("images") or []
    # [CORE_LOGIC] Empty images array gate → None (API returned success-shaped junk).
    if not images:
        return None

    raw = base64.b64decode(images[0])
    out_dir = Path(os.environ.get("SD_OUTPUT_DIR", "sd_outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"else_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    path = out_dir / name
    path.write_bytes(raw)
    return path


# [EXTENSION_POINT] Future: img2img, controlnet payload adapters, or Forge-specific routes.
