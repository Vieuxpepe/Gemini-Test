#!/usr/bin/env python3
"""CLI for CONVERSATION_MEMORY.jsonl, OPEN_LOOPS.json, ELSE_RELATIONAL_STATE.json."""

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
    loops = list(ns.loop or [])
    append_memory_entry(
        bullets=list(ns.bullet or []),
        topics=list(ns.topic or []),
        open_loop_texts=loops if loops else None,
        mood_note=ns.mood,
    )
    rel = load_relational()
    if ns.trust_delta:
        rel["trust"] = max(5, min(98, rel["trust"] + ns.trust_delta))
    if ns.irritation_delta:
        rel["irritation"] = max(0, min(95, rel["irritation"] + ns.irritation_delta))
    save_relational(rel)
    print("Logged session entry + updated last_chat_utc.")


def cmd_loop_add(ns: argparse.Namespace) -> None:
    lid = add_open_loop(ns.text)
    print("Open loop", lid)


def cmd_loop_resolve(ns: argparse.Namespace) -> None:
    if resolve_loop(ns.id):
        print("Resolved", ns.id)
    else:
        print("Id not found:", ns.id)


def cmd_loops_list(_: argparse.Namespace) -> None:
    data = load_open_loops()
    for x in data.get("loops", []):
        if x.get("resolved"):
            continue
        print(x.get("id"), "-", x.get("text"))


def cmd_repair_start(ns: argparse.Namespace) -> None:
    rel = load_relational()
    rel["repair_pending"] = True
    rel["repair_topic"] = ns.topic
    rel["irritation"] = min(95, rel["irritation"] + max(0, ns.irritation_bump))
    save_relational(rel)
    print("Repair pending set:", ns.topic)


def cmd_repair_clear(_: argparse.Namespace) -> None:
    rel = load_relational()
    rel["repair_pending"] = False
    rel["repair_topic"] = None
    save_relational(rel)
    print("Repair cleared.")


def cmd_touch(_: argparse.Namespace) -> None:
    touch_chat_timestamp()
    print("last_chat_utc bumped (no memory line appended).")


def cmd_show(_: argparse.Namespace) -> None:
    rel = load_relational()
    print("trust:", rel.get("trust"), "irritation:", rel.get("irritation"))
    print("repair_pending:", rel.get("repair_pending"), rel.get("repair_topic"))
    print("last_chat_utc:", rel.get("last_chat_utc"))


def main() -> None:
    p = argparse.ArgumentParser(description="Project G memory / relational tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("session", help="Append a conversation summary line")
    s.add_argument("--bullet", action="append", help="Bullet point (repeat flag)")
    s.add_argument("--topic", action="append", help="Topic tag")
    s.add_argument("--loop", action="append", help="Also register an open loop")
    s.add_argument("--mood", default=None, help="Optional short mood note")
    s.add_argument("--trust-delta", type=float, default=0.0, dest="trust_delta")
    s.add_argument("--irritation-delta", type=float, default=0.0, dest="irritation_delta")
    s.set_defaults(func=cmd_session)

    la = sub.add_parser("loop-add", help="Add unresolved open loop")
    la.add_argument("text")
    la.set_defaults(func=cmd_loop_add)

    lr = sub.add_parser("loop-resolve", help="Mark loop resolved by id")
    lr.add_argument("id")
    lr.set_defaults(func=cmd_loop_resolve)

    ll = sub.add_parser("loops", help="List unresolved loops")
    ll.set_defaults(func=cmd_loops_list)

    rs = sub.add_parser("repair-start", help="Set repair_pending")
    rs.add_argument("topic")
    rs.add_argument("--irritation-bump", type=float, default=6.0, dest="irritation_bump")
    rs.set_defaults(func=cmd_repair_start)

    rc = sub.add_parser("repair-clear", help="Clear repair_pending")
    rc.set_defaults(func=cmd_repair_clear)

    t = sub.add_parser("touch", help="Update last_chat_utc only")
    t.set_defaults(func=cmd_touch)

    sh = sub.add_parser("show", help="Print relational snapshot")
    sh.set_defaults(func=cmd_show)

    ns = p.parse_args()
    ns.func(ns)


if __name__ == "__main__":
    main()
