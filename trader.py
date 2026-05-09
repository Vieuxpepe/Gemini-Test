# =============================================================================
# Purpose:
#   Simulated MEXC execution bridge — advances TRIBUTE.json toward the Trois-Rivières
#   lab capital goal while honoring extraction thresholds (README tribute narrative).
#
# Overall Goal:
#   Deterministic, auditable JSON ledger: equity curve, realized profit, reservoir for
#   lab extraction when thresholds trip — no network I/O until OPERATOR replaces stub.
#
# Project Context (Legends of Aurelia / The Else):
#   The Else routes market tribute to Marc-Antoine Authier’s lab ops; Titan Schema is
#   the symbolic datum — capital velocity feeds COM3 / E-tongue / bench upgrades.
#
# Dependencies:
#   stdlib: json, os, random, argparse, datetime
#   External (future): requests + signed MEXC REST — replace SimulatedMEXCBridge.tick().
# =============================================================================
"""Simulated Predator_V2 → TRIBUTE.json bridge — lab yield tracking."""

from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# --- [CONFIG_ZONE] ---
TRIBUTE_PATH = Path(os.environ.get("TRIBUTE_PATH", "TRIBUTE.json"))
DEFAULT_INITIAL_EQUITY = 500.0
LAB_YIELD_TARGET_USD = 25000.0
DEFAULT_EXTRACTION_THRESHOLD_USD = 500.0


@dataclass
class SimulatedTickResult:
    """Envelope for one simulated exchange tick (realized delta + equity snapshot)."""

    realized_delta_usd: float
    equity_usd: float
    extraction_events: int


class SimulatedMEXCBridge:
    """
    Purpose:
        Stand-in for PREDATOR_V2 execution against MEXC until live keys wire in.

    Inputs:
        volatility (float): Mean absolute drift scaler per tick.

    Outputs:
        Instance exposes tick() → SimulatedTickResult.

    Side Effects:
        Random draws only (deterministic seeding available via env TRADER_SEED).
    """

    def __init__(self, volatility: float = 12.5) -> None:
        self.volatility = volatility

    def tick(self, equity_usd: float) -> SimulatedTickResult:
        """
        Purpose:
            One synthetic bar — Gaussian-ish return clipped for stability.

        Inputs:
            equity_usd (float): Current simulated equity.

        Outputs:
            SimulatedTickResult: Delta realized for this tick + post equity estimate.

        Side Effects:
            Calls random.random / random.gauss.
        """
        # [CORE_LOGIC] Return draw: μ=0, σ=volatility/350 — scaled for hourly-ish micro moves.
        delta_pct = random.gauss(0.0, self.volatility / 350.0)
        delta_pct = max(-0.035, min(0.035, delta_pct))
        delta_usd = round(equity_usd * delta_pct, 4)
        new_equity = max(50.0, equity_usd + delta_usd)
        return SimulatedTickResult(
            realized_delta_usd=delta_usd,
            equity_usd=new_equity,
            extraction_events=0,
        )


