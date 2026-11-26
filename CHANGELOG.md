# Changelog

## Unreleased

- Recovery v0.4 adds explicit correction, family-specific conclusion, decimal, identifier and bounded equation-result parsing.
- Preserve prior corpus judgments; add regression tests for the second formal batch and retain unresolved conflicts separately.

## v0.3.1

- Connect response diagnosis to deterministic, reference-blind answer recovery across all 50 observed labels.
- Recover bounded answer declarations, split labels, terminal Markdown and math wrappers, repeated claims, safe representation changes, and structured answers.
- Preserve incorrect claims, evidence failures, conflicts and unresolved/truncated responses; never solve the underlying task or substitute a reference value.
- Report original and recovered semantic outcomes side by side, with per-label strategies and explicit unresolved reasons.
- Partition unresolved replies by observed blocker and termination, with separate residual review counts.
- Extend reference-blind recovery to structured fields, ordered status vectors, route tuples, character pairs and explicit conclusions; audit the remaining non-truncated unresolved cases.
- Add recovery regression tests and frozen-corpus replay. Original scoring and raw outputs remain unchanged.

## v0.3.0

- Publish Failure Corpus v0.1: 3,048 generated responses from Qwen3-4B, Granite 4.2-3B, SmolLM3-3B and Phi-4 Mini Instruct Q2_K.
- Add offline response diagnostics, corpus replay and a diagnostic adapter for the existing v0.2 Core/Ladder runner.
- Separate historical scores, candidate failure labels, observations and evaluator defects.
- Consolidate overlapping names, detect JSON structural failures and repeated answer declarations with a truncated tail.
- Include frozen corpus fingerprints, model/runtime provenance and deterministic regression tests.
- Ship Core Depth, answer extraction and delivery-control experiments as draft modules. They are not part of the frozen official scoring protocol.
- Preserve all v0.2 scoring behavior. No composite score or model ranking is introduced.

## v0.2-alpha

- Unified Core and ConceptLadder, output contracts, cost accounting, raw-response replay and external IFEval adapter.
