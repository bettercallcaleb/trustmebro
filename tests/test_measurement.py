import unittest
import measurement as m
import trustmebro as t

class MeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=m.generate(211,2,"all",1)
        cls.tasks=cls.manifest["tasks"]
    def test_integration(self):
        self.assertEqual(len(self.tasks),76)
        self.assertEqual(len({x["id"] for x in self.tasks}),76)
        m.verify(self.manifest)
        for x in self.tasks:
            s=t.canonical(x["answer"]) if x["format"]=="json" else str(x["answer"])
            g=m.grade(x,s,"strict","stop")
            self.assertTrue(g["joint_success"],(x,g))
            self.assertTrue(m.grade(x,"Reasoning.\nFINAL: "+s,"relaxed","stop")["joint_success"],x)
    def test_separation(self):
        x={"format":"integer","answer":"42"}
        self.assertEqual(m.grade(x,"43","strict","stop")["semantic_correct"],False)
        self.assertTrue(m.grade(x,"43","strict","stop")["format_compliant"])
        g=m.grade(x,"The answer is 42.","strict","stop")
        self.assertTrue(g["semantic_correct"]);self.assertFalse(g["joint_success"])
        self.assertIsNone(m.grade(x,"42\nor 43","strict","stop")["semantic_correct"])
        self.assertIsNone(m.grade(x,"FINAL: 42\nFINAL: 43","relaxed","stop")["semantic_correct"])
    def test_json(self):
        x=next(x for x in self.tasks if x["format"]=="json")
        s=t.canonical(x["answer"])
        self.assertFalse(m.grade(x,chr(96)*3+"json\n"+s+"\n"+chr(96)*3,"strict","stop")["format_compliant"])
        self.assertTrue(m.grade(x,chr(96)*3+"json\n"+s+"\n"+chr(96)*3,"strict","stop")["semantic_correct"])
        self.assertIsNone(m.grade(x,'{"id":"a","id":"b"}',"strict","stop")["semantic_correct"])
    def test_fixed_denominator(self):
        x={"format":"integer","answer":"42"}
        rows=[]
        for s,cost in [("42",2),("43",3),("unknown",20),("Answer: 42",5)]:
            rows.append({"grade":m.grade(x,s,"strict","stop"),"elapsed_s":cost/10,"raw":{"usage":{"completion_tokens":cost}}})
        r=m.report(rows,4)
        self.assertEqual((r["confirmed_correct_rate"],r["confirmed_wrong_rate"],r["unknown_rate"]),(.5,.25,.25))
        self.assertEqual(r["tokens_per_success"],30)
        self.assertEqual(r["strict_accuracy"],.25)
        self.assertEqual(r["error_matrix"]["correct_noncompliant"],1)
        self.assertEqual(r["error_matrix"]["wrong_compliant"],1)
        self.assertIsNone(m.report(rows,5)["tokens_per_success"])
        self.assertEqual(m.report(rows,5)["unknown_rate"],.4)
        self.assertIsNone(m.report(rows+[{"error":"timeout","elapsed_s":1}],5)["tokens_per_success"])
    def test_separate_profiles(self):
        run={"manifest":self.manifest,"manifest_sha256":t.digest(self.manifest),"budgets":[64],"modes":["strict"],"protocol":m.protocol(),"rows":[]}
        ps=m.score(run)
        self.assertEqual([p["n"] for p in ps],[16,60])
        self.assertTrue(all(p["unknown_rate"]==1 and not p["complete"] for p in ps))
        self.assertEqual(ps[1]["depth_lower"],0);self.assertEqual(ps[1]["depth_upper"],4)
    def test_repetition_flag(self):
        self.assertTrue(m.repetition_diagnostic("let us repeat the same calculation again "*5))
        self.assertFalse(m.repetition_diagnostic("42"*100))
    def test_protocol_mismatch(self):
        run={"manifest":self.manifest,"manifest_sha256":t.digest(self.manifest),"budgets":[64],"modes":["strict"],"protocol":{},"rows":[]}
        with self.assertRaises(ValueError):m.score(run)
    def test_truncation_independent(self):
        x={"format":"integer","answer":"42"}
        r=m.grade(x,"42","strict","length")
        self.assertTrue(r["joint_success"]);self.assertTrue(r["truncated"])
if __name__=="__main__":unittest.main()
