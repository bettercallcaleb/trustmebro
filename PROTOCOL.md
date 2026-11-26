# TrustMeBro v0.2-alpha protocol

## Tracks and controls

Core and Ladder are reported separately. Core has reasoning and instruction subdomains; Ladder uses the original Exact v0.4 scenario generators and four levels. Both use a versioned manifest and explicit strict and relaxed prompt contracts. Strict requests only the answer value, while relaxed permits explanation and asks for a terminal FINAL line. Compare profiles with matching track, mode, task manifest, budget and sampling protocol. Different prompt contracts measure different behaviors.

## Scoring

Every planned item is confirmed correct, confirmed wrong or unknown. Unknown receives no correctness credit, but is not proof of an underlying knowledge error. Transport errors and unrun items are distinguished from unknown model answers. All rates use the full planned denominator, never only successfully parsed answers. The upper bound is hypothetical, not an achieved score.

Semantic extraction accepts a standalone value, an explicitly labeled answer, or a tightly constrained answer phrase. It does not search the response for the gold answer or accept arbitrary numeric fragments. Conflicting labels are unknown. Strict format compliance checks the requested output representation; task-dependent content constraints such as correct ordering remain in answer correctness. A well-formed wrong value is compliant but wrong. A correct value with extra explanation is semantically correct but fails the strict output contract. Relaxed mode separately requires a single terminal FINAL line. Surrounding whitespace is ignored. JSON must reject duplicate keys and non-finite constants; field names and value types matter. No universal semantic judge.

Joint success = confirmed correct AND compliance with the selected output contract. Strict accuracy is joint success divided by planned items within that profile. The error matrix cross-tabulates confirmed correct, confirmed wrong and unknown with format compliance for model responses; transport errors and unrun items are outside the matrix. A length finish is independently counted, even if the final answer is available. Repetition flags are a conservative exact repeated-token-block heuristic, not a validated general degeneration classifier. Neither these flags nor truncation automatically overrides answer correctness.

Efficiency = all reported completion tokens or all endpoint wall time divided by joint successes. Cost includes failed model attempts; missing token metadata, incomplete request coverage or zero successes yields null for the corresponding cost ratio. Transport errors may consume unreported tokens; do not rank incomplete profiles. Report hardware and runtime, and avoid cross-hardware speed rankings. Actual token usage can differ from the cap and backend reporting may omit hidden reasoning. Contiguous knowledge depth is reported as lower and upper bounds for each Ladder profile.

## External reference

IFEval uses its original external 541-prompt set and official strict/loose prompt/instruction scorers. It is a separate reference, not a combined score or proof that the custom output-format metric measures general instruction following. QuantBench remains a separate reference-distribution tool. No single score or ranking combines these tracks.

## Reproducibility and limits

Predeclare seeds and budget grids; retain raw responses and all profiles. Public templates are not secret held-out questions, and generated variants share a small number of source families. The protocol does not prove runtime model identity or reasoning settings; artifact hashes and operator declarations must be checked. v0.2 is an engineering alpha, not a psychometrically validated leaderboard. Original v0.1 remains available below and its scores are not directly comparable.

---

# Core v0.1 protocol

Each seed generates 20 items per family (160 total). Four reasoning and four instruction families receive equal item counts. Tasks are deterministic for a fixed Python implementation and seed; the SHA-256 of the canonical manifest is authoritative. Use the exact same manifest and output-token caps across compared models. For public comparisons, predeclare seeds, engine/template/settings and budget grid; report all completed profiles, including losses. Temperature 0; API seed is requested but backend support is not assumed. No external tools or judge.

Score: strict exact text after trimming surrounding whitespace, except the JSON family uses parsed semantic equality with type-sensitive canonical JSON and rejects duplicate keys. No extracting a correct answer from a verbose response: format is part of the task. Only final content is scored; reasoning_content is retained in raw responses. Non-JSON response or network errors count as failed transport, not a model error; profiles with such failures are incomplete and ineligible for ranking. Show accuracy denominator, failures, finish reasons, reported tokens (missing stays unknown), median and total latency. API token counts may exclude hidden reasoning, and token caps are not guaranteed to be enforced; use runtime-specific checks for a controlled thinking-budget study. Latency is endpoint wall time including prefill and request overhead, not decode speed. VRAM is not measured in Core. No cross-hardware speed ranking.

Core compares task performance, not quantization fidelity. QuantBench results are separate. ConceptLadder is a separate procedural technical stress suite; do not combine scores. Core currently has eight template families and no validated difficulty hierarchy, real coding execution, long-context evaluation, or independent contamination audit. Publish failures and raw outputs; review for unintended sensitive data before sharing. Public generated tasks can be targeted by training; future held-out seeds are not equivalent to secret templates.

Artifact hashes are calculated from supplied local files; the harness cannot independently attest that the server loaded them. Hardware and runtime are operator declarations. Community submissions require review, not automatic verification.
