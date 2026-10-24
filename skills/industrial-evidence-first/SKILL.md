---
name: industrial-evidence-first
license: MIT
description: Review technical quantity tables using explicit units, pinned source records and unresolved-gap tracking. Use for evidence gates on engineering documents; it does not validate CAD geometry or certify manufacturing.
---

# Technical evidence gates

Separate a document's proposed values, source statements, measurements, estimates and unresolved conflicts. Keep units explicit; absent unit evidence remains unknown. Preserve assumptions and conflicting sources instead of silently choosing a convenient answer.

Use source records that were reviewed independently of the candidate document. Pin their local bytes and exact passages. A producer's self-authored registry does not become trusted merely because a validator accepts its shape.

Keep document preparation, source consistency, geometric checks, simulation, physical measurement and final acceptance as separate conclusions. Source-code coordinates do not establish a CAD solid, a simulation does not establish a physical test, and a supplier statement does not establish current inventory or certified precision.

For a small quantity-table gate, read [delivery-format.md](references/delivery-format.md) and run:

```bash
python3 scripts/check_delivery.py delivery.json --registry registry.json --root evidence-directory
```

The tool checks required content, finite decimal values, supported units, pinned local passages and value/source bindings. Unknown, conflicting, estimated or synthetic-only entries hold the evidence gate. A draft never passes it. Passing this limited gate is not permission to publish or manufacture and does not certify safety, geometry or accuracy.

Retain failed checks and older versions. Correct the candidate or acquire better evidence; do not alter source records or historical model output merely to obtain a passing label. Do not execute untrusted source files to extract dimensions. This skill grants no training, external-service or publication authorization.
