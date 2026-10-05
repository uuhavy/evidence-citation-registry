# EvidenceCitationRegistry

A standalone GenLayer registry for exact-span quotations and semantic citation
attestations. The contract first proves that a submitted quote occurs at a
specific position in an immutable document, then GenLayer assesses whether the
quote supports the claim without losing qualifications or surrounding context.
No frontend, financial transfer, web scraping or external fact-checking service.

## Why GenLayer is necessary

Substring matching establishes that text is present; it cannot establish that
the text supports the claim. An authentic quotation can come from a retracted
draft, a hypothetical example or an attributed opinion. The model separately
assesses quote entailment and the full document context.

Inside `gl.vm.run_nondet_unsafe`, the leader assesses both relations. The custom
validator independently repeats the assessment on the same frozen document,
claim and quote. It agrees on the **meaning of both relations, not JSON format**.
Reasons may vary, but matching final verdicts with different quote/context
decisions do not pass. Format validation is only an initial guard.

Quote relation: SUPPORTS, CONTRADICTS or INSUFFICIENT. Context relation:
CONSISTENT, CONTRADICTS or INSUFFICIENT. Deterministic code records REJECTED if
either contradicts, VERIFIED only for SUPPORTS + CONSISTENT, and UNRESOLVED
otherwise. Extra model-provided verdict fields cannot override this rule.
VERIFIED means supported by the submitted document, not true in the world.

## API and lifecycle

| Method | Behavior |
| --- | --- |
| `register_document(title, body)` | Anyone registers a frozen document; returns document ID |
| `submit_citation(document_id, claim, quote, start)` | Anyone; requires exact quote at the supplied character offset; returns citation ID |
| `audit(citation_id)` | Anyone; runs semantic consensus, records a terminal assessment and returns JSON |
| `get_document(document_id)` | Public author, title and exact body |
| `get_citation(citation_id)` | Public submitter, document reference, claim, exact span and assessment |
| `get_count()` | Number of citations; documents have a separate counter |

Citation: PENDING -> VERIFIED / REJECTED / UNRESOLVED. All terminal records are
immutable. Provider/parse errors leave PENDING for retry. Once a semantic
uncertainty is recorded as UNRESOLVED, further evidence requires a new citation.
There are no document edits, citation edits, deletions, appeals or reward claims.
Duplicate submissions are allowed as separate records; repeat auditing the same
record is forbidden. This is a citation audit registry, not a deduplication system.

Storage uses typed storage dataclasses, string-keyed TreeMaps, bigint counters
and bigint offsets. JSON objects in views/assessments are temporary. Character
offsets are Python Unicode code-point indices, zero-based, with an exclusive end.
They are not UTF-8 byte offsets or JavaScript UTF-16 code-unit offsets. Text is
not normalized or trimmed; exact matching preserves offsets and repeated quotes.

Limits: title 1..160 characters, body 1..12,000, claim 1..2,000 and quote
1..3,000; whitespace-only values are rejected. Invalid offsets, nonmatching
quotes, missing IDs, oversized input and duplicate audits raise UserError.
Wrong model format/provider failure cannot silently verify a citation.

## Validation and deployment

- Official **genvm-linter 0.11.0**, pinned GenVM v0.2.16: check passes, 6 methods.
- Official `typecheck --all`: **0 errors, 0 warnings**.
- Direct tests: **41 passed in 6.09s** on 2026-10-05.
- ASCII source and named class `EvidenceCitationRegistry(gl.Contract)`.
- Network **studionet**, chain **61999**.
- Address **`0x2B91C2029973Da08Ab024FBc6f5760e52db7f0b4`**.
- [Explorer](https://explorer-studio.genlayer.com/address/0x2B91C2029973Da08Ab024FBc6f5760e52db7f0b4).
- Deployment **FINALIZED / SUCCESS**; remote source matches the file checked by the linter.
- [Schema proof](schema-validation.json), [public verification](deployment-verification.json).
- Source SHA-256: `f8e41883f4872061c999671219d8650c65e3a8ff1650ff71c3e1a9d3feb41e56`.

```sh
python -m venv .venv
# Activate .venv (Windows: .venv\Scripts\activate; POSIX: source .venv/bin/activate)
python -m pip install -r requirements-dev.txt
python scripts/prepare_windows_tests.py
python scripts/validate_submission.py
# Windows PowerShell: $env:GENVM_VERSION='v0.2.16'
# POSIX: export GENVM_VERSION=v0.2.16
genvm-lint typecheck contracts/evidence_citation_registry.py --all --json
gltest tests/ -q -p no:cacheprovider --tb=short
python scripts/verify_public.py
```

The SDK is downloaded from the official release on first use. The Windows helper
fixes test-runner temporary-file handling only. The official linter is unmodified.
Tests use SDK storage and mocked model output, with separate independent validator
invocations; no simulator service is required. Coverage includes all nine
semantic combinations, differing relations with equal verdicts, malformed output,
actual provider exceptions and retry, fabricated spans, Unicode/repeated-quote
offsets, document isolation, input bounds and immutable terminal state.

## Scope and reuse

Useful for research-note citation audits, proposal evidence review and retrieval-
augmented answer provenance. Consumers choose which document authors to trust.
Anyone may register a document; its content, provenance and author identity are
not authenticated. VERIFIED is internal textual support, not an independent
truth certificate. No external page is fetched and no source can silently change
under an existing citation. All material is public. Do not submit private data.

LLM bias, ambiguous prose and prompt injection can still affect judgments.
Inputs are explicitly treated as untrusted by the prompt, but this is not a
proof of immunity. Strict semantic agreement may fail to converge. The system
does not automate legal, medical or financial decisions. Studionet verification
is dated evidence, not a permanent-retention guarantee.

## Worked example inputs

Fictional registered document:

```text
Draft: Offline mode is available in version 1. Correction: that draft is false. Version 1 requires an internet connection. Version 2 supports offline mode.
```

Citation `"0"` uses claim/quote `Offline mode is available in version 1.` at
offset 7, length 39. The exact span check passes. The real public audit records
quote_relation SUPPORTS but context_relation CONTRADICTS -> REJECTED. This
demonstrates why an authentic quote is insufficient: the document retracts it.
The actual rejected audit transaction is
[0x64f584db...95952f](https://explorer-studio.genlayer.com/tx/0x64f584dbd6243f102b1d5d4b52bf3ceac81767a3d4367b1adc19ea4b8395952f).

Citation `"1"` uses claim/quote `Version 2 supports offline mode.` at offset 123.
The real audit returned SUPPORTS + CONSISTENT -> VERIFIED on 2026-10-05.
Its finalized successful audit transaction is
[0xc18de24b...66c5d](https://explorer-studio.genlayer.com/tx/0xc18de24b3614a41742119f183cd5576e089982a9372200ffa737259195266c5d).
All five example transactions are FINALIZED with execution result SUCCESS.
Full public call arguments, receipts and read results are recorded in
[live-example.json](live-example.json), with the repeatable steps in
[example-plan.json](example-plan.json). The document is fictional; LLM judgments
and public network transactions are real, with no mocks and no leader-only mode.

`python scripts/live_example.py` verifies existing receipts and final reads
without sending a transaction. `--send` advances an unfinished recorded step;
do not delete the manifest and restart against an already-used instance.
