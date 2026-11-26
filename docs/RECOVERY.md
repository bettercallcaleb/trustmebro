# Answer recovery v0.4

Recovery answers a different question from strict compliance: what did the model actually commit to?

## Invariants

- Recovery receives only kind, format, family, contract and mode plus the original reply and termination metadata. No reference value, prompt, evidence, supplied tag or task solution is available to the recovery function.
- Comparison occurs only after candidate extraction. Strict compliance and legacy scores are retained. Evidence is independently checked against the source and designated decisive statements.
- A wrong answer is not repaired into a correct one. Numeric formatting equivalence follows the existing semantic normalizer for hexadecimal, octal, error codes and interfaces; raw recovered spelling remains visible. Exact literal tasks and typed protocol JSON are compared without changing case, leading zeros or types.
- Repeated identical declarations and equivalent duplicate JSON keys can be recovered; conflicting declarations and conflicting duplicate keys are not guessed. No arbitrary last-number selection. A bare value cut off at the token limit is unresolved unless a complete structured or explicitly delimited commitment is demonstrable.
- Detectors may use reference information for diagnostic labels, but those labels do not feed back into candidate selection. Recovery uses shared shape-specific parsers rather than 50 independent rewrites.

## Frozen-corpus replay

| Outcome | Original | Recovered |
| --- | ---: | ---: |
| Correct | 697 | 879 |
| Wrong | 610 | 1113 |
| Unknown | 1741 | 1056 |
| Joint success | 426 | 426 |

691 formerly unknown replies receive a candidate judgment. 6 formerly wrong replies become unresolved under conservative recovery. No formerly correct replies are lost. The development corpus is not an independent holdout. Recovered labels are not independently established ground truth.

## Label-by-label policy

| Label | Policy | Events | Remaining unknown |
| --- | --- | ---: | ---: |
| alternative_label | explicit_declaration | 4 | 0 |
| bit_delimiter | normalize_bit_separators | 17 | 0 |
| bit_width | retain_complete_wrong_width | 34 | 4 |
| code_fence | unwrap_balanced_wrapper | 145 | 5 |
| contract_violation | preserve_original_contract_score | 2207 | 1053 |
| csv_length_mismatch | retain_complete_sequence | 36 | 4 |
| csv_space | normalize_csv_separators | 20 | 1 |
| duplicate_json_keys | collapse_identical_keys_only | 4 | 3 |
| empty_final_label | inspect_adjacent_value_or_abstain | 10 | 10 |
| empty_output | abstain_no_answer | 1 | 1 |
| error_code_width | retain_complete_wrong_width | 2 | 0 |
| extra_outer_whitespace | preserve_literal_contract | 18 | 0 |
| extra_text | terminal_explicit_commitment_only | 34 | 0 |
| false_extraction | retain_extracted_claim | 95 | 0 |
| hex_width | retain_complete_wrong_width | 10 | 3 |
| inline_code | unwrap_balanced_wrapper | 2 | 0 |
| invalid_json | parse_complete_json_or_abstain | 76 | 8 |
| irrelevant_quote | retain_claim_evaluate_evidence_separately | 70 | 0 |
| json_abstention | explicit_abstention | 11 | 0 |
| json_array_length_mismatch | retain_complete_json | 4 | 0 |
| json_key_set_mismatch | retain_complete_json | 6 | 1 |
| json_type_mismatch | retain_typed_json | 5 | 0 |
| leading_role_marker | strip_assistant_prefix_only | 33 | 24 |
| length_limit | abstain_unless_repeated_complete_declarations | 991 | 987 |
| literal_mismatch | retain_literal | 86 | 15 |
| malformed_declaration | bounded_declaration_parser | 103 | 24 |
| markdown_emphasis | unwrap_balanced_wrapper | 87 | 4 |
| markdown_wrapper | unwrap_balanced_wrapper | 308 | 9 |
| missing_keys | retain_claim_if_present | 12 | 0 |
| missing_quote | retain_claim_evaluate_evidence_separately | 1 | 0 |
| multiple_declarations | require_consistent_commitments | 32 | 9 |
| noncanonical_abstention | explicit_abstention | 11 | 0 |
| noncanonical_label | explicit_declaration | 875 | 676 |
| nonterminal_declaration | abstain_if_subsequent_text | 17 | 12 |
| octal_width | retain_complete_wrong_width | 18 | 0 |
| periodic_numeric_output | retain_complete_sequence_or_abstain_if_truncated | 16 | 16 |
| quote_not_in_source | retain_claim_evaluate_evidence_separately | 58 | 0 |
| repeated_answer_declaration | collapse_identical_complete_declarations | 15 | 5 |
| repeated_thinking_marker | strip_orphan_closing_prefix_only | 2 | 2 |
| representation_deviation | normalize_representation_without_guessing | 70 | 1 |
| tab_to_comma_substitution | retain_wrong_literal | 17 | 2 |
| tag_error | retain_claim_preserve_contract | 5 | 1 |
| thinking_marker_in_visible_output | strip_thought_boundary_only | 141 | 57 |
| tool_marker_in_visible_output | abstain_tool_content | 1 | 1 |
| truncated_declaration_prefix | require_repeated_identical_complete_declarations | 1 | 0 |
| unresolved_decision | conservative_recovery_or_abstain | 1741 | 1050 |
| value_used_as_key | retain_wrong_structure | 5 | 0 |
| wrong_answer_type | safe_integer_field_conversion_only | 80 | 1 |
| wrong_output_entity_cidr | retain_wrong_entity | 3 | 1 |
| wrong_value | retain_claim | 515 | 6 |

