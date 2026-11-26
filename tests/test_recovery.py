import json
from pathlib import Path
import unittest
import recovery as r

ROOT=Path(__file__).resolve().parents[1]

class RecoveryTests(unittest.TestCase):
    def get(self,fmt,text,finish="stop",**spec):
        return r.recover({"format":fmt,**spec},{"content":text,"finish_reason":finish})

    def test_markdown_headers_fences(self):
        for text in (
            "**FINAL: 42**","**Final**: 42","### Answer:\n42",
            "### Final Answer:\nThe calculation gives the value.\nFINAL: 42",
            "Calculation.\n"+chr(96)*3+"\nFINAL: 42\n"+chr(96)*3,
            "Previous example.\n"+chr(96)*3+"\n19\n"+chr(96)*3+"\n### Final Answer:\n"+chr(96)*3+"\nFINAL: 42\n"+chr(96)*3,
            "### Final Answer:\n$$\n\\text{FINAL: } 42\n$$",
            "So the answer is **42**.",
            "RETURN: 42","</think>\n\nAssistant:\n42",
        ):
            self.assertEqual(self.get("integer",text)["candidate"],"42",text)

    def test_equation_is_not_recomputed(self):
        self.assertEqual(self.get("integer","2 + 2 = 99")["candidate"],"99")
        self.assertEqual(self.get("integer","2 + 2")["status"],"unresolved")
        self.assertEqual(self.get("integer","The remainder is:\n**6**")["candidate"],"6")

    def test_truncated_and_conflicting(self):
        for text in ("I tried 42 and 43.","FINAL: 42\nFINAL: 43","FINAL: 42\nNot sure.","Example:\nFINAL: 42","FINAL:","The answer might be 42.","If x then the answer is 42."):
            self.assertEqual(self.get("integer",text)["status"],"unresolved",text)
        for text in ("42","FINAL: 42","Working: 42"):
            self.assertEqual(self.get("integer",text,"length")["status"],"unresolved",text)
        self.assertEqual(self.get("integer","FINAL: 42\n","length")["candidate"],"42")

    def test_repeated_claim(self):
        self.assertEqual(self.get("csv","FINAL: 1,2,3\nFINAL: 1,2,3\nFINAL: 1,2","length")["candidate"],"1,2,3")
        self.assertEqual(self.get("csv","FINAL: 1,2,3\nFINAL: 1,2,4\nFINAL: 1,2","length")["status"],"unresolved")
        self.assertEqual(self.get("integer","3\n3")["candidate"],"3")

    def test_width_and_delimiters(self):
        self.assertEqual(self.get("bitstring","FINAL:\n1\n0\n1")["candidate"],"101")
        self.assertEqual(self.get("bitstring","7,0,1,0,1")["candidate"],"7,0,1,0,1")
        self.assertEqual(self.get("hex4","785D3A58")["candidate"],"785D3A58")
        self.assertEqual(self.get("octal","644")["candidate"],"644")
        self.assertTrue(r.compare({"format":"octal","answer":"0644"},self.get("octal","644"))[0])
        self.assertFalse(r.compare({"format":"hex4","answer":"3A58"},self.get("hex4","785D3A58"))[0])
        self.assertEqual(self.get("integer","4,400")["candidate"],"4400")
        self.assertEqual(self.get("integer","2500B",family="tcp-send-window")["candidate"],"2500")
        self.assertEqual(self.get("integer","/26",family="ipv4-cidr-boundaries")["candidate"],"26")
        self.assertEqual(self.get("integer","2500B")["status"],"unresolved")

    def test_structured_json(self):
        self.assertEqual(self.get("json",'{"x":1,"x":1}')["candidate"],{"x":1})
        for text in ('{"x":1,"x":2}','{"x":NaN}','{"x":1e999}','{"x":'):
            self.assertEqual(self.get("json",text)["status"],"unresolved",text)
        self.assertEqual(self.get("json",'{"x":1,"extra":2}')["candidate"],{"x":1,"extra":2})
        self.assertEqual(self.get("json",'{"code":"0036","count":"73"}',kind="protocol")["candidate"],{"code":"0036","count":"73"})
        self.assertEqual(self.get("json",'{"id":"a","count":"73","enabled":false}')["candidate"],{"id":"a","count":73,"enabled":False})

    def test_extraction_abstention_and_evidence(self):
        spec={"kind":"extraction","answer":"7","response":"My final answer is 7.","evidence":["My final answer is 7."]}
        reply={"content":'{"answer":7,"quote":"not in source"}',"finish_reason":"stop"}
        d=r.assess(spec,reply,{"score":{"semantic_correct":None,"format_compliant":False,"joint_success":False}})
        self.assertTrue(d["semantic_correct"]);self.assertFalse(d["evidence_supported"]);self.assertFalse(d["joint_success_recovered"])
        self.assertEqual(r.recover(spec,{"content":'{"answer":"UNKNOWN"}',"finish_reason":"stop"})["candidate"],{"decision":"abstain"})
        self.assertEqual(r.recover(spec,{"content":'{"answer":"UNKNOWN","other":"7"}',"finish_reason":"stop"})["status"],"unresolved")
        self.assertEqual(r.recover(spec,{"content":'{"answer":"7"}',"finish_reason":"stop"})["candidate"],{"decision":"extract","answer":"7","quote":None})

    def test_literal_not_repaired(self):
        task={"kind":"protocol","format":"exact","family":"leading_zero","answer":"0036"}
        self.assertFalse(r.compare(task,r.recover(task,{"content":"36","finish_reason":"stop"}))[0])
        task={"kind":"protocol","format":"exact","family":"literal_case","answer":"AbC"}
        self.assertFalse(r.compare(task,r.recover(task,{"content":"abc","finish_reason":"stop"}))[0])
        self.assertFalse(r.compare(task,r.recover(task,{"content":"AbC\n","finish_reason":"stop"}))[0])
        self.assertEqual(r.recover(task,{"content":"I do not know the answer.","finish_reason":"stop"})["status"],"unresolved")

    def test_wrong_entity_and_tool_boundary(self):
        self.assertEqual(self.get("interface","10.0.0.0/8")["candidate"],"10.0.0.0/8")
        self.assertEqual(self.get("interface","The selected interface is if09.")["candidate"],"if09")
        self.assertEqual(self.get("text2","The two ASCII characters in the answer are 'x' and 'y'.")["candidate"],"xy")
        self.assertEqual(self.get("integer","<tool_call>42</tool_call>")["status"],"unresolved")
        self.assertEqual(self.get("integer","<think>43</think>\n42")["candidate"],"42")

    def test_no_gold_or_prompt_access(self):
        reply={"content":"FINAL: 43","finish_reason":"stop"}
        a={"format":"integer","answer":"42","prompt":"Return 42","evidence":["42"],"tag":"42"}
        b={"format":"integer","answer":"43","prompt":"Return 43","evidence":["43"],"tag":"43"}
        self.assertEqual(r.recover(a,reply),r.recover(b,reply))
        self.assertEqual(r.public_spec(a),{"format":"integer"})
        self.assertFalse(r.compare(a,r.recover(a,reply))[0])
        self.assertTrue(r.compare(b,r.recover(b,reply))[0])

    def test_label_policy_coverage(self):
        labels=json.loads((ROOT/"corpus/summary.json").read_text())["label_counts"]
        self.assertEqual(set(labels)-set(r.STRATEGIES),set())

    def test_unknown_reason_partition(self):
        task={"format":"integer","answer":"42"}
        cases=[
            ("42","stop",None),
            ("43","stop",None),
            ("FINAL: 42\n","length",None),
            ("Working on it","length","truncated"),
            ("<tool_call>42</tool_call>","length","truncated"),
            ("","stop","empty_output"),
            ("FINAL:","stop","empty_declaration"),
            ("FINAL: 42\nFINAL: 43","stop","conflicting_declarations"),
            ("FINAL: xyz","stop","malformed_declaration"),
            ("FINAL: 42\nNot sure.","stop","nonterminal_declaration"),
            ("The answer might be 42.","stop","uncertain_claim"),
            ("<tool_call>42</tool_call>","stop","special_marker_blocked"),
            ("Something else","stop","unclassified_response"),
            ("Something else",None,"unclassified_response"),
        ]
        rows=[]
        for text,finish,reason in cases:
            d=r.assess(task,{"content":text,"finish_reason":finish})
            self.assertEqual(d["unknown_reason"],reason,text)
            rows.append(d)
        summary=r.report(rows)
        self.assertEqual(summary["remaining_unknown"],11)
        self.assertEqual(summary["unknown_truncated"],2)
        self.assertEqual(summary["unknown_nontruncated"],8)
        self.assertEqual(summary["unknown_finish_missing"],1)
        self.assertEqual(summary["unknown_unclassified"],2)
        self.assertEqual(summary["unknown_nontruncated_classified"],7)
        self.assertEqual(summary["termination_by_semantic_outcome"]["length"],{"correct":1,"wrong":0,"unknown":2})
        self.assertEqual(sum(summary["unknown_breakdown"].values()),summary["remaining_unknown"])
        self.assertEqual(rows[4]["unknown_detail"],"special_marker_inside_response")
        self.assertTrue(rows[-1]["review_required"])
        self.assertIsNone(rows[-1]["truncated"])

    def test_structured_unknown_reasons(self):
        task={"format":"json","answer":{"x":1}}
        for text,expected in [('{"x":1,"x":2}',"conflicting_json_keys"),('{"x":',"structured_claim_unresolved")]:
            d=r.assess(task,{"content":text,"finish_reason":"stop"})
            self.assertEqual(d["unknown_reason"],expected)

    def test_frozen_replay(self):
        report=r.corpus_replay(ROOT/"corpus/responses.jsonl")
        summary=json.loads((ROOT/"corpus/recovery-summary.json").read_text())
        self.assertEqual({k:v for k,v in report.items() if k!="rows"},summary)
        self.assertEqual(report["overall"]["attempted"],3048)
        for group in [report["overall"],*report["by_model"].values(),*report["by_label"].values()]:
            self.assertEqual(sum(group["unknown_breakdown"].values()),group["remaining_unknown"])
            self.assertEqual(group["unknown_truncated"]+group["unknown_nontruncated"]+group["unknown_finish_missing"],group["remaining_unknown"])
        self.assertEqual(report["overall"]["transitions"].get("correct->unknown",0),0)
        self.assertEqual(report["overall"]["transitions"].get("correct->wrong",0),0)
        self.assertEqual(report["overall"]["original_joint_success"],report["overall"]["recovered_joint_success"])

if __name__=="__main__":unittest.main()
