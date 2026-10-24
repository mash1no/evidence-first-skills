# Evidence-first skills

Two small, newly written public implementations for evidence-based assistant work. They are not verbatim copies of private skills with the same names. See [PROVENANCE.md](PROVENANCE.md).

| Skill | Purpose |
| --- | --- |
| [evidence-first](skills/evidence-first/SKILL.md) | Separate observation, reports, inference, uncertainty and conflicts; check pinned local text references. |
| [industrial-evidence-first](skills/industrial-evidence-first/SKILL.md) | Check quantities, explicit units and source bindings before a technical document passes an evidence gate. |

Both tools use Python 3.9+ and its standard library. They only read explicitly supplied local JSON/text files. They do not run source code, train models, contact services, upload files or certify engineering results.

## Try locally

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 skills/evidence-first/scripts/check_claims.py claims.json --root evidence
python3 skills/industrial-evidence-first/scripts/check_delivery.py delivery.json --registry registry.json --root evidence
```

Formats are documented in each skill's `references/` directory. Examples and tests are synthetic; they are not manufacturing, measurement, supplier or deployment evidence.

To install a skill, place its complete directory under your Codex skills directory, commonly `~/.codex/skills`. If a skill with that name already exists, compare and merge deliberately or use a separate test environment; do not overwrite it blindly. Discovery and loading depend on the host session; installing files alone does not prove that existing conversations loaded them.

Use `$evidence-first` when preparing an evidence-backed status report, or `$industrial-evidence-first` when reviewing a technical quantity table. Automatic selection remains available through the task-specific skill descriptions. Neither skill grants permission to send, publish, spend money or execute external work.

## Limits

A matching hash identifies bytes. A checked reference identifies a passage. Neither proves that its author is truthful, that a test really ran, or that a physical part is safe. The industrial tool checks a separately supplied registry; it does not authenticate that registry or replace qualified engineering review.

Licensed under the [MIT License](LICENSE). Keep the license and copyright notice with redistributed copies, including standalone skill installations. This license covers these new public files, not the excluded private material described in PROVENANCE.md.
