# Quantity-table format

A document has `schema_version: 1`, `stage` (`draft` or `release-candidate`), a nonempty `summary`, and a nonempty `items` array. Every item has:

- `id`: unique nonempty string.
- `value`: finite decimal string, or null for unknown/conflict.
- `unit`: one of `mm`, `cm`, `m`, `deg`, `rad`, `N`, `kg`; null only for unknown/conflict.
- `status`: `source-stated`, `measured`, `estimated`, `unknown`, or `conflict`.
- `evidence_ids`: unique strings referencing the independently supplied registry. Source-stated/measured require a matching fact. Conflict requires differing source facts. Any supplied reference is checked, including references attached to unknown items.
- `notes`: nonempty for estimated/unknown/conflict, optional otherwise.

The separately reviewed registry has `schema_version: 1` and `sources`, an array of:

```json
{"id":"synthetic-source","path":"note.txt","sha256":"DIGEST_COMPUTED_FROM_FILE","line":1,"quote":"Synthetic width: 12 mm","fixture":true,"facts":[{"item_id":"width","value":"12","unit":"mm","basis":"source-stated"}]}
```

Each source pins a UTF-8 local file, its complete SHA-256 and one exact line. The digest example is a shape marker, not a usable digest. Paths must remain under `--root`, including through symlinks. Every registry source is checked, even if unused by the document. `fixture` is a required boolean; synthetic examples must use true.

Each fact binds `item_id`, decimal-string `value`, `unit` and `basis` (`source-stated` or `measured`). Measured facts additionally require a nonempty `method` and `measured_on` in YYYY-MM-DD form. The checker compares numerical values without unit conversion: `12.0 mm` can match `12 mm`; it never assumes `12 mm` equals `12 m`. Source facts must still be reviewed for meaning and authority; a matching quote does not authenticate the source.

An estimated item requires notes and does not pass the gate. Unknown/conflict items use null value and unit and retain their reasons. A conflict needs at least two distinct source facts with different values or units for the same item. Duplicate IDs, blank content, non-finite numbers and invalid supplied references are errors.

Exit 0 means the document is structurally consistent; its JSON output may still say `evidence_gate: hold`. Use `--require-gate` to receive exit 2 when the gate is held. Exit 1 means invalid input. Even `evidence_gate: pass` is a limited consistency result, not an engineering approval or an authorization to release.
