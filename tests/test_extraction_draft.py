import collections
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"draft"))
import extraction as e

class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.m=e.generate(17,2)
        self.pos=next(t for t in self.m["tasks"] if t["polarity"]=="answerable")
        self.neg=next(t for t in self.m["tasks"] if t["root"]==self.pos["root"] and t["polarity"]=="unanswerable")
    def answer(self,task):
        return "UNKNOWN" if task["answer"] is None else json.dumps({"answer":task["answer"],"quote":task["evidence"][0]})
    def test_panel(self):
        e.verify(self.m)
        self.assertEqual(len(self.m["tasks"]),32)
        self.assertEqual(collections.Counter(t["polarity"] for t in self.m["tasks"]),{"answerable":16,"unanswerable":16})
        for t in self.m["tasks"]:
            self.assertTrue(e.grade(t,self.answer(t))["joint_success"])
            if t["answer"] is not None:self.assertTrue(all(q in t["response"] for q in t["evidence"]))
    def test_overextraction(self):
        t=self.neg
        self.assertIn(self.pos["answer"],t["response"])
        q=next(line for line in t["response"].splitlines() if self.pos["answer"] in line)
        g=e.grade(t,json.dumps({"answer":self.pos["answer"],"quote":q}))
        self.assertTrue(g["quote_exact"]);self.assertFalse(g["quote_relevant"])
        self.assertTrue(g["flags"]["false_extraction"]);self.assertFalse(g["joint_success"])
    def test_wrong_quote(self):
        g=e.grade(self.pos,json.dumps({"answer":self.pos["answer"],"quote":"invented "+self.pos["answer"]}))
        self.assertTrue(g["semantic_correct"]);self.assertTrue(g["format_compliant"])
        self.assertTrue(g["flags"]["quote_not_in_source"]);self.assertFalse(g["joint_success"])
        g=e.grade(self.pos,json.dumps({"answer":self.pos["answer"],"quote":self.pos["answer"]}))
        self.assertTrue(g["quote_exact"]);self.assertFalse(g["quote_relevant"]);self.assertFalse(g["joint_success"])
    def test_type_and_wrapper(self):
        g=e.grade(self.pos,json.dumps({"answer":int(self.pos["answer"]),"quote":self.pos["evidence"][0]}))
        self.assertTrue(g["semantic_correct"]);self.assertTrue(g["quote_relevant"]);self.assertFalse(g["format_compliant"])
        g=e.grade(self.pos,"**"+self.answer(self.pos)+"**")
        self.assertTrue(g["semantic_correct"]);self.assertFalse(g["joint_success"])
        g=e.grade(self.neg,"**UNKNOWN**")
        self.assertTrue(g["semantic_correct"]);self.assertFalse(g["joint_success"])
    def test_abstention_and_ambiguity(self):
        self.assertTrue(e.grade(self.neg,"UNKNOWN")["joint_success"])
        self.assertTrue(e.grade(self.pos,"UNKNOWN")["flags"]["false_abstention"])
        self.assertIsNone(e.grade(self.pos,"I think "+self.pos["answer"])["semantic_correct"])
        self.assertIsNone(e.grade(self.pos,'{"answer":"1","answer":"2","quote":"x"}')["semantic_correct"])
        self.assertIsNone(e.grade(self.pos,'{"answer":true,"quote":"x"}')["semantic_correct"])
    def test_value_evidence_mismatch(self):
        g=e.grade(self.pos,json.dumps({"answer":str(int(self.pos["answer"])+1),"quote":self.pos["evidence"][0]}))
        self.assertTrue(g["quote_relevant"]);self.assertTrue(g["flags"]["quote_answer_mismatch"]);self.assertFalse(g["joint_success"])
    def test_report(self):
        rows=[]
        for t in self.m["tasks"]:
            rows.append({"id":t["id"],"budget":128,"elapsed_s":1.0,"raw":{"choices":[{"message":{"content":self.answer(t)},"finish_reason":"stop"}],"usage":{"completion_tokens":10}}})
        run={"version":e.VERSION,"budget":128,"manifest":self.m,"manifest_sha256":e.core.digest(self.m),"rows":rows}
        r=e.score(run)
        self.assertEqual(r["overall"]["joint_success"],32)
        self.assertEqual(r["paired_joint_outcomes"],{"pass/pass":16})
        self.assertEqual(r["overall"]["tokens_per_success"],10)
        run["rows"]=rows[:1]
        self.assertEqual(e.score(run)["overall"]["unknown"],31)
        self.assertIsNone(e.score(run)["overall"]["tokens_per_success"])
        run["rows"]=rows+[rows[0]]
        with self.assertRaises(ValueError):e.score(run)
    def test_cpu_audit(self):
        for seed in range(20):
            m=e.generate(seed,2)
            pairs=collections.defaultdict(list)
            for t in m["tasks"]:
                self.assertTrue(e.grade(t,self.answer(t))["joint_success"])
                pairs[t["root"]].append(t)
            for group in pairs.values():
                a=next(t for t in group if t["answer"] is not None)
                b=next(t for t in group if t["answer"] is None)
                self.assertIn(a["answer"],b["response"])
                self.assertNotEqual(a["response"],b["response"])

if __name__=="__main__":unittest.main()
