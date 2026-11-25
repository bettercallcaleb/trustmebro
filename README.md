# TrustMeBro v0.1.0

**Don't trust us. Reproduce us.**

An independent open-weight model benchmark for people who actually run models locally. No paid placement. No LLM judge. No universal intelligence score.

## What ships

- Core v0.1: 160 generated open-answer tasks per seed, across eight families: arithmetic, scheduling, modular arithmetic, shortest path, exact copying, structured JSON, ordering, and filtering.
- Budget sweep: identical tasks at configurable output-token ceilings. A ceiling is not a verified thinking budget; record actual reported token counts and backend reasoning settings.
- Replay: raw API replies, task manifest, deterministic grading, exact model-file SHA-256, runtime, hardware, decoding settings, elapsed time and reported token usage.
- Technical depth: [ConceptLadder Exact v0.4](https://github.com/bettercallcaleb/conceptladder-bench/tree/1bcd09ada509f6dfa8943c22143bb41e632762ac), a separate pinned 240-item technical suite.
- Quantization fidelity: [RAMGPT QuantBench](https://github.com/bettercallcaleb/ramgpt-quantbench/tree/f9da19f1d05977907db99c7d92c3da71e9f32341), separate BF16-reference distribution measurements.

## Run locally

Python 3.10+, standard library only. Start an OpenAI-compatible local server, then:

```bash
python3 trustmebro.py generate --seed 17 --out tasks.json
python3 trustmebro.py run --tasks tasks.json --url http://127.0.0.1:8080/v1 --model local --artifact /path/to/model.gguf --runtime 'llama.cpp COMMIT and flags' --hardware 'RTX 4090 24GB' --budgets 128,512,2048 --out run.json
python3 trustmebro.py score run.json
python3 -m unittest discover -s tests -v
```

Use a local server only; no model downloads or GPU processes are started by the harness. For sharded models supply --artifact repeatedly. Pin the actual server configuration, chat template, reasoning policy, GPU offload and model source in --runtime. Run separate profiles if these differ. A response that exhausts the cap is still graded; network errors are counted separately and the profile is incomplete.

## Results

[Evidence index](RESULTS.md). Core has **no measured model scores yet**; the synthetic self-test is not a model result. Historical results are labeled by suite and never merged into a composite. A single run is a pilot. Use multiple predeclared seeds and repeated decoding runs before claiming robust differences. Scores describe these task families, not general intelligence.

## Governance

See [protocol](PROTOCOL.md). The public generator is not a contamination-proof hidden test. Anyone can challenge our methodology or submit raw, reproducible results. Versions are frozen; changes to questions or scoring require a new protocol version.

MIT license.
