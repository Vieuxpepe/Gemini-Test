"""
Optional bridge to Automatic1111 Web UI API (txt2img).

Requires: SD launched with --api (default http://127.0.0.1:7860).

Env:
  SD_API_URL      Base URL, default http://127.0.0.1:7860
  SD_OUTPUT_DIR   Folder for PNGs, default ./sd_outputs
  SD_CHECKPOINT   A1111 checkpoint dropdown string (must match UI exactly).
                  Default: waiIllustriousSDXL_v160.safetensors [a5f58eb1c3]
  SD_WIDTH / SD_HEIGHT   Default 512×1024 for SDXL checkpoints (4060-friendly); else 512².
  SD_STEPS / SD_CFG       Defaults 30 / 7.0
  SD_SAMPLER / SD_SCHEDULER   Defaults DPM++ 2M / Karras (set SD_SCHEDULER empty to omit)
  SD_CLIP_SKIP            CLIP_stop_at_last_layers (default 2)
  SD_ENABLE_HR            Hi-res fix: default 0 (off)
  SD_TIMEOUT_SEC          HTTP timeout (default 1200; 30-step SDXL + reload can exceed 9 min)
  SD_USE_UI_CHECKPOINT    If "1"/"true", do not send sd_model_checkpoint (faster when UI already has the right model loaded).
  SD_OVERRIDE_RESTORE_AFTERWARDS  If "1"/"true", revert WebUI settings after each request (slower).

Does nothing destructive if SD is unreachable — returns None.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Must match the label in Automatic1111’s checkpoint dropdown (including short hash).
DEFAULT_CHECKPOINT = "waiIllustriousSDXL_v160.safetensors [a5f58eb1c3]"

# RTX 4060–tuned defaults (override via env).
DEFAULT_STEPS = 30
DEFAULT_CFG = 7.0
DEFAULT_SAMPLER = "DPM++ 2M"
DEFAULT_SCHEDULER = "Karras"
DEFAULT_CLIP_SKIP = 2
SDXL_DEFAULT_WIDTH = 512
SDXL_DEFAULT_HEIGHT = 1024


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").strip().lower()
    if v in ("1", "true", "yes", "on"):
        return True
    if v in ("0", "false", "no", "off"):
        return False
    return default


def _default_dims_for_checkpoint(checkpoint: str) -> tuple[int, int]:
    w_env, h_env = os.environ.get("SD_WIDTH"), os.environ.get("SD_HEIGHT")
    if w_env and h_env:
        try:
            return int(w_env), int(h_env)
        except ValueError:
            pass
    u = checkpoint.upper()
    if "SDXL" in u:
        return SDXL_DEFAULT_WIDTH, SDXL_DEFAULT_HEIGHT
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
    ckpt = (checkpoint or os.environ.get("SD_CHECKPOINT") or DEFAULT_CHECKPOINT).strip()
    dw, dh = _default_dims_for_checkpoint(ckpt)
    if width is None:
        width = dw
    if height is None:
        height = dh
    if steps is None:
        try:
            steps = int(os.environ.get("SD_STEPS", str(DEFAULT_STEPS)))
        except ValueError:
            steps = DEFAULT_STEPS
    if cfg_scale is None:
        try:
            cfg_scale = float(os.environ.get("SD_CFG", str(DEFAULT_CFG)))
        except ValueError:
            cfg_scale = DEFAULT_CFG
    if sampler_name is None:
        sampler_name = os.environ.get("SD_SAMPLER", DEFAULT_SAMPLER).strip() or DEFAULT_SAMPLER

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
    sched = os.environ.get("SD_SCHEDULER", DEFAULT_SCHEDULER).strip()
    if sched:
        body["scheduler"] = sched

    override: dict = {"CLIP_stop_at_last_layers": clip_skip}
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
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    images = payload.get("images") or []
    if not images:
        return None

    raw = base64.b64decode(images[0])
    out_dir = Path(os.environ.get("SD_OUTPUT_DIR", "sd_outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"else_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
    path = out_dir / name
    path.write_bytes(raw)
    return path