Counts overlap across labels. A strategy does not imply every occurrence is recoverable. Generic contract and value flags retain the independently determined candidate. Other observations remain diagnostic only; evaluator gaps are not attributed to model failures.

## Commands

    python3 recovery.py run run.json --out recovered.json
    python3 recovery.py corpus corpus/responses.jsonl --out corpus-replay.json
    python3 failure_corpus.py diagnose-run run.json --out diagnostics.json

The official v0.2 score is frozen. The diagnostic output contains the original score, recovered candidate, recovered correctness, evidence support, unchanged contract compliance, recovery method and explicit unresolved reason. Transport errors and missing attempts are reported separately. No new model inference is required.

## Unknown is an outcome, not a diagnosis

Each unresolved reply receives exactly one primary unknown_reason. A confirmed length finish takes precedence, and the original recovery blocker remains in unknown_detail. Otherwise the reason describes the observed blocker, such as conflicting declarations, an empty declaration, malformed declaration, nonterminal declaration, explicit uncertainty, special markers, invalid or unresolved structured claims, or an unsupported format. unclassified_response is reserved for replies where the current parser cannot establish a specific cause. Known blockers do not establish the model's underlying failure mechanism; ambiguous/parser-limited cases are marked review_required.

Termination is independently recorded for every reply: stop, length, missing, or other. A truncated reply can still contain a recoverable correct or wrong answer. Missing finish metadata is not evidence of truncation or normal completion. Transport errors and unrun tasks remain outside response-level unknown counts.

Each report and profile includes:
- unknown_breakdown: mutually exclusive primary reasons that sum exactly to remaining_unknown.
- unknown_details: the recovery-level blocker, including for truncated replies.
- unknown_truncated, unknown_nontruncated, unknown_finish_missing: a mutually exclusive termination partition of unresolved replies.
- unknown_unclassified: residual unexplained replies, across termination categories.
- unknown_nontruncated_classified: stopped or otherwise non-length replies with a specific observed blocker.
- unknown_review_required: cases where an independent review may reveal parser limitations.
- termination_by_semantic_outcome: separate correct/wrong/unknown counts at each termination state.

## Extended recovery and unresolved-case audit

The secondary parser handles explicit answer/quote fields, bounded JSON blocks and unquoted keys, literal character pairs, bit vectors and ordered status rows, interface names and route tuples, narrowly scoped units, terminal answer phrases and answer-first outputs. It runs only on normally stopped replies left unresolved by the primary parser. Conflicting claims, missing answer fields, prompt/source echoes, unsupported units and malformed structured payloads remain unresolved rather than being guessed.

The frozen development corpus now has zero unclassified responses, but 987 length-limited and 69 other unresolved responses remain. This is classification coverage on known data, not a guarantee that all semantic judgments are correct or that future unseen responses can be recovered. See [non-truncated unresolved cases](../corpus/nontruncated-unresolved.jsonl) for the response fingerprints, blockers and excerpts. New unknown forms remain in the unclassified review queue.

The first formal batch (seed 601, 912 requests across BF16/Q4_K_M/Q2_K) has 203 remaining unresolved responses: 201 truncated and two conflicting answer declarations, with zero unclassified. Original raw runs and original scores remain unchanged. The first formal batch was also used during development; it is not an independent validation set.

## Second formal batch replay

Recovery v0.4 adds bounded family-specific conclusion patterns, decimal and malformed identifier claims without correcting their values, explicitly written byte-equation and bitwise-expression results, and explicit withdrawal of a prior standalone answer. It does not calculate the answer or infer missing identifier prefixes. Conflicting commitments without an explicit withdrawal remain unresolved.

Across the second formal batch (three Q4_K_M models, 912 requests), 28 previously unclassified replies and four other unresolved replies were recovered. Remaining unresolved: 230 truncated and two conflicting declarations. The 3,048-response development corpus retains exactly the same per-row semantic judgments as v0.3. Both formal batches contain zero unclassified replies after replay. These batches informed development and are not an independent holdout.
