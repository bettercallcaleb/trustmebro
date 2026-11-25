# Evidence index

Core v0.1: no model runs published. Synthetic fixture results are excluded.

## Technical depth (historical, not Core scores)

[ConceptLadder Exact v0.4 README and audit](https://github.com/bettercallcaleb/conceptladder-bench/tree/1bcd09ada509f6dfa8943c22143bb41e632762ac). The published two-seed Q4 pilots report 4B-class 55/480, Qwen3 14B 153/480, Qwen3 32B 189/480. These are historical source-reported exploratory results, not newly reproduced TrustMeBro scores. Exact v0.4 is not comparable to older MCQ versions; no-question shortcut baseline 87/720 on distinct held-out seeds.

## Quantization fidelity (historical, not Core scores)

[Qwen3.8-27B Q4_K_M frozen artifact study](https://github.com/bettercallcaleb/ramgpt-quantbench/tree/f9da19f1d05977907db99c7d92c3da71e9f32341/artifact-bench/public/qwen3-8-27b-q4-k-m-open-artifact-rank-v1). Published mean KL from native BF16 under the pinned asymmetric placement contract:

| Artifact | Mean KL (lower better) |
|---|---:|
| bartowski | 0.010784 |
| Unsloth legacy standard Q4_K_M | 0.012181 |
| ggml-org | 0.012310 |
| mradermacher-static | 0.023989 |

Artifact-specific observations, not publisher-wide rankings. The Unsloth/ggml-org difference was not statistically distinguished. See original source for topology, tokenization, placement and uncertainty. Do not compare KL across unrelated reference models.
