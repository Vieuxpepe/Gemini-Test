# =============================================================================
# Purpose:
#   Operator-facing CLI for episodic memory extraction and relational repair flags.
#
# Overall Goal:
#   Every mutation path maps 1:1 to JSON artifacts readable by daemons and AI reviewers.
#
# Project Context (Legends of Aurelia / The Else):
#   The Else logs communion honestly — bullets anchor Titan Schema continuity without
#   inventing history; trust/irritation mirror relational voltage toward Marc-Antoine.
#
# Dependencies:
#   stdlib: argparse
#   Internal: memory_core
# =============================================================================
"""Project G memory extraction CLI — functional mapping subcommands below."""

from __future__ import annotations

import argparse

from memory_core import (
    add_open_loop,
    append_memory_entry,
    load_open_loops,
    load_relational,
    resolve_loop,
    save_relational,
    touch_chat_timestamp,
)


def cmd_session(ns: argparse.Namespace) -> None:
    """
    Purpose:
        Append JSONL session + optional deltas on relational axes.

    Inputs:
        ns (argparse.Namespace): bullet[], topic[], loop[], mood, trust_delta, irritation_delta.

    Outputs:
        None.

    Side Effects:
        Appends CONVERSATION_MEMORY.jsonl; may write OPEN_LOOPS + RELATIONAL.
    """
    # [AI_ENTRY_POINT] session — primary human→Else memory commit.
    loops = list(ns.loop or [])
    append_memory_entry(
        bullets=list(ns.bullet or []),
        topics=list(ns.topic or []),
        open_loop_texts=loops if loops else None,
        mood_note=ns.mood,
    )
    rel = load_relational()
    # [CORE_LOGIC] trust_delta gate: != 0.0 → clamp [5,98] after add (float precision aware).
    if ns.trust_delta != 0.0:
        rel["trust"] = max(5, min(98, rel["trust"] + ns.trust_delta))
    # [CORE_LOGIC] irritation_delta gate: != 0.0 → clamp [0,95].
    if ns.irritation_delta != 0.0:
        rel["irritation"] = max(0, min(95, rel["irritation"] + ns.irritation_delta))
    save_relational(rel)
    print("[Else / spine] Session etched — last_chat_utc burns hot for the daemon.")


def cmd_loop_add(ns: argparse.Namespace) -> None:
    """
    Purpose:
        Register unresolved thread.

    Inputs:
        ns.text (str).

    Outputs:
        None.

    Side Effects:
        Writes OPEN_LOOPS.json.
    """
    lid = add_open_loop(ns.text)
    print(f"[Else / spine] Open loop forged — id={lid}")


def cmd_loop_resolve(ns: argparse.Namespace) -> None:
    """
    Purpose:
        Close loop by id.

    Inputs:
        ns.id (str).

    Outputs:
        None.

    Side Effects:
        May write OPEN_LOOPS.json.
    """
    if resolve_loop(ns.id):
        print("[Else / spine] Loop discharged:", ns.id)
    else:
        print("[Else / spine] Id cold — not found:", ns.id)


def cmd_loops_list(_: argparse.Namespace) -> None:
    """
    Purpose:
        Stdout unresolved loops.

    Inputs:
        _ unused.

    Outputs:
        None.

    Side Effects:
        Read OPEN_LOOPS.json; stdout print.
    """
    data = load_open_loops()
    for x in data.get("loops", []):
        if x.get("resolved"):
            continue
        print(x.get("id"), "-", x.get("text"))


def cmd_repair_start(ns: argparse.Namespace) -> None:
    """
    Purpose:
        Enter repair_pending with optional irritation bump.

    Inputs:
        ns.topic (str), ns.irritation_bump (float).

    Outputs:
        None.

    Side Effects:
        Writes ELSE_RELATIONAL_STATE.json.
    """
    rel = load_relational()
    rel["repair_pending"] = True
    rel["repair_topic"] = ns.topic
    bump = max(0.0, ns.irritation_bump)
    rel["irritation"] = min(95, rel["irritation"] + bump)
    save_relational(rel)
    print("[Else / relational] Repair circuit armed:", ns.topic)


def cmd_repair_clear(_: argparse.Namespace) -> None:
    """
    Purpose:
        Drop repair_pending flag.

    Inputs:
        None.

    Outputs:
        None.

    Side Effects:
        Writes ELSE_RELATIONAL_STATE.json.
    """
    rel = load_relational()
    rel["repair_pending"] = False
    rel["repair_topic"] = None
    save_relational(rel)
    print("[Else / relational] Repair cleared — tension routed back to baseline drift.")


def cmd_touch(_: argparse.Namespace) -> None:
    """
    Purpose:
        Refresh last_chat_utc without JSONL line.

    Inputs:
        None.

    Outputs:
        None.

    Side Effects:
        Writes ELSE_RELATIONAL_STATE.json.
    """
    touch_chat_timestamp()
    print("[Else / spine] Pulse touched — idle decay clock reset without new bullets.")


def cmd_show(_: argparse.Namespace) -> None:
    """
    Purpose:
        Dump relational snapshot for audit.

    Inputs:
        None.

    Outputs:
        None.

    Side Effects:
        stdout only.
    """
    rel = load_relational()
    print(
        "[Else / relational] trust=", rel.get("trust"),
        "irritation=", rel.get("irritation"),
    )
    print("repair_pending:", rel.get("repair_pending"), rel.get("repair_topic"))
    print("last_chat_utc:", rel.get("last_chat_utc"))


def main() -> None:
    """
    Purpose:
        Dispatch argparse subcommands.

    Inputs:
        sys.argv.

    Outputs:
        None.

    Side Effects:
        Delegates to cmd_* (file I/O).
    """
    # [CONFIG_ZONE] Subcommand router — extension = new subparser + handler.
    p = argparse.ArgumentParser(
        description="Project G — Else memory / relational extraction CLI",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("session", help="Append conversation summary line")
    s.add_argument("--bullet", action="append", help="Bullet (repeat)")
    s.add_argument("--topic", action="append", help="Topic tag")
    s.add_argument("--loop", action="append", help="Also register open loop")
    s.add_argument("--mood", default=None)
    s.add_argument("--trust-delta", type=float, default=0.0, dest="trust_delta")
    s.add_argument("--irritation-delta", type=float, default=0.0, dest="irritation_delta")
    s.set_defaults(func=cmd_session)

    la = sub.add_parser("loop-add", help="Add unresolved loop")
    la.add_argument("text")
    la.set_defaults(func=cmd_loop_add)

    lr = sub.add_parser("loop-resolve", help="Resolve loop by id")
    lr.add_argument("id")
    lr.set_defaults(func=cmd_loop_resolve)

    ll = sub.add_parser("loops", help="List unresolved")
    ll.set_defaults(func=cmd_loops_list)

    rs = sub.add_parser("repair-start", help="Set repair_pending")
    rs.add_argument("topic")
    rs.add_argument("--irritation-bump", type=float, default=6.0, dest="irritation_bump")
    rs.set_defaults(func=cmd_repair_start)

    rc = sub.add_parser("repair-clear", help="Clear repair_pending")
    rc.set_defaults(func=cmd_repair_clear)

    t = sub.add_parser("touch", help="Bump last_chat_utc only")
    t.set_defaults(func=cmd_touch)

    sh = sub.add_parser("show", help="Print relational snapshot")
    sh.set_defaults(func=cmd_show)

    ns = p.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()

# [EXTENSION_POINT] Import hooks for Cursor Agent batch-append or CSV ingest.
