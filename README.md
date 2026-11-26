# TrustMeBro v0.3.1

**Don't trust us. Reproduce us.**

An independent open-weight model benchmark for people who actually run models locally. No paid placement. No LLM judge. No universal intelligence score.

## New in v0.3.1: Answer recovery

Diagnostics now recover the model's committed answer independently of contract compliance. Recovery uses the response and public answer-format specification, never the reference answer, original problem or supplied target value. Recovered correctness and unresolved reasons are reported separately from the original frozen score.

    python3 recovery.py run run.json --out recovered.json
    python3 recovery.py corpus corpus/responses.jsonl --out corpus-replay.json

The existing diagnostic command also includes per-response recovery results and a recovery summary. See [recovery policy and validation](docs/RECOVERY.md). The official v0.2 scoring protocol is unchanged; recovery v0.2 is a separately versioned diagnostic measurement. Unknowns are partitioned into confirmed truncation, specific observed blockers and unclassified replies; termination remains independent of correctness.

## New in v0.3.0: Failure Corpus

**3,048 real model replies. Four model architectures. 2,367 unique anomalous response texts.**

TrustMeBro now ships a public [Failure Corpus](corpus/README.md) and a standalone response-diagnostics tool. Inspect nonstandard answers, malformed output, repeated declarations, JSON schema deviations and special-token leakage without silently repairing the answer or changing the official score.

    python3 failure_corpus.py summarize corpus/responses.jsonl
    python3 failure_corpus.py diagnose-run run.json --out diagnostics.json

The corpus is exploratory, not a model ranking. Diagnostic annotations remain candidate labels; the v0.2 benchmark protocol and its scoring semantics are unchanged. Core Depth, extraction and supplied-answer delivery prototypes are available under [draft/](draft/README.md), with their calibration limitations documented.

## What ships

- Core: 160 generated tasks per default seed, covering arithmetic, scheduling, modular arithmetic, paths, copying, JSON, ordering and filtering.
- Ladder: 240 generated technical tasks across four levels and 15 concept families, including networking, databases, Linux and security. The ConceptLadder generator and executable oracles are bundled, not just linked.
- Strict and relaxed profiles: identical underlying problems, different output contracts. Report confirmed correct, confirmed wrong, unknown, format compliance and joint success separately.
- Budget sweep: fixed output-token ceilings, not a verified thinking budget. Record actual token counts and reasoning policy.
- Efficiency: total cost divided by joint successes, including failed attempts. Missing cost data stays unknown.
- External reference: the original IFEval dataset and upstream scorer through a separate adapter; no bundled third-party data or invented general instruction-following score.
- Replay: raw API replies, task manifest, deterministic grading, exact supplied model-file hashes, runtime, hardware and decoding settings.
- Quantization fidelity: [RAMGPT QuantBench](https://github.com/bettercallcaleb/ramgpt-quantbench/tree/f9da19f1d05977907db99c7d92c3da71e9f32341), a separate BF16-reference measurement, not a component of a composite score.

## Run locally

Python 3.10+, standard library only for Core and Ladder. Start an OpenAI-compatible local server, then:

```bash
python3 trustmebro.py generate --suite all --seed 17 --out tasks.json
python3 trustmebro.py run --tasks tasks.json --url http://127.0.0.1:8080/v1 --model local --artifact /path/to/model.gguf --runtime 'llama.cpp COMMIT and flags' --hardware 'RTX 4090 24GB' --reasoning-policy off --modes strict,relaxed --budgets 64,256,1024,2048 --out run.json
python3 trustmebro.py score run.json
python3 -m unittest discover -s tests -v
```

Choose `--suite core` or `--suite ladder` for separate runs. The default 400-item manifest and the example eight profiles require 3,200 requests. For a small smoke test, use `--variants 1 --ladder-variants 1`. A versionless legacy command (omit `--suite`) still generates Core v0.1 for reproducibility. The v0.2 report contains separate profiles for each track, mode and budget; no aggregate score.

Use a local server only; no model downloads or GPU processes are started by the harness. For sharded models supply --artifact repeatedly. Pin actual server configuration, chat template, reasoning policy, GPU offload and model source. A length finish is recorded independently from answer correctness. API errors and unrun questions remain in the planned denominator; incomplete profiles are not eligible for ranking.

### External IFEval reference

Install the upstream IFEval checkout and its requirements separately, as described in [the adapter notes](docs/IFEVAL.md).

```bash
python3 trustmebro.py ifeval run --ifeval-root /path/to/google-research --model local --url http://127.0.0.1:8080/v1 --max-tokens 2048 --profile 'engine and reasoning settings' --out ifeval.jsonl
```

## Results

[Evidence index](RESULTS.md). v0.2 is an alpha protocol; historical experiments do not constitute scores for this new prompt protocol. No model ranking is published for v0.2 yet. Historical results are labeled by suite and never merged into a composite. A single run is a pilot. Use multiple predeclared seeds and repeated decoding runs before claiming robust differences. Scores describe these task families, not general intelligence.

## Governance

See [protocol](PROTOCOL.md). The public generator is not a contamination-proof hidden test. Anyone can challenge our methodology or submit raw, reproducible results. Versions are frozen; changes to questions or scoring require a new protocol version.

MIT license.
