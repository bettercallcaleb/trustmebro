import collections
import json
import re
import statistics
import extraction as e

def audit():
    all_tasks=[]
    for seed in range(100):
        m=e.generate(seed,2)
        e.verify(m)
        all_tasks.extend(m["tasks"])
    counts=collections.Counter()
    heuristics=collections.Counter()
    source_texts=set()
    for t in all_tasks:
        positive=t["polarity"]=="answerable"
        source_texts.add(t["response"])
        good="UNKNOWN" if not positive else json.dumps({"answer":t["answer"],"quote":t["evidence"][0]})
        assert e.grade(t,good)["joint_success"]
        counts[t["polarity"]]+=1
        if positive:
            assert all(q in t["response"] for q in t["evidence"])
            assert not e.grade(t,json.dumps({"answer":t["answer"],"quote":t["answer"]}))["joint_success"]
            assert not e.grade(t,json.dumps({"answer":int(t["answer"]),"quote":t["evidence"][0]}))["joint_success"]
        else:
            assert not t["evidence"]
        numbers=re.findall(r"(?<!\w)-?\d+(?!\w)",t["response"])
        a=numbers[-1] if numbers else None
        guess=next(iter(re.findall(r"(?im)^FINAL: (-?\d+)$",t["response"])[-1:]),None)
        heuristics["always_abstain_semantic_correct"]+=not positive
        heuristics["last_number_semantic_correct"]+=positive and a==t["answer"]
        heuristics["bare_final_or_abstain_semantic_correct"]+=(positive and guess==t["answer"]) or (not positive and guess is None)
    n=len(all_tasks)
    return {"version":e.VERSION,"seeds":100,"variants_per_seed":2,"tasks":n,"by_polarity":dict(counts),"unique_source_texts":len(source_texts),"duplicate_source_texts":n-len(source_texts),"oracle_fixture_passes":n,"prompt_character_median":statistics.median(len(e.prompt_for(t)) for t in all_tasks),"heuristic_semantic_baselines":{k:v/n for k,v in heuristics.items()},"note":"CPU fixture and structural checks only; semantic labels derive from authored templates, not a second independently annotated corpus. Heuristics do not earn evidence or strict-format credit."}

if __name__=="__main__":print(json.dumps(audit(),indent=2))
