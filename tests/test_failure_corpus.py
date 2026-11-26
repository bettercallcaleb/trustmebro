import hashlib
import json
from pathlib import Path
import unittest

import failure_corpus as fc

ROOT=Path(__file__).resolve().parents[1]

class FailureCorpusTests(unittest.TestCase):
    def label(self,task,text,finish="stop",prior=None):
        return fc.diagnose(task,{"content":text,"finish_reason":finish},prior)

    def test_repeated_complete_answer_and_truncated_prefix(self):
        prior={"score":{"semantic_correct":None,"format_compliant":False,"joint_success":False},"flags":["conflicting_declarations"]}
        d=self.label({"format":"csv","answer":"1,2,3"},"Final: 1,2,3\nFinal: 1,2,3\nFinal: 1,2","length",prior)
        self.assertIn("repeated_answer_declaration",d["labels"])
        self.assertIn("truncated_declaration_prefix",d["labels"])
        self.assertNotIn("conflicting_declarations",d["labels"])
        self.assertEqual(d["score_unchanged"],prior["score"])

    def test_distinct_answers_not_repaired(self):
        prior={"flags":["conflicting_declarations"]}
        d=self.label({"format":"integer","answer":"12"},"FINAL: 12\nFINAL: 13","stop",prior)
        self.assertIn("conflicting_declarations",d["labels"])
        self.assertNotIn("repeated_answer_declaration",d["labels"])

    def test_stop_is_not_truncation(self):
        d=self.label({"format":"csv","answer":"1,2,3"},"FINAL: 1,2,3\nFINAL: 1,2,3\nFINAL: 1,2")
        self.assertNotIn("truncated_declaration_prefix",d["labels"])

    def test_nested_duplicate_json(self):
        d=self.label({"format":"json","answer":{"a":{"x":1}}},'{"a":{"x":1,"x":2}}')
        self.assertIn("duplicate_json_keys",d["labels"])

    def test_nonfinite_json(self):
        for s in ('{"x":NaN}','{"x":1e9999}'):
            self.assertIn("invalid_json",self.label({"format":"json","answer":{"x":1}},s)["labels"])

    def test_json_types_and_length(self):
        d=self.label({"format":"json","answer":[91,"91",True,None,51]},'[91,"91",true,false]')
        self.assertIn("json_array_length_mismatch",d["labels"])
        self.assertIn("json_type_mismatch",d["labels"])
        for s in ("null","1","true",'"empty"','{"records":[]}'):
            self.assertIn("json_type_mismatch",self.label({"format":"json","answer":[]},s)["labels"])

    def test_value_used_as_key(self):
        d=self.label({"format":"json","answer":{"code":"0036","count":73}},'{"0036":{"count":73}}')
        self.assertIn("value_used_as_key",d["labels"])

    def test_cidr_explanation_not_wrong_entity(self):
        task={"format":"interface","answer":"if03"}
        d=self.label(task,"Matched 10.0.0.0/8\nFINAL: if03",prior={"flags":["interface_returned_cidr"]})
        self.assertNotIn("wrong_output_entity_cidr",d["labels"])
        self.assertIn("interface_returned_cidr",d["observations"])
        self.assertIn("wrong_output_entity_cidr",self.label(task,"10.0.0.0/8")["labels"])

    def test_periodic_and_valid_repetition(self):
        s="01"*40
        self.assertIn("periodic_numeric_output",self.label({"format":"bitstring","answer":"0010"},s)["labels"])
        self.assertNotIn("periodic_numeric_output",self.label({"format":"bitstring","answer":s},s)["labels"])

    def test_marker_alias_and_evaluator_separation(self):
        d=self.label({}, "</think>\n</think>\n</think>\n<tool_call>",prior={"flags":["think_tag_loop","reference_coverage_gap","format_noncompliant"]})
        self.assertEqual(d["evaluator_flags"],["reference_coverage_gap"])
        self.assertIn("repeated_thinking_marker",d["labels"])
        self.assertNotIn("think_tag_loop",d["labels"])
        self.assertIn("tool_marker_in_visible_output",d["labels"])

    def test_width_and_delimiter(self):
        self.assertIn("hex_width",self.label({"format":"hex4","answer":"587F"},"785D3A58")["labels"])
        self.assertIn("bit_delimiter",self.label({"format":"bitstring","answer":"001"},"1\n1\n1")["labels"])
        self.assertIn("tab_to_comma_substitution",self.label({"kind":"protocol","answer":"a\t1\t2"},"a,1,2.")["labels"])

    def test_empty_and_whitespace(self):
        self.assertIn("empty_output",self.label({},"")["labels"])
        d=self.label({"kind":"protocol","answer":"abc"},"abc\n",prior={"flags":["outer_whitespace"]})
        self.assertEqual(d["labels"],["extra_outer_whitespace"])

    def test_frozen_corpus(self):
        path=ROOT/"corpus"/"responses.jsonl"
        manifest=json.loads((path.parent/"manifest.json").read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),manifest["responses_sha256"])
        replay=fc.summarize(fc.records(path))
        self.assertEqual(replay,json.loads((path.parent/"summary.json").read_text()))
        self.assertEqual(replay["attempted"],3048)
        self.assertEqual(replay["by_model"],manifest["by_model"])

if __name__=="__main__":
    unittest.main()
