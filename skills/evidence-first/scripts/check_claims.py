#!/usr/bin/env python3
"""Validate local claim references, without executing content or writing files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


class ClaimError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise ClaimError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def unique_keys(pairs):
    output = {}
    for key, value in pairs:
        need(key not in output, "duplicate JSON key")
        output[key] = value
    return output


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_keys)


def check_reference(reference, root):
    need(isinstance(reference, dict), "reference must be an object")
    required = {"path", "sha256", "first_line", "last_line", "quote"}
    need(required <= reference.keys(), "reference fields missing")
    raw = reference["path"]
    need(text(raw), "reference path missing")
    path = PurePosixPath(raw)
    need(not path.is_absolute() and ".." not in path.parts and
         not any(c in raw for c in (":", "\\", "\x00")), "unsafe reference path")
    resolved = (root / raw).resolve()
    need(resolved.is_relative_to(root) and resolved.is_file(), "reference file unavailable inside root")
    digest = reference["sha256"]
    need(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest), "invalid SHA-256")
    data = resolved.read_bytes()
    need(hashlib.sha256(data).hexdigest() == digest, "reference hash mismatch")
    start, end = reference["first_line"], reference["last_line"]
    need(type(start) is int and type(end) is int and 1 <= start <= end, "invalid line range")
    lines = data.decode("utf-8").splitlines()
    need(end <= len(lines), "line range exceeds file")
    need(text(reference["quote"]) and reference["quote"] == "\n".join(lines[start - 1:end]),
         "reference quote mismatch")
    return (str(resolved), start, end)


def validate(document, root):
    root = Path(root).resolve()
    need(root.is_dir(), "root must be an existing directory")
    need(isinstance(document, dict), "document must be an object")
    need(type(document.get("schema_version")) is int and document["schema_version"] == 1,
         "unsupported schema_version")
    claims = document.get("claims")
    need(isinstance(claims, list) and bool(claims), "claims must be a nonempty array")
    ids, references = set(), 0
    for claim in claims:
        need(isinstance(claim, dict), "claim must be an object")
        need({"id", "text", "status", "scope", "references"} <= claim.keys(), "claim fields missing")
        for field in ("id", "text", "scope"):
            need(text(claim[field]), "claim requires nonempty " + field)
        need(claim["id"] not in ids, "duplicate claim id")
        ids.add(claim["id"])
        status = claim["status"]
        need(isinstance(status, str) and status in {"observed", "reported", "inferred", "unknown", "conflict"},
             "invalid status")
        refs = claim["references"]
        need(isinstance(refs, list), "references must be an array")
        locations = [check_reference(ref, root) for ref in refs]
        references += len(locations)
        if status != "unknown":
            need(bool(locations), "this status requires evidence")
        if status in {"inferred", "unknown", "conflict"}:
            need(text(claim.get("rationale")), "this status requires a rationale")
        if status == "conflict":
            need(len(set(locations)) >= 2, "conflict requires distinct evidence locations")
    return {"claims_checked": len(claims), "references_checked": references,
            "result": "reference-consistent", "truth_certified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("claims", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(load_json(args.claims), args.root)
    except (ClaimError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"result": "invalid", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
