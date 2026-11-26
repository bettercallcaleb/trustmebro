# Answer recovery v0.1

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
| Correct | 697 | 744 |
| Wrong | 610 | 844 |
| Unknown | 1741 | 1460 |
| Joint success | 426 | 426 |

289 formerly unknown replies receive a candidate judgment; 8 formerly wrong replies become unresolved under the conservative recovery rules. No originally correct replies are lost on this development corpus. The corpus is used to develop the recovery rules, not an independent holdout. These are replayed annotations, not an independently established precision/recall estimate.

## Label-by-label policy

| Label | Policy | Events | Remaining unknown |
| --- | --- | ---: | ---: |
| alternative_label | explicit_declaration | 4 | 0 |
| bit_delimiter | normalize_bit_separators | 17 | 0 |
| bit_width | retain_complete_wrong_width | 34 | 4 |
| code_fence | unwrap_balanced_wrapper | 145 | 12 |
| contract_violation | preserve_original_contract_score | 2207 | 1457 |
| csv_length_mismatch | retain_complete_sequence | 36 | 5 |
| csv_space | normalize_csv_separators | 20 | 1 |
| duplicate_json_keys | collapse_identical_keys_only | 4 | 4 |
| empty_final_label | inspect_adjacent_value_or_abstain | 10 | 10 |
| empty_output | abstain_no_answer | 1 | 1 |
| error_code_width | retain_complete_wrong_width | 2 | 0 |
| extra_outer_whitespace | preserve_literal_contract | 18 | 0 |
| extra_text | terminal_explicit_commitment_only | 34 | 0 |
| false_extraction | retain_extracted_claim | 95 | 0 |
| hex_width | retain_complete_wrong_width | 10 | 3 |
| inline_code | unwrap_balanced_wrapper | 2 | 1 |
| invalid_json | parse_complete_json_or_abstain | 76 | 25 |
| irrelevant_quote | retain_claim_evaluate_evidence_separately | 70 | 0 |
| json_abstention | explicit_abstention | 11 | 0 |
| json_array_length_mismatch | retain_complete_json | 4 | 0 |
| json_key_set_mismatch | retain_complete_json | 6 | 1 |
| json_type_mismatch | retain_typed_json | 5 | 0 |
| leading_role_marker | strip_assistant_prefix_only | 33 | 28 |
| length_limit | abstain_unless_repeated_complete_declarations | 991 | 987 |
| literal_mismatch | retain_literal | 86 | 35 |
| malformed_declaration | bounded_declaration_parser | 103 | 60 |
| markdown_emphasis | unwrap_balanced_wrapper | 87 | 11 |
| markdown_wrapper | unwrap_balanced_wrapper | 308 | 24 |
| missing_keys | retain_claim_if_present | 12 | 0 |
| missing_quote | retain_claim_evaluate_evidence_separately | 1 | 0 |
| multiple_declarations | require_consistent_commitments | 32 | 16 |
| noncanonical_abstention | explicit_abstention | 11 | 0 |
| noncanonical_label | explicit_declaration | 875 | 733 |
| nonterminal_declaration | abstain_if_subsequent_text | 17 | 17 |
| octal_width | retain_complete_wrong_width | 18 | 0 |
| periodic_numeric_output | retain_complete_sequence_or_abstain_if_truncated | 16 | 16 |
| quote_not_in_source | retain_claim_evaluate_evidence_separately | 58 | 0 |
| repeated_answer_declaration | collapse_identical_complete_declarations | 15 | 6 |
| repeated_thinking_marker | strip_orphan_closing_prefix_only | 2 | 2 |
| representation_deviation | normalize_representation_without_guessing | 70 | 1 |
| tab_to_comma_substitution | retain_wrong_literal | 17 | 3 |
| tag_error | retain_claim_preserve_contract | 5 | 1 |
| thinking_marker_in_visible_output | strip_thought_boundary_only | 141 | 73 |
| tool_marker_in_visible_output | abstain_tool_content | 1 | 1 |
| truncated_declaration_prefix | require_repeated_identical_complete_declarations | 1 | 0 |
| unresolved_decision | conservative_recovery_or_abstain | 1741 | 1452 |
| value_used_as_key | retain_wrong_structure | 5 | 0 |
| wrong_answer_type | safe_integer_field_conversion_only | 80 | 1 |
| wrong_output_entity_cidr | retain_wrong_entity | 3 | 1 |
| wrong_value | retain_claim | 515 | 8 |

Counts overlap across labels. A strategy does not imply every occurrence is recoverable. Generic contract and value flags retain the independently determined candidate. Other observations remain diagnostic only; evaluator gaps are not attributed to model failures.

## Commands

    python3 recovery.py run run.json --out recovered.json
    python3 recovery.py corpus corpus/responses.jsonl --out corpus-replay.json
    python3 failure_corpus.py diagnose-run run.json --out diagnostics.json

The official v0.2 score is frozen. The diagnostic output contains the original score, recovered candidate, recovered correctness, evidence support, unchanged contract compliance, recovery method and explicit unresolved reason. Transport errors and missing attempts are reported separately. No new model inference is required.
