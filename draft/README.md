# Core Depth — candidate design, not a released benchmark

The original Core remains a quick sanity check. This CPU-only draft is a new reasoning candidate, not a replacement of Ladder or IFEval. It is deliberately not wired into the model runner. The approved initial 80-request GPU calibration has completed. No further GPU evaluation is authorized by this draft.

| Family | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| Routing | Minimum cost | Required waypoint | Toll cap | Incompatible consecutive edges |
| Scheduling | Weighted interval selection | Required job | Resource budget | Prerequisite dependencies |
| Ledger | Balance and failed spend | Reservation and release | Two-account transfers | Atomic batch rollback |
| Relational | Filter and sum | Join with users | Latest event before filtering | Group aggregation and exclusion |
| Constraints | Ordering counts | Adjacency | Position and nonadjacency | Exclusive-or constraints, possible unsatisfiability |

These are **design levels**, not empirically calibrated difficulty labels. Four families share a scenario across levels; ledger uses different event sequences. Each problem is independent and is given in a fresh conversation. Do not give a model the earlier-level answers. All require short integer answers to avoid confounding the reasoning comparison with output complexity. This candidate is not a general knowledge, coding, or language benchmark. Instruction following is a separate track (IFEval and future matched supplied-answer controls). Keep strict task success and confirmed semantic correctness separate.

## CPU quality checks

Two algorithmically distinct oracles agree for all retained cases: path enumeration vs state DP; job subsets vs chronological memoized search; ledger integer state vs unit-level state; relational Python vs SQLite; permutation enumeration vs pruned DFS. They operate on the same generated scenario, so this does not prove the natural-language rendering is unambiguous. Inspect the prompts and answers in the review panel and independently work selected examples by hand. Generation uses rejection sampling to exercise binding constraints, plus deliberately nonbinding and zero/no-solution controls. This is a synthetic stress distribution, not an estimate of real-world frequency.

Run the CPU audit with:

    python3 draft/audit_core_depth.py
    python3 draft/core_depth.py --seed 17 --variants 2 --out review.json
    python3 -m unittest discover -s tests -v

The audit uses 100 seeds x 2 variants x 5 families x 4 levels. One exact prompt repeated across the 4,000 generated items; do not treat overlapping seeds as independent data. Each manifest rejects internal duplicates and validate_panel rejects cross-manifest exact duplicates. Template/structural dependence still exists even for text-unique prompts. The reported modal answer frequency is a descriptive hindsight guess baseline, not an independent held-out guessing experiment.

## Acceptance gates before any large inference run

1. Human review: read the 40-item sample including all 20 family/level cells and verify selected answers independently; reject ambiguous wording or irrelevant difficulty. Separate structural difficulty from prompt-length effects.
2. Freeze the candidate generator and scorer, explicitly record the task hash and exact prompts; verify old v0.2 replay is unchanged.
3. Only after owner approval, run a small calibration (proposal: Qwen3.8-27B Q4_K_M and Qwen3-4B BF16, same 40 tasks, one relaxed 2048-output-token profile, 80 requests maximum). This is a capability contrast, not a causal quantization comparison. Use a fresh conversation per item and identical decoding settings where supported. Inspect every failure and measure actual tokens, finish reasons and output-format compliance. Stop on runtime errors or ambiguous questions. Do not sweep 17 models.
4. With only two variants per cell, judge gross ceiling/floor, reversals, and obvious shortcuts, not statistical monotonicity. Flag suspicious cells (both models consistently solve all levels or fail all levels, repeated L4 success with L1 failure, or high truncation). Revise or remove flawed families; use fresh predeclared seeds for confirmation rather than tune and report on the same data.
5. After a separate approval, integrate a versioned track into the harness and measure a broader panel. Retain Core sanity, Ladder, IFEval and efficiency as separate results. No composite score.

The candidate [reliability scorer and paired delivery controls](RELIABILITY.md) preserve the original protocol and expose specific observed failures. The 80-response replay is complete; the new 60-item delivery panel is CPU-validated only. Official IFEval remains separate.

The standalone [Answer Extraction & Abstention module](EXTRACTION.md) includes 32 paired review items and independent evidence/abstention scoring. It is not part of the automatic Core/Ladder runner.
