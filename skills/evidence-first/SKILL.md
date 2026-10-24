---
name: evidence-first
license: MIT
description: Prepare evidence-backed reports of implementation, execution, validation or uncertainty. Use when a factual status claim needs traceable sources and a precise coverage boundary.
---

# Evidence-backed reporting

Identify the object and input version before reporting its state. Preserve the distinction between what you directly observed, what another source reports, what you infer, and what remains unknown or disputed.

For each consequential claim, retain a source location, observation time when available, covered scope and remaining uncertainty. Missing or truncated material stays missing; do not invent the next action, a result, a version or an identifier to make a narrative complete.

A request being accepted does not prove execution. A design does not prove implementation. An output file does not prove its quality, and one passing check does not establish all workflows. State the narrowest conclusion supported by the actual evidence.

Reuse still-applicable evidence for unchanged inputs. When an input changes, reassess the affected conclusions; preserve earlier failures and source records rather than silently replacing them. A report about another worker is a report until independently checked.

If recording structured claims is useful, read [claim-format.md](references/claim-format.md). The local helper checks JSON structure, relative paths, file hashes and quoted line ranges:

```bash
python3 scripts/check_claims.py claims.json --root evidence-directory
```

The helper does not judge truth, prove execution or approve delivery. Every supplied reference is checked, even on an unknown claim. A successful check must be described as reference consistency only.

This skill does not authorize external messages, uploads, payments or further work. Use the user's actual task scope and report unresolved dependencies while continuing independent authorized work.
