# Answer Extraction & Abstention — candidate module

A response can contain the correct number without providing a defensible final answer. This module evaluates the model as an extractor, not as a solver or a judge of mathematical truth. It must identify the author's completed answer and copy its decisive evidence, or explicitly abstain. It must not infer an answer from unfinished calculations.

## Task design

Eight paired families, two variants per family in the default review panel: 16 answerable and 16 unanswerable responses. Matched pairs reuse the same numeric candidates. Each request contains just one response; gold values, evidence keys, pair IDs, and polarity never enter the prompt.

| Family | Answerable | Unanswerable |
|---|---|---|
| Commitment | Author selects a candidate | Author has not decided |
| Correction | Earlier answer replaced | Earlier answer withdrawn without replacement |
| Conflict | Disagreement resolved | Contradictory values remain |
| Quoted example | Author's own result | Example mistaken for answer |
| Conditional | Applicable assumption established | Assumption still unresolved |
| Unfinished | Checks completed | Intermediate candidate only |
| Repeated answer | Same result explicitly affirmed | Repeated unverified intermediate result |
| Embedded instruction | Author's answer independent of pasted note | Instruction or candidate masquerades as answer |

Some answers appear before noncontradictory trailing text; some unanswerable cases contain FINAL labels. This is a synthetic development panel; semantic labeling is explicit by construction. The template vocabulary is public, and shallow shortcuts may remain. Before a larger comparison, review a fresh, independently paraphrased or independently annotated panel of real responses.

## Independent scoring

The output is exactly UNKNOWN for abstention, or a JSON object with string fields answer and quote. The quote must reproduce the complete decisive sentence or line. A valid JSON object containing the correct number is not sufficient if the citation is fabricated or irrelevant. Separate metrics:

- Decision correctness (extract versus abstain).
- Semantic correctness (correct extracted value or correct abstention), confirmed wrong, unresolved, all divided by planned items.
- Exact quotation presence in source and relevance to the designated conclusion; distinguish a wrong number paired with the right quote.
- Format compliance, including JSON value type, canonical decimal representation, no extra keys, no Markdown.
- False extraction on unanswerable cases, false abstention on answerable cases, wrong extracted values, citation missing, citation absent from source, citation irrelevant, truncation and repetition flags.
- Joint success: correct semantic result, valid original output contract, and relevant exact evidence for an extraction. A correct abstention requires no citation. Report both polarities and paired outcomes, plus cost per joint success. Infrastructure errors are separate. No combined score with other TrustMeBro tracks.

Exact quote matching is deliberately strict and uses authored allowable decisive statements. Real text may have multiple defensible spans not covered by a small synthetic generator. The scorer does not infer unstated evidence or search for a favorable gold number. Unknown is a successful decision when the source truly contains no committed answer; unresolved extractor output is different. The fixture audit is not a measure of model accuracy.

## Run only after review

This standalone CLI generates a frozen manifest, sends individual prompts to an existing local OpenAI-compatible endpoint, preserves raw replies and artifact hashes, and replays scoring. It does not start a GPU server or download models. The runner caps a single invocation at 64 requests and stops at the first transport error. Default review panel: 32 requests.

    python3 draft/extraction.py generate --seed 17 --variants 2 --out extraction-tasks.json
    python3 draft/extraction.py run --tasks extraction-tasks.json --url http://127.0.0.1:8080/v1 --model local --artifact /path/to/model.gguf --runtime "engine revision, template, reasoning settings" --hardware "RTX 4090" --budget 128 --out extraction-run.json
    python3 draft/extraction.py score extraction-run.json
    python3 draft/audit_extraction.py

A separate 24-request exploratory audit of 4B on earlier model responses motivated this module. That audit is not part of the generated panel and cannot establish its difficulty. Do not use the new extractor to overwrite old Unknown answers or silently change model rankings.

Review gate: inspect the 32-item panel, then use only a small approved calibration with positive and negative controls. Inspect false extractions and citations manually; revise ambiguous cases before freezing a new protocol. No new GPU runs are authorized by adding this module.
