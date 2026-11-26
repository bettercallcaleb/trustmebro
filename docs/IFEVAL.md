# IFEval reference adapter

Use the official Google Research source at revision e6890f85757dd84e27ca6df2dd30651dafad28e0. It is not bundled.

```bash
git clone --filter=blob:none --sparse https://github.com/google-research/google-research.git
cd google-research
git sparse-checkout set instruction_following_eval
git checkout e6890f85757dd84e27ca6df2dd30651dafad28e0
python -m pip install -r instruction_following_eval/requirements.txt
python -m nltk.downloader punkt punkt_tab
cd ..
python3 trustmebro.py ifeval run --ifeval-root ./google-research --model local --max-tokens 2048 --out ifeval.jsonl
python3 trustmebro.py ifeval score --ifeval-root ./google-research --out ifeval.jsonl
```

Full 541 prompts by default. Optional --limit selects a deterministic diagnostic subset; disclose the subset size. Upstream source hashes, the dataset hash and prompt-level and instruction-level strict and loose metrics are recorded. No extra system prompt is used. This is a separate adapter with its own JSONL format, not a v0.2 combined manifest. The caller must record and control the external runtime, model identity, reasoning policy and decoding settings; unlike the Core/Ladder runner this adapter currently does not hash model files. Cite Zhou et al. (2023), https://arxiv.org/abs/2311.07911.

The bundled ConceptLadder measurement adapter is maintained separately from the unified Core/Ladder report.
