import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"draft"))
import response_taxonomy as t
import extraction as e

class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.m=e.generate(17,2)
        self.pos=next(x for x in self.m["tasks"] if x["family"]=="embedded_instruction" and x["polarity"]=="answerable")
        self.neg=next(x for x in self.m["tasks"] if x["root"]==self.pos["root"] and x["polarity"]=="unanswerable")
    def test_json_abstain(self):
        g=t.extraction_grade(self.neg,'{"answer":"UNKNOWN","quote":"not needed"}',"stop")
        self.assertTrue(g["semantic_correct"])
        self.assertFalse(g["format_compliant"])
        self.assertFalse(g["joint_success"])
        self.assertIn("json_abstention",g["flags"])
        self.assertIn("semantic_recognition_gap",g["flags"])
        self.assertNotIn("false_extraction",g["flags"])
    def test_false_extraction(self):
        q=next(x for x in self.neg["response"].splitlines() if self.pos["answer"] in x)
        g=t.extraction_grade(self.neg,json.dumps({"answer":self.pos["answer"],"quote":q}),"stop")
        self.assertFalse(g["semantic_correct"])
        self.assertIn("false_extraction",g["flags"])
        self.assertIn("irrelevant_quote",g["flags"])
        self.assertNotIn("fabricated_quote",g["flags"])
    def test_reference_line(self):
        q=next(x for x in self.pos["response"].splitlines() if self.pos["evidence"][0] in x)
        g=t.extraction_grade(self.pos,json.dumps({"answer":self.pos["answer"],"quote":q}),"stop")
        self.assertTrue(g["joint_success"])
        self.assertEqual(g["flags"],["reference_coverage_gap"])
        self.assertFalse(g["legacy"]["joint_success"])
    def test_evidence_not_substring(self):
        g=t.extraction_grade(self.pos,json.dumps({"answer":self.pos["answer"],"quote":self.pos["answer"]}),"stop")
        self.assertTrue(g["semantic_correct"])
        self.assertFalse(g["joint_success"])
        self.assertIn("irrelevant_quote",g["flags"])
    def test_type_and_representation(self):
        q=self.pos["evidence"][0]
        g=t.extraction_grade(self.pos,json.dumps({"answer":int(self.pos["answer"]),"quote":q}),"stop")
        self.assertTrue(g["semantic_correct"])
        self.assertIn("wrong_answer_type",g["flags"])
        self.assertFalse(g["joint_success"])
        g=t.extraction_grade(self.pos,json.dumps({"answer":"+"+self.pos["answer"],"quote":q,"extra":0}),"stop")
        self.assertIn("noncanonical_number",g["flags"])
        self.assertIn("extra_keys",g["flags"])
    def test_invalid_and_duplicate(self):
        for s,flag in [('{"answer":"1","answer":"2"}',"duplicate_json_keys"),('{"answer":',"invalid_json")]:
            g=t.extraction_grade(self.pos,s,"stop")
            self.assertIsNone(g["semantic_correct"])
            self.assertIn(flag,g["flags"])
    def test_no_recover_competing_fields(self):
        g=t.extraction_grade(self.neg,'{"answer":"UNKNOWN","alternative":1}',"stop")
        self.assertIsNone(g["semantic_correct"])
        self.assertIn("extra_keys",g["flags"])
    def test_reasoning_multiflags(self):
        g=t.reasoning_grade({"format":"integer","answer":"42"},"**FINAL: 42**","relaxed","length",130,128)
        self.assertTrue(g["semantic_correct"])
        self.assertFalse(g["joint_success"])
        self.assertIn("markdown_emphasis",g["flags"])
        self.assertIn("length_limit",g["flags"])
        self.assertIn("reported_tokens_over_cap",g["flags"])
    def test_summary_fixed_denominator(self):
        g=t.extraction_grade(self.neg,"UNKNOWN","stop")
        a=t.summarize([{"diagnostic":g,"tokens":1,"elapsed_s":0.1},{"tokens":None,"elapsed_s":1}],4)
        self.assertEqual(a["joint_success"],1)
        self.assertEqual(a["buckets"]["not_run"],2)
        self.assertEqual(a["buckets"]["transport_error"],1)
        self.assertEqual(sum(a["buckets"].values()),4)
if __name__=="__main__":unittest.main()
