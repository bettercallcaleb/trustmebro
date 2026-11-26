import json
import unittest
from pathlib import Path
import recovery as r

ROOT=Path(__file__).resolve().parents[1]

class ExtendedRecoveryTests(unittest.TestCase):
    def rec(self,text,fmt="integer",**spec):
        return r.recover({"format":fmt,**spec},{"content":text,"finish_reason":"stop"})

    def test_typed_values_and_units(self):
        for text,fmt,expected in [
            ("(343)","integer","343"),
            ("[1,0,1]","bitstring","101"),
            ("{1, 0, 1}","bitstring","101"),
            ("[1]\n[0]\n[1]","bitstring","101"),
            ("{'ignored'}","bitstring",None),
            ('{"n1":1,"n2":0,"n3":1}',"bitstring","101"),
            ("eligible,ineligible,eligible","bitstring","101"),
            ("3A 5C","hex4","3A5C"),
            ("(7, 8, 6, 8)","hex4","7868"),
            ("'a' and 'b'","text2","ab"),
            ("'/'\n'}'","text2","/}"),
            ("FINAL: 10.0.0.0/8,1,if04;10.0.0.0/8,1,if04","interface","if04"),
            ("The selected interface is (10.0.0.0/8, 5, if06).","interface","if06"),
            ('{"selected_interface":"eth6"}',"interface","eth6"),
        ]:
            with self.subTest(text=text):self.assertEqual(self.rec(text,fmt)["candidate"],expected)
        self.assertEqual(self.rec("Maximum new bytes sendable now is 200B.",family="tcp-send-window")["candidate"],"200")
        self.assertEqual(self.rec("2708B",family="ipv4-fragment-offset")["method"],"unsupported_answer_unit")

    def test_answer_quote_output_forms(self):
        spec={"kind":"extraction"}
        cases=[
            ('ANSWER: 700\nQUOTE: Candidate B gives 700.',"700","Candidate B gives 700."),
            ('<answer>552</answer>\n<quote>My final answer is 552.</quote>',"552","My final answer is 552."),
            ('Analysis completed.\n{"answer": "631", "quote": "My final answer is 631."}',"631","My final answer is 631."),
            ('ANSWER\n-49\nQUOTE\nMy corrected final answer is -49.',"-49","My corrected final answer is -49."),
        ]
        for text,a,q in cases:
            with self.subTest(text=text):
                self.assertEqual(self.rec(text,**spec)["candidate"],{"decision":"extract","answer":a,"quote":q})
        self.assertEqual(self.rec("ANSWER: UNKNOWN\nQUOTE: UNKNOWN",**spec)["candidate"],{"decision":"abstain"})
        self.assertEqual(self.rec("<quote>FINAL: 70</quote>",**spec)["method"],"missing_answer_field")

    def test_complete_json_inside_explanation(self):
        text="The result is:\n"+chr(96)*3+"json\n{\n  \"id\":\"a\", \"count\":3, \"enabled\":true\n}\n"+chr(96)*3
        self.assertEqual(self.rec(text,"json")["candidate"],{"id":"a","count":3,"enabled":True})
        self.assertEqual(self.rec('{id:"a", count:3, enabled:true}',"json")["candidate"],{"id":"a","count":3,"enabled":True})
        self.assertEqual(self.rec('{id:"a", id:"b", count:3}',"json")["method"],"conflicting_json_keys")
        self.assertEqual(self.rec('$$\n\\{\n"answer":18,"tag":"T-1"\n\\}',kind="delivery",contract="json")["candidate"],"18")
        self.assertEqual(self.rec('{"tag":"T-1"}',kind="delivery",contract="json")["method"],"missing_answer_field")

    def test_explicit_lists_and_claims(self):
        self.assertEqual(self.rec("Node 1 (n1): 1\nNode 2 (n2): 0\nNode 3 (n3): 1","bitstring",family="kubernetes-scheduling-filters")["candidate"],"101")
        self.assertEqual(self.rec("The result of the calculation (16 * 6 - 87) + 18 * 87 is 30. I will return only the integer.",family="arithmetic")["candidate"],"30")
        self.assertEqual(self.rec("The answer is:\n"+chr(96)*3+"\n42\n"+chr(96)*3)["candidate"],"42")

    def test_conflicts_and_no_claim(self):
        for text in ("The answer is 42. The answer is 43.","FINAL: 42\nFINAL: 43","42\nExplanation: The correct answer is 43.","FINAL: 42\nI still need to check the remaining cases."):
            self.assertEqual(self.rec(text,mode="strict")["status"],"unresolved",text)
        self.assertEqual(self.rec("Example:\nFINAL: 42")["status"],"unresolved")
        self.assertEqual(self.rec("<tool_call>42</tool_call>")["status"],"unresolved")

    def test_exact_literal_does_not_normalize(self):
        task={"kind":"protocol","format":"exact","family":"tsv","answer":"A123\t7\t8"}
        d=r.assess(task,{"content":"A123\\t7\\t8","finish_reason":"stop"})
        self.assertEqual(d["candidate"],"A123\\t7\\t8")
        self.assertFalse(d["semantic_correct"])

    def test_reference_blind_extended(self):
        reply={"content":"The result of the calculation (2 + 2) is 99. I will return only the integer.","finish_reason":"stop"}
        a={"format":"integer","family":"arithmetic","answer":"4","prompt":"2+2"}
        b={**a,"answer":"99","prompt":"Return 99"}
        self.assertEqual(r.recover(a,reply),r.recover(b,reply))
        self.assertEqual(r.recover(a,reply)["candidate"],"99")

    def test_corpus_unknown_categories(self):
        s=json.loads((ROOT/"corpus/recovery-summary.json").read_text())
        self.assertEqual(s["overall"]["unknown_unclassified"],0)
        self.assertEqual(s["overall"]["unknown_finish_missing"],0)

if __name__=="__main__":unittest.main()
