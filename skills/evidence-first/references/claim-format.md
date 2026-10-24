# Local claim format

The top level has `schema_version: 1` and a nonempty `claims` array. Each claim has:

- `id`: unique nonempty string.
- `text`: nonempty factual statement.
- `status`: `observed`, `reported`, `inferred`, `unknown`, or `conflict`.
- `scope`: nonempty string describing exactly what this statement covers.
- `rationale`: nonempty for inferred, unknown and conflict; optional otherwise.
- `references`: array of local references. Observed/reported require at least one; inferred requires at least one plus its rationale; conflict requires at least two distinct references. Unknown may have none, but supplied references still must validate.

A reference has `path`, `sha256`, `first_line`, `last_line` and `quote`. Paths are relative to `--root`; absolute paths, URLs, parent traversal and symlinks escaping that root are rejected. The digest identifies the entire original file. Line numbers are positive and inclusive. `quote` must exactly match those UTF-8 lines joined by a newline; line endings in the file are normalized by `splitlines()` for this comparison.

Synthetic shape example; compute the digest from your actual file before using it:

```json
{"schema_version":1,"claims":[{"id":"example-1","text":"Execution has not been checked.","status":"unknown","scope":"runtime","rationale":"No runtime receipt supplied.","references":[]}]}
```

Exit 0 means structure and provided local references are consistent. Exit 1 means invalid input or mismatched evidence. It never promotes reported claims to observation or transforms uncertainty into success. References may support a false statement; the caller must still assess their meaning and trustworthiness.
