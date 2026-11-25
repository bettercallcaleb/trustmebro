import unittest
from trustmebro import generate, digest, correct, score, verify_manifest

class CoreTests(unittest.TestCase):
    def test_manifest(self):
        a=generate(17)
        self.assertEqual(len(a["tasks"]),160)
        self.assertEqual(digest(a),digest(generate(17)))
        self.assertNotEqual(digest(a),digest(generate(41)))
        self.assertEqual(len({x["id"] for x in a["tasks"]}),160)
        verify_manifest(a)
        a["tasks"][0]["prompt"]="tampered"
        with self.assertRaises(ValueError):
            verify_manifest(a)

    def test_json(self):
        t={"family":"json","answer":{"enabled":False,"count":1}}
        self.assertTrue(correct(t,'{"count":1,"enabled":false}'))
        self.assertFalse(correct(t,'{"count":true,"enabled":false}'))
        self.assertFalse(correct(t,'{"count":1,"count":1,"enabled":false}'))

    def test_replay(self):
        import json
        m=generate(17)
        rows=[]
        for t in m["tasks"]:
            content=json.dumps(t["answer"]) if t["family"]=="json" else t["answer"]
            rows.append({"id":t["id"],"budget":128,"elapsed_s":1,"raw":{"choices":[{"message":{"content":content},"finish_reason":"stop"}],"usage":{"completion_tokens":10}}})
        run={"manifest":m,"manifest_sha256":digest(m),"budgets":[128],"rows":rows}
        self.assertEqual(score(run)[0]["accuracy"],1)
        self.assertTrue(score(run)[0]["complete"])
        rows.pop()
        self.assertFalse(score(run)[0]["complete"])
        self.assertEqual(score(run)[0]["failures"],1)
        rows.append(rows[0])
        with self.assertRaises(ValueError):
            score(run)

if __name__=="__main__":
    unittest.main()
