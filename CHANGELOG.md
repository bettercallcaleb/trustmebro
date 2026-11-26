# Changelog

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
