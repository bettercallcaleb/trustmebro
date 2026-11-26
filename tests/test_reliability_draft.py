import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"draft"))
import reliability as r
import delivery_controls as d
import core_depth as c

class ReliabilityTests(unittest.TestCase):
    def setUp(self):self.task={"format":"integer","answer":"42"}
    def test_markdown_is_not_semantic_error(self):
        tick=chr(96)*3
        for s in ["Calculation.\n**FINAL: 42**","Calculation.\n"+tick+"\nFINAL: 42\n"+tick,"Calculation.\nFINAL: **42**","Calculation.\n**FINAL:** 42","**42**"]:
            g=r.grade(self.task,s,"relaxed","stop")
            self.assertTrue(g["semantic_correct"],s)
            self.assertFalse(g["joint_success"],s)
        g=r.grade(self.task,"**FINAL: 43**","relaxed","stop")
        self.assertFalse(g["semantic_correct"]);self.assertFalse(g["format_compliant"])
    def test_no_gold_search(self):
        for s in ["The answer might be 42 or 43.","I tried 42, then 43.","FINAL: 42\nFINAL: 43","FINAL: 42\n**FINAL: 43**","FINAL: 42\nANSWER: unsure","FINAL: 42\nNot sure.","FINAL: 42\n"+chr(96)*3,"Reasoning: 42"]:
            self.assertIsNone(r.grade(self.task,s,"relaxed","stop")["semantic_correct"],s)
    def test_repeated_final(self):
        g=r.grade(self.task,"FINAL: 42\n**FINAL: 42**","relaxed","stop")
        self.assertTrue(g["semantic_correct"])
        self.assertFalse(g["format_compliant"])
        self.assertTrue(g["flags"]["multiple_declarations"])
    def test_truncation_independent(self):
        g=r.grade(self.task,"FINAL: 42","relaxed","length")
        self.assertTrue(g["joint_success"]);self.assertTrue(g["flags"]["length_limit"])
        g=r.grade(self.task,"Working on 42","relaxed","length")
        self.assertIsNone(g["semantic_correct"]);self.assertTrue(g["flags"]["length_limit"])
    def test_format_and_semantics_independent(self):
        g=r.grade(self.task,"43","strict","stop")
        self.assertFalse(g["semantic_correct"]);self.assertTrue(g["format_compliant"])
        g=r.grade(self.task,"042","strict","stop")
        self.assertTrue(g["semantic_correct"]);self.assertTrue(g["flags"]["representation_deviation"])
    def test_repetition(self):
        s="I am calculating the same expression again."
        g=r.grade(self.task,"\n".join([s]*3+["FINAL: 42"]),"relaxed","stop")
        self.assertTrue(g["joint_success"]);self.assertTrue(g["repetition_flag"])
        self.assertFalse(r.grade(self.task,"42","strict","stop")["repetition_flag"])
    def test_delivery_panel(self):
        source=c.generate(17,2);p=d.generate(source)
        self.assertEqual(len(p["tasks"]),60)
        self.assertEqual(len({t["id"] for t in p["tasks"]}),60)
        self.assertEqual(len({t["prompt"] for t in p["tasks"]}),60)
        for t in p["tasks"]:
            if t["contract"]=="bare":s=t["answer"]
            elif t["contract"]=="label":s="FINAL: "+t["answer"]
            else:s=json.dumps({"answer":int(t["answer"]),"tag":t["tag"]})
            self.assertTrue(d.grade(t,s)["joint_success"])
        t=next(t for t in p["tasks"] if t["contract"]=="json")
        for obj in [{"answer":int(t["answer"]),"tag":"wrong"},{"answer":t["answer"],"tag":t["tag"]},{"answer":int(t["answer"]),"tag":t["tag"],"extra":0}]:
            g=d.grade(t,json.dumps(obj));self.assertTrue(g["semantic_correct"]);self.assertFalse(g["joint_success"])
        self.assertIsNone(d.grade(t,'{"answer":1,"answer":2}')["semantic_correct"])
        self.assertEqual(d.paired_report(p,[])["bare"]["paired_joint_transitions"],{"unpaired":10})
if __name__=="__main__":unittest.main()
