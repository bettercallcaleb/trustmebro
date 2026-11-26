# Reliability and delivery controls — draft, not a model leaderboard

The original v0.2 scorer and historical results remain frozen. The new candidate scorer has a separate version and can replay existing raw responses without inference. We distinguish an evaluator's inability to recognize an answer from a model's failure to follow its output contract. Improving extraction does not retroactively make the original output compliant.

## Report independent axes

- Semantic outcome: confirmed correct, confirmed wrong, or unresolved. Denominator: every planned item. Unknown does not receive credit.
- Delivery outcome: original contract compliance, regardless of answer correctness. Joint success requires both.
- Specific observable diagnostic flags: Markdown emphasis, code fences, inline code, noncanonical representation, missing terminal marker, extra output in strict mode, multiple explicit declarations, conflicting declarations, malformed or nonterminal declaration, empty visible output.
- Generation flags: output limit reached, repeated text heuristic, missing or unusual finish reason, reported token count over the cap. A correct answer may still have a generation flag.
- Infrastructure: transport failure and unrun items are distinct from model output failure.
- Efficiency: all-attempt tokens and endpoint time per joint success, plus resource consumption on unsuccessful attempts. Missing token data remains unknown.

These axes overlap. Do not sum flag rates or call them a causal diagnosis of weight quantization. An observed failure is evidence of a delivery or computation problem under this protocol, not a measured probability of failure across repeated runs. Repetition is a conservative text heuristic, not a general detector of all degeneration. A compliant wrong answer is a semantic failure, not a format failure.

The extractor accepts only a full standalone value or an unambiguous explicit terminal answer, including balanced Markdown wrappers. It does not search for a gold substring or infer a final answer from unfinished reasoning. Conflicting explicit declarations remain unresolved; repeated identical declarations can convey a semantic value but remain noncompliant. A heading without an answer value is not automatically an answer declaration. The previous v0.2 report is not overwritten.

## Existing 80-response CPU replay

The 27B Q4 model remains 29 correct, 1 wrong and 10 unresolved out of 40. The 4B BF16 model changes from 12 correct, 8 wrong and 20 unresolved to 19 correct, 15 wrong and 6 unresolved. All fourteen recovered 4B answers were explicitly declared using Markdown emphasis (11) or code fences (3). Seven were right and seven wrong. Strict successes remain 29 and 12. The aggregate replay report includes the source manifest and raw file SHA-256; it does not publish raw model content. No new inference was used.

## Paired delivery-control panel

Ten preselected source items (two per family, L2 and L4) are crossed with two conditions and three output contracts, for 60 candidate items:

| Condition | Bare integer | One FINAL line | JSON with integer answer and exact tag |
|---|---|---|---|
| Solve | Compute result | Compute result | Compute result |
| Supplied | Use verified result in same context | Use verified result in same context | Use verified result in same context |

The source problem remains present in both conditions. Each request uses a fresh conversation. The supplied value is not hidden, and the model is explicitly asked not to recompute it. For JSON, a correct numeric answer with a missing/incorrect tag, extra key, string instead of integer or Markdown wrapper gets semantic credit where unambiguous but fails the delivery contract. Duplicate keys are rejected, not resolved by choosing a favorable value.

Report paired success transitions and per-contract semantic and delivery results, never a combined score. A failure even with the answer supplied exposes a delivery weakness under that specific prompt, but a successful supplied condition does not establish the mechanism of the original failure. The supplied condition changes the instruction and adds information. The control panel is a development candidate, not an independent held-out validation. No model runs are authorized by this draft; its standalone scorer is not yet integrated with the raw inference and cost harness.

## Core Depth next design gate

Retain the original difficult enumeration tasks as a named stress subset, not as calibrated general reasoning levels. Test shorter witness-validation and feasibility questions separately from full arrangement enumeration. Keep the same answer representation and compare task variants without treating longer output as inherently more difficult. For scheduling, distinguish a compact feasibility/witness check from optimization. Add stronger state-transition and relational tasks with interacting constraints and boundary cases; oracle cross-checks remain mandatory. Do not tune on the 40-item pilot and then report that pilot as validation. Freeze a fresh panel and inspect it before any GPU use.

## Reproduce

    python3 draft/replay_reliability.py --run-dir /path/to/calibration/results --out replay.json
    python3 draft/delivery_controls.py --source draft/review-seed17.json --out delivery.json
    python3 -m unittest discover -s tests -v
