import collections
import json
import statistics
import time
from core_depth import generate,FAMILIES

def audit():
    started=time.monotonic()
    totals=collections.Counter()
    answers=collections.defaultdict(list)
    inactive=collections.Counter()
    controls=collections.Counter()
    prompts=set()
    repeated=0
    for seed in range(100):
        m=generate(seed,2)
        assert len(m["tasks"])==40
        assert len({t["id"] for t in m["tasks"]})==40
        for t in m["tasks"]:
            key=(t["family"],t["level"])
            totals[key]+=1
            answers[key].append(int(t["answer"]))
            checks=t["design_checks"]
            controls[key]+=bool(checks.get("control"))
            inactive[key]+=checks.get("active_constraint") is False
            repeated+=t["prompt"] in prompts
            prompts.add(t["prompt"])
            assert int(t["answer"])>=0
            assert "Return" in t["prompt"]
    return {"tasks":sum(totals.values()),"unique_prompts":len(prompts),"duplicate_prompts":repeated,"seconds":round(time.monotonic()-started,3),"by_family_level":[{"family":f,"level":l,"n":totals[(f,l)],"distinct_answers":len(set(answers[(f,l)])),"zero_answers":answers[(f,l)].count(0),"min":min(answers[(f,l)]),"max":max(answers[(f,l)]),"control_count":controls[(f,l)],"inactive_constraint_count":inactive[(f,l)],"modal_answer_frequency":collections.Counter(answers[(f,l)]).most_common(1)[0][1]/totals[(f,l)]} for f in FAMILIES for l in range(1,5)]}

if __name__=="__main__":
    print(json.dumps(audit(),indent=2))
