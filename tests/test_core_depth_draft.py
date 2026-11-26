import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"draft"))
import core_depth as c

class DraftTests(unittest.TestCase):
    def test_panel(self):
        a=c.generate(17,2);b=c.generate(211,2)
        self.assertEqual(a,c.generate(17,2))
        self.assertEqual(c.validate_panel([a,b]),80)
        with self.assertRaises(ValueError):c.validate_panel([a,a])
        self.assertEqual(len({t["id"] for t in a["tasks"]}),40)
    def test_route(self):
        edges={("A","F"):(1,0),("A","C"):(2,2),("C","F"):(2,2),("C","E"):(3,0),("E","F"):(4,1)}
        for level,want in enumerate([1,4,4,9],1):
            self.assertEqual(c.route_ref(edges,level),want)
            self.assertEqual(c.route_dp(edges,level),want)
    def test_jobs(self):
        jobs=[["A",0,2,5,4,"-"],["B",2,4,8,5,"A"],["C",0,4,15,2,"-"]]
        for level,want in enumerate([15,13,8,0],1):
            self.assertEqual(c.schedule_ref(jobs,level,"B"),want)
            self.assertEqual(c.schedule_dp(jobs,level,"B"),want)
    def test_rollback(self):
        start={"A":10,"B":0}
        events=[[["hold","A",3]],[["transfer","A",5,"B"],["spend","A",9]],[["release","A",1]]]
        self.assertEqual(c.ledger_int(start,events),(8,1))
        self.assertEqual(c.ledger_units(start,events),(8,1))
    def test_relational(self):
        u=[("A","X","active"),("B","X","blocked"),("C","Y","active"),("D","Y","active")]
        e=[("A",1,20,"paid"),("A",2,20,"void"),("B",1,10,"paid"),("C",1,30,"paid"),("C",2,10,"paid"),("D",1,9,"paid")]
        for level,want in enumerate([79,69,19,19],1):
            self.assertEqual(c.relational_py(u,e,level),want)
            self.assertEqual(c.relational_sql(u,e,level),want)
    def test_logic(self):
        cs=[("before","A","B"),("adjacent","B","C")]
        self.assertEqual(c.logic_ref("ABC",cs),2)
        self.assertEqual(c.logic_dfs("ABC",cs),2)
        cs.append(("either_before","A",("B","C")))
        self.assertEqual(c.logic_ref("ABC",cs),0)
        self.assertEqual(c.logic_dfs("ABC",cs),0)
if __name__=="__main__":unittest.main()
