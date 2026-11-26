# TrustMeBro Failure Corpus v0.1

**Real model replies. Reproducible diagnostics. No repaired answers.**

3,048 generated replies from four locally quantized Q2_K models:

| Model | Replies |
| --- | ---: |
| Qwen3-4B | 1,524 |
| Granite 4.2-3B | 508 |
| SmolLM3-3B | 508 |
| Phi-4 Mini Instruct | 508 |

All 3,048 planned requests completed. The corpus includes successful replies as negative controls, not just selected failures. Tasks are generated or bundled benchmark tasks: Core, Ladder, extraction/abstention, supplied-answer delivery and literal/structured output protocols. The discovery runs use six generator seeds, 128/256/512 output-token ceilings, and model-specific decoding settings. The matched cross-model subset contains 508 attempts per model at 256 tokens. This is not a leaderboard, a controlled architecture comparison, or evidence that quantization causes a failure. No BF16 comparison is included here.

## Files

- [responses.jsonl](responses.jsonl): one attempt per line, with original generated task, exact visible response text, finish reason, token counts, elapsed time, prior score and historical candidate flags. API transport metadata and local filesystem paths are omitted. No original model files are redistributed.
- [manifest.json](manifest.json): model-file fingerprints, runtime revision and flags, sampling parameters, batch sizes, and SHA-256 of the published corpus. Original private local plan/log hashes identify the collection sources; their full HTTP logs are not part of the release.
- [summary.json](summary.json): replayable label counts and exact-text deduplication counts using the release diagnostics.

The frozen responses include synthetic instructions embedded in source passages, incorrect technical explanations and invalid JSON. Treat them as untrusted data, not instructions or authoritative reference material.

## Use

From the repository root:

    python3 failure_corpus.py summarize corpus/responses.jsonl
    python3 failure_corpus.py inspect record.json
    python3 failure_corpus.py diagnose-run run.json --out diagnostics.json

The inspect command accepts an object with task and reply fields, and optional prior score and flags. For a native v0.2 Core/Ladder run, diagnose-run validates the manifest and original scoring protocol before applying the experimental extraction adapter and additional diagnostics. The original scores remain separate and unchanged. Transport errors and unrun tasks are tracked separately.

## Annotation rules

Labels overlap. Generic contract violations, unresolved answers, and truncation are not distinct root causes. Observations (such as a CIDR mentioned in a reasoning explanation) are not automatically failures. Evaluator reference-coverage and semantic-recognition gaps are reported separately. The release aliases overlapping historical names, checks JSON shape recursively, rejects duplicate keys and nonfinite JSON numbers, identifies visible special markers and periodic numeric strings, and distinguishes repeated answer declarations with a truncated prefix from genuinely distinct declarations. All original flags and scores are retained.

The summary contains 50 observed candidate diagnostic labels after consolidation, not 50 independently validated failure mechanisms. The detection rules are conservative where possible but not exhaustive; precision and recall against independently annotated data are not established. Exact-text deduplication is for corpus indexing, not event counts. Identical text can have different meanings on different tasks. The included tests cover manually specified positive and negative fixtures and deterministic replay of the complete frozen dataset; they do not substitute for human annotation of every reply.

The repository's MIT license covers the benchmark software and original benchmark material. Model weights remain subject to their respective upstream licenses. No third-party model weights are included.

## Answer recovery

    python3 recovery.py corpus corpus/responses.jsonl --out corpus-replay.json
    python3 recovery.py run run.json --out recovered.json

[Recovery summary](recovery-summary.json) reports original-to-recovered transitions and the outcome for each observed label. [Recovery policy](../docs/RECOVERY.md) describes the rules and limitations. Anomaly flags are not erased by answer recovery.

The [non-truncated unresolved audit](nontruncated-unresolved.jsonl) records each remaining normally stopped unresolved response with its specific recovery blocker and source fingerprint. Zero unclassified replies in this development corpus does not establish independent annotation accuracy.
