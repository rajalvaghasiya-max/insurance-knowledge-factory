# MO-011 — Deterministic Repository Line Endings

## Why governed artifacts require LF

Several generic contracts in this repository (`factory_core/canonical/generic_legal_condition_binding.py`,
`generic_legal_condition_canonical_projection.py`, and related modules)
establish and verify lineage between governed artifacts by comparing a
**SHA-256 computed over the raw bytes on disk**, not over a
parsed-and-re-serialized version of the JSON. That is a deliberate
governance choice: an immutable evidence or lineage record should not
be treatable as "the same" just because two byte sequences happen to
decode to the same data structure. Byte-identity is the guarantee.

The consequence is that anything which rewrites those bytes without
changing the underlying data — most commonly, a text tool or `git`
itself converting line endings — silently invalidates every hash that
was computed against the original bytes, even though nothing about
the governed content actually changed.

## Lineage hashes operate on raw bytes

Concretely: `knowledge/factory/registry_backed/star_health_star_comprehensive/generic_source_registration/star_health_star_comprehensive_generic_source_bundle.json`
was originally written with LF (`\n`) line endings by the generic
registration contract. In a Windows checkout with `git config
core.autocrlf true`, Git rewrote those LF bytes to CRLF (`\r\n`) on
checkout. The file's *content*, once parsed, was unchanged. Its
*bytes* were not: a 39-line JSON file gained 39 extra `\r` bytes,
which changed its SHA-256 from `fa56d4497170e6534bb435a699c97fb4c2b6445f48b894709c45a01ed4757900`
to `a5cad01371bc6494f5293a02f988b35b074da1112f424e81f1bf89f791fd0288`.
The binding manifest that referenced the bundle recorded the original
(correct) hash, so the canonical projection contract correctly
detected a mismatch and refused to proceed. This was the contract
working exactly as designed — the actual defect was line-ending drift
introduced outside the contract's control, at the Git checkout layer.

## Recommended Git configuration

In addition to this repository's `.gitattributes` (which is
authoritative and applies regardless of any individual contributor's
global settings), contributors — especially on Windows — should set:

```bash
git config core.autocrlf false
git config core.eol lf
```

`.gitattributes` alone is normally sufficient once committed and
recognized by Git, but setting these explicitly avoids any ambiguity
and matches the configuration already applied in the authoritative
local environment following this incident.

## How to verify effective attributes

To check what Git will actually do with a specific file, given the
current `.gitattributes`:

```bash
git check-attr text eol -- path/to/file.json
```

Expected output for any governed JSON artifact:

```text
path/to/file.json: text: set
path/to/file.json: eol: lf
```

To scan the whole repository for any tracked JSON/JSONL/YAML/Python/
Markdown file that is *not* correctly LF-controlled (a regression
check), run:

```bash
python scripts/verify_line_endings.py
```

This script is narrowly scoped: it checks attribute coverage and
scans working-tree bytes for CRLF in the governed Star source bundle
specifically (the artifact this incident affected), plus a general
sweep across `.gitattributes`-covered extensions, without modifying
any file.

## Scope of this change

This is a repository-governance change only. It does not alter
production behaviour, does not change any schema or generic contract,
does not regenerate any governed artifact, and does not mass-normalize
or rewrite any existing file's line endings. `.gitattributes` affects
only how Git checks files in and out going forward; files already
committed with LF endings (which is every governed JSON artifact in
this repository, confirmed as part of this order) are unaffected.
