# Validation record - 2026-10-05

- Official unmodified genvm-linter 0.11.0 check: exit 0, 6 methods, class
  EvidenceCitationRegistry. See schema-validation.json with source hash.
- `genvm-lint typecheck contracts/evidence_citation_registry.py --all --json`
  with GENVM_VERSION=v0.2.16: ok=true, 0 errors, 0 warnings, 0 info.
- `gltest tests/ -q -p no:cacheprovider --tb=short`: 41 passed in 6.09s.
- Source ASCII, pinned dependency header, wildcard SDK import.
- Public schema and finalized deployment verified; remote source is byte-identical
  to the local source and its official linter evidence hash.
- Five real example transactions FINALIZED/SUCCESS: retracted quote REJECTED,
  context-consistent quote VERIFIED, both confirmed by public reads.
- Exact spans, Unicode offsets, repeated quotations, document isolation, all nine
  relation combinations and same-outcome semantic disagreements are tested.
- Provider TimeoutError/malformed-output retries preserve pending state.
- No frontend, web snapshot mutation, hardcoded verdict or format-only validator.

Type checking is not execution. Direct tests mock LLM output. Real public network
audits are recorded separately in live-example.json. contracts/ contains the only
deployable Python source; other Python files are tooling. The contract verifies
textual support relative to supplied data, not external source authenticity.
