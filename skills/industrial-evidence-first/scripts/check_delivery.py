#!/usr/bin/env python3
"""Read-only quantity/source consistency gate; never an engineering certificate."""
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

UNITS = {"mm", "cm", "m", "deg", "rad", "N", "kg"}


class DeliveryError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise DeliveryError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def number(value):
    need(isinstance(value, str) and bool(re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value)),
         "value must be a finite decimal string")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise DeliveryError("invalid decimal value") from exc
    need(result.is_finite(), "non-finite decimal value")
    return result


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_keys)


def versioned(obj):
    need(isinstance(obj, dict) and type(obj.get("schema_version")) is int and obj["schema_version"] == 1,
         "expected object with schema_version 1")


def read_registry(registry, root):
    versioned(registry)
    sources = registry.get("sources")
    need(isinstance(sources, list), "sources must be an array")
    output = {}
    for source in sources:
        need(isinstance(source, dict) and {"id", "path", "sha256", "line", "quote", "fixture", "facts"} <= source.keys(),
             "source fields missing")
        sid = source["id"]
        need(text(sid) and sid not in output, "missing or duplicate source id")
        raw = source["path"]
        need(text(raw), "source path missing")
        path = PurePosixPath(raw)
        need(not path.is_absolute() and ".." not in path.parts and
             not any(c in raw for c in (":", "\\", "\x00")), "unsafe source path")
        local = (root / raw).resolve()
        need(local.is_relative_to(root) and local.is_file(), "source unavailable inside root")
        digest = source["sha256"]
        need(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "invalid source digest")
        data = local.read_bytes()
        need(hashlib.sha256(data).hexdigest() == digest, "source digest mismatch")
        line = source["line"]
        lines = data.decode("utf-8").splitlines()
        need(type(line) is int and 1 <= line <= len(lines), "invalid source line")
        need(text(source["quote"]) and source["quote"] == lines[line - 1], "source quote mismatch")
        need(type(source["fixture"]) is bool, "fixture must be boolean")
        facts = source["facts"]
        need(isinstance(facts, list) and bool(facts), "facts must be a nonempty array")
        fact_ids = set()
        for fact in facts:
            need(isinstance(fact, dict) and {"item_id", "value", "unit", "basis"} <= fact.keys(), "fact fields missing")
            fid = fact["item_id"]
            need(text(fid) and fid not in fact_ids, "missing or duplicate fact item id")
            fact_ids.add(fid)
            number(fact["value"])
            need(isinstance(fact["unit"], str) and fact["unit"] in UNITS, "unsupported fact unit")
            need(isinstance(fact["basis"], str) and fact["basis"] in {"source-stated", "measured"}, "invalid fact basis")
            if fact["basis"] == "measured":
                need(text(fact.get("method")) and isinstance(fact.get("measured_on"), str) and
                     bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", fact["measured_on"])), "measurement metadata missing")
                date.fromisoformat(fact["measured_on"])
        output[sid] = source
    return output


def validate(document, registry, root):
    root = Path(root).resolve()
    need(root.is_dir(), "root must be an existing directory")
    sources = read_registry(registry, root)
    versioned(document)
    stage = document.get("stage")
    need(isinstance(stage, str) and stage in {"draft", "release-candidate"}, "invalid stage")
    need(text(document.get("summary")), "summary must not be blank")
    items = document.get("items")
    need(isinstance(items, list) and bool(items), "items must be a nonempty array")
    seen, holds = set(), []
    for item in items:
        need(isinstance(item, dict) and {"id", "value", "unit", "status", "evidence_ids"} <= item.keys(), "item fields missing")
        ident = item["id"]
        need(text(ident) and ident not in seen, "missing or duplicate item id")
        seen.add(ident)
        status = item["status"]
        need(isinstance(status, str) and status in {"source-stated", "measured", "estimated", "unknown", "conflict"}, "invalid item status")
        refs = item["evidence_ids"]
        need(isinstance(refs, list) and all(text(r) for r in refs) and len(refs) == len(set(refs)), "invalid evidence_ids")
        need(all(r in sources for r in refs), "unresolved evidence id")
        matched = []
        for ref in refs:
            facts = [f for f in sources[ref]["facts"] if f["item_id"] == ident]
            need(bool(facts), "source has no fact for this item")
            matched.extend(facts)
        if status in {"unknown", "conflict"}:
            need(item["value"] is None and item["unit"] is None, "unknown/conflict require null value and unit")
        else:
            value = number(item["value"])
            need(isinstance(item["unit"], str) and item["unit"] in UNITS, "unsupported item unit")
            if status in {"source-stated", "measured"}:
                need(bool(matched), "supported item requires evidence")
                need(all(number(f["value"]) == value and f["unit"] == item["unit"] and f["basis"] == status for f in matched),
                     "quantity/unit/basis does not match pinned facts")
        if status in {"estimated", "unknown", "conflict"}:
            need(text(item.get("notes")), "unresolved or estimated item requires notes")
            holds.append("unresolved-or-estimated-item")
        if status == "conflict":
            need(len({(number(f["value"]), f["unit"]) for f in matched}) >= 2,
                 "conflict requires differing source facts")
        if any(sources[r]["fixture"] for r in refs):
            holds.append("synthetic-evidence")
    if stage == "draft":
        holds.append("draft-stage")
    return {"structural_ok": True, "items_checked": len(items), "sources_checked": len(sources),
            "evidence_gate": "hold" if holds else "pass", "hold_reasons": sorted(set(holds)),
            "engineering_certified": False, "publication_authorized": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document", type=Path)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--require-gate", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(load_json(args.document), load_json(args.registry), args.root)
    except (DeliveryError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"structural_ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 2 if args.require_gate and result["evidence_gate"] != "pass" else 0


if __name__ == "__main__":
    sys.exit(main())