def load_tribute() -> dict:
    """
    Purpose:
        Load TRIBUTE.json with schema defaults merged.

    Inputs:
        None.

    Outputs:
        dict: Tribute ledger.

    Side Effects:
        Read-only file access.
    """
    default = {
        "usd_profit_total": 0.0,
        "usd_extracted_to_lab": 0.0,
        "lab_yield_target_usd": LAB_YIELD_TARGET_USD,
        "extraction_threshold_usd": DEFAULT_EXTRACTION_THRESHOLD_USD,
        "simulated_equity_usd": DEFAULT_INITIAL_EQUITY,
        "last_tick_utc": None,
        "predator_v2_simulation": True,
        "note": "Simulated MEXC until live bridge — see trader.py",
    }
    if not TRIBUTE_PATH.exists():
        return dict(default)
    try:
        with open(TRIBUTE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(default)
        for k, v in default.items():
            data.setdefault(k, v)
        return data
    except json.JSONDecodeError:
        return dict(default)


def save_tribute(data: dict) -> None:
    """
    Purpose:
        Persist tribute ledger.

    Inputs:
        data (dict): Full tribute record.

    Outputs:
        None.

    Side Effects:
        Writes TRIBUTE_PATH (truncate).
    """
    with open(TRIBUTE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def apply_extractions(data: dict) -> int:
    """
    Purpose:
        Move accumulated profit across extraction_threshold_usd into usd_extracted_to_lab.

    Inputs:
        data (dict): Mutated ledger.

    Outputs:
        int: Number of extraction slices executed this call.

    Side Effects:
        Mutates usd_profit_total routing fields inside data; writes nothing alone.
    """
    events = 0
    threshold = float(data.get("extraction_threshold_usd", DEFAULT_EXTRACTION_THRESHOLD_USD))
    profit = float(data.get("usd_profit_total", 0.0))
    # [CORE_LOGIC] Gate E1: threshold ≤ 0 → bypass (invalid config guard).
    if threshold <= 0:
        return 0
    # [CORE_LOGIC] Gate E2: while profit ≥ threshold, peel one slab toward lab reservoir.
    while profit >= threshold - 1e-9:
        profit -= threshold
        data["usd_extracted_to_lab"] = float(data.get("usd_extracted_to_lab", 0.0)) + threshold
        events += 1
    data["usd_profit_total"] = round(max(0.0, profit), 4)
    return events


def run_tick() -> dict:
    """
    Purpose:
        Execute one simulation tick, update equity + profit, run extraction gates.

    Inputs:
        None (reads TRIBUTE_PATH).

    Outputs:
        dict: Summary echo for logs.

    Side Effects:
        Writes TRIBUTE_PATH; mutates random state.
    """
    # [AI_ENTRY_POINT] Daemon / cron friendly single step.
    if os.environ.get("TRADER_SEED"):
        random.seed(int(os.environ["TRADER_SEED"]))
    data = load_tribute()
    bridge = SimulatedMEXCBridge(volatility=float(os.environ.get("TRADER_VOL", "12.5")))
    equity = float(data.get("simulated_equity_usd", DEFAULT_INITIAL_EQUITY))
    result = bridge.tick(equity)
    data["simulated_equity_usd"] = result.equity_usd
    # [CORE_LOGIC] Profit pool: any signed delta flows into tribute reservoir (floor at 0).
    delta = result.realized_delta_usd
    pool = max(0.0, float(data.get("usd_profit_total", 0.0)) + delta)
    data["usd_profit_total"] = round(pool, 4)
    ext = apply_extractions(data)
    data["last_extraction_events"] = ext
    data["last_tick_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    target = float(data.get("lab_yield_target_usd", LAB_YIELD_TARGET_USD))
    extracted = float(data.get("usd_extracted_to_lab", 0.0))
    data["lab_yield_progress_ratio"] = round(extracted / target, 6) if target > 0 else 0.0
    save_tribute(data)
    return {
        "equity_usd": result.equity_usd,
        "delta_usd": delta,
        "profit_pool_usd": data["usd_profit_total"],
        "extracted_lab_usd": extracted,
        "extractions": ext,
        "progress_to_25k": data["lab_yield_progress_ratio"],
    }


def cmd_tick(_: argparse.Namespace) -> None:
    """CLI: single tick."""
    summary = run_tick()
    print("[Else / tribute] Tick sealed:", summary)


def cmd_status(_: argparse.Namespace) -> None:
    """CLI: print ledger without trading."""
    data = load_tribute()
    print(json.dumps(data, indent=2))


def main() -> None:
    """Argparse entry."""
    p = argparse.ArgumentParser(description="Project G — simulated MEXC ↔ TRIBUTE bridge")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tick", help="Run one simulated Predator_V2 tick")
    t.set_defaults(func=cmd_tick)
    s = sub.add_parser("status", help="Show TRIBUTE.json")
    s.set_defaults(func=cmd_status)
    ns = p.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()

# [EXTENSION_POINT] Swap SimulatedMEXCBridge for signed REST client; preserve apply_extractions().
