# Nonstandard Response Taxonomy — draft

The primary engineering target is to identify and quantify distinct ways that an output deviates from the requested contract, without erasing the deviation when the semantic extractor improves. Preserve raw outputs, source task hashes, and prior scores. Diagnose the original response rather than a repaired response.

Five independent groups:

- Decision/value: wrong value, false extraction, false abstention, unresolved decision.
- Output contract: incorrect label, bare numeric answer when structured output is required, JSON-encoded abstention, noncanonical numbers, wrong JSON field types, missing/extra keys, invalid JSON, duplicate keys, extra text, Markdown wrappers (emphasis, inline code, fences), multiple or malformed declarations.
- Evidence: missing quote, absent-from-source quote, irrelevant quote, quote/answer mismatch, conflicting declarations.
- Generation: length limit, empty output, repeated-text heuristic, missing or unusual finish reason, reported tokens exceeding the cap.
- Evaluator defects: semantic recognition gap and reference coverage gap. These are not model defects.

A single reply can have several flags. Group counts count each response once per group; individual flags can overlap. Per-flag costs also overlap and must not be added together. The mutually exclusive correctness-by-contract buckets retain the full planned denominator, with transport errors and unrun tasks separate. Evidence failure may occur even when both semantic correctness and format compliance hold.

The new offline adapter recognizes explicit JSON abstention (answer=UNKNOWN) without making it compliant with the original bare UNKNOWN contract. It also accepts a complete source line containing the designated decisive statement where the original extraction instructions explicitly allowed a sentence OR line. This is a reference-coverage correction, not a relaxation of the output contract. Other ambiguous outputs remain unresolved. No favorable-number search or inference from intermediate work is allowed.

## Replay of existing experiments

This draft replays the 80 Core Depth and 64 Extraction calibration responses without new inference. Extraction: 4B has 23/32 semantic successes, 16/32 joint successes, 7 JSON-form abstentions and 9 false extractions. 27B has 31/32 semantic successes, 16/32 joint successes, 15 JSON-form abstentions and one false extraction. Two 4B evidence reference gaps are corrected. Historical reports remain unchanged. The reasoning baseline here is the already-revised reliability draft, not the original v0.2 scorer.

The summary report contains raw file hashes, overall and family-specific counts, polarity-specific counts where applicable, and costs attributed to observed flags. It is not a claim that every possible nonstandard response has been identified. Taxonomy flags describe observable outcomes, not latent causes; repetition and extraction remain conservative heuristics. Missing or unclear cases require review and may motivate new categories. No model-specific exceptions.

    python3 draft/response_taxonomy.py --extraction-dir /path/to/extraction/results --reasoning-dir /path/to/depth/results --out taxonomy.json
    python3 -m unittest discover -s tests -v

The adapter is draft-only, not integrated into the main runner. Further calibration and extension to the separate delivery-control, Ladder and IFEval tracks require independent review. No new GPU tests are authorized by this change.
