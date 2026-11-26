# Bundled ConceptLadder provenance

The technical scenario generation and answer oracle code is derived from ConceptLadder Exact v0.4, https://github.com/bettercallcaleb/conceptladder-bench/tree/1bcd09ada509f6dfa8943c22143bb41e632762ac . The bundled adapter and CLI additionally contain the local v0.5-alpha/v0.5.1 measurement work (fixed all-item denominator and official IFEval integration). The upstream MIT license is preserved in licenses/ConceptLadder-MIT.txt.

This repository's measurement.py is the canonical v0.2 Core/Ladder scorer. The bundled conceptladder package is retained for scenario generation and the external IFEval adapter. Its old CLI is not a v0.2 score. No prior source repository is removed or rewritten.

Development motivation: earlier experiments exposed output truncation, answer extraction selection bias, and format failures distinct from semantic errors. The new protocol retains strict task success, separates error types and counts resource usage on failures. Historical experiments used different prompts or item sets and must not be represented as v0.2 results.
