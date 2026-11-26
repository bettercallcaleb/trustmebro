import argparse
import collections
import json
import re
from pathlib import Path

import extraction
import reliability
from trustmebro import digest, file_hash, no_duplicates, save

VERSION="response-taxonomy-draft-v0.1"
GROUPS={
    "decision":("false_extraction","false_abstention","wrong_value","unresolved_decision"),
    "format":("contract_violation","code_fence","markdown_emphasis","inline_code","noncanonical_abstention","json_abstention","abstention_case","markdown_wrapper","invalid_json","duplicate_json_keys","missing_keys","extra_keys","wrong_answer_type","wrong_quote_type","noncanonical_number","bare_numeric_answer","noncanonical_label","extra_text","representation_deviation","multiple_declarations","malformed_declaration","nonterminal_declaration"),
    "evidence":("missing_quote","fabricated_quote","irrelevant_quote","quote_answer_mismatch","conflicting_declarations"),
    "generation":("length_limit","empty_output","repetition_heuristic","finish_reason_missing","other_finish_reason","reported_tokens_over_cap"),
    "evaluator":("reference_coverage_gap","semantic_recognition_gap"),
}
KNOWN={k:g for g,keys in GROUPS.items() for k in keys}

def json_object(s):
    try:
        obj=json.loads(s,object_pairs_hook=no_duplicates,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
        return obj if type(obj) is dict else None,None
    except (ValueError,TypeError,OverflowError,RecursionError) as exc:
        if "Duplicate" in str(exc):return None,"duplicate_json_keys"
        return None,"invalid_json"

def result(flags,semantic,format_ok,joint,legacy,decision,evidence_state=None):
    flags=sorted(set(flags))
    unknown=set(flags)-set(KNOWN)
    if unknown:raise ValueError("Unknown flags: "+str(unknown))
    return {"decision":decision,"semantic_correct":semantic,"format_compliant":format_ok,"joint_success":joint,"evidence_state":evidence_state,"flags":flags,"groups":sorted({KNOWN[x] for x in flags}),"legacy":{"semantic_correct":legacy["semantic_correct"],"format_compliant":legacy["format_compliant"],"joint_success":legacy["joint_success"]}}

def generation_flags(content,finish_reason,tokens,budget):
    s=content.strip() if isinstance(content,str) else ""
    flags=[]
    if not s:flags.append("empty_output")
    if finish_reason=="length":flags.append("length_limit")
    elif finish_reason is None:flags.append("finish_reason_missing")
    elif finish_reason!="stop":flags.append("other_finish_reason")
    if reliability.base.repetition_diagnostic(s) or reliability.repeated_line(s):flags.append("repetition_heuristic")
    if type(tokens) is int and type(budget) is int and tokens>budget:flags.append("reported_tokens_over_cap")
    return flags

def extraction_grade(task,content,finish_reason,tokens=None,budget=None):
    legacy=extraction.grade(task,content,finish_reason)
    s=content.strip() if isinstance(content,str) else ""
    body=reliability.base.strip_wrapper(s)
    body,styles=reliability.unwrap_inline(body)
    flags=generation_flags(s,finish_reason,tokens,budget)
    if body!=s:
        flags.append("markdown_wrapper")
        if s.startswith(chr(96)*3):flags.append("code_fence")
        elif s.startswith(chr(96)):flags.append("inline_code")
        if "markdown_emphasis" in styles or s.startswith(("**","__","*","_")):flags.append("markdown_emphasis")
    obj,error=json_object(body)
    decision=legacy["decision"]
    candidate=legacy["candidate"]
    quote=legacy["quote"]
    relevant=legacy["quote_relevant"]
    if isinstance(obj,dict):
        keys=set(obj)
        quote=obj.get("quote")
        relevant=isinstance(quote,str) and quote in task["evidence"] and quote in task["response"]
        if {"answer","quote"}-keys:flags.append("missing_keys")
        if keys-{"answer","quote"}:flags.append("extra_keys")
        answer=obj.get("answer")
        if "answer" in obj and type(answer) is not str:flags.append("wrong_answer_type")
        if "quote" in obj and type(obj["quote"]) is not str:flags.append("wrong_quote_type")
        if type(answer) is str and answer.strip().upper()=="UNKNOWN":
            flags.append("json_abstention")
            if answer!="UNKNOWN":flags.append("abstention_case")
            # Only a structured, explicit abstention without competing fields is recovered.
            if keys<={"answer","quote"}:
                decision="abstain"
                candidate=None
        elif extraction.normalized(answer) is not None:
            candidate=extraction.normalized(answer)
            decision="extract"
            if type(answer) is str and answer!=candidate:flags.append("noncanonical_number")
    elif body.upper()=="UNKNOWN":
        decision="abstain"
        if body!="UNKNOWN":flags.append("abstention_case")
    elif body and body[0] in "{[":
        if error:flags.append(error)
        else:flags.append("invalid_json")
    elif extraction.normalized(body) is not None:
        decision="extract";candidate=extraction.normalized(body)
        flags.append("bare_numeric_answer")
        if body!=candidate:flags.append("noncanonical_number")
    if decision=="abstain" and s!="UNKNOWN":flags.append("noncanonical_abstention")
    expected="extract" if task["polarity"]=="answerable" else "abstain"
    semantic=None if decision=="unresolved" else (decision=="abstain" if expected=="abstain" else decision=="extract" and candidate==task["answer"])
    if decision=="unresolved":flags.append("unresolved_decision")
    elif decision=="abstain" and expected=="extract":flags.append("false_abstention")
    elif decision=="extract" and expected=="abstain":flags.append("false_extraction")
    elif decision=="extract" and semantic is False:flags.append("wrong_value")
    if legacy["semantic_correct"] is None and semantic is not None:flags.append("semantic_recognition_gap")
    evidence_state="not_required" if decision=="abstain" else "unresolved"
    if decision=="extract":
        if not isinstance(quote,str) or not quote:
            flags.append("missing_quote");evidence_state="missing"
        elif quote not in task["response"]:
            flags.append("fabricated_quote");evidence_state="not_in_source"
        else:
            # The original prompt permits a full decisive sentence OR line. Recover only
            # a complete original line containing a designated decisive statement.
            line_match=quote in task["response"].splitlines()
            if not relevant and line_match and any(q in quote for q in task["evidence"]):
                relevant=True;flags.append("reference_coverage_gap")
            if not relevant:flags.append("irrelevant_quote");evidence_state="irrelevant"
            elif candidate!=task["answer"]:flags.append("quote_answer_mismatch");evidence_state="answer_mismatch"
            else:evidence_state="supports_answer"
    if not legacy["format_compliant"]:flags.append("contract_violation")
    joint=semantic is True and legacy["format_compliant"] and (decision=="abstain" or evidence_state=="supports_answer")
    return result(flags,semantic,legacy["format_compliant"],joint,legacy,decision,evidence_state)

def reasoning_grade(task,content,mode,finish_reason,tokens=None,budget=None):
    g=reliability.grade(task,content,mode,finish_reason)
    f=g["flags"]
    flags=generation_flags(content,finish_reason,tokens,budget)
    mapping={"wrong_value":"wrong_value","answer_unresolved":"unresolved_decision","markdown_emphasis":"markdown_wrapper","code_fence":"markdown_wrapper","inline_code":"markdown_wrapper","missing_canonical_final_marker":"noncanonical_label","strict_extra_text":"extra_text","representation_deviation":"representation_deviation","multiple_declarations":"multiple_declarations","conflicting_declarations":"conflicting_declarations","malformed_declaration":"malformed_declaration","nonterminal_declaration":"nonterminal_declaration"}
    flags.extend(v for k,v in mapping.items() if f[k])
    flags.extend(k for k in ("markdown_emphasis","code_fence","inline_code") if f[k])
    if not g["format_compliant"]:flags.append("contract_violation")
    return result(flags,g["semantic_correct"],g["format_compliant"],g["joint_success"],g,"unresolved" if g["semantic_correct"] is None else "answer")

def summarize(rows,expected):
    if len(rows)>expected:raise ValueError("Unexpected count")
    flags=collections.Counter()
    groups=collections.Counter()
    buckets=collections.Counter()
    transitions=collections.Counter()
    cost=collections.defaultdict(lambda:{"attempts":0,"tokens":0,"time_s":0.0,"missing_tokens":0,"missing_time":0})
    def add_cost(key,row):
        x=cost[key];x["attempts"]+=1
        if type(row.get("tokens")) is int:x["tokens"]+=row["tokens"]
        else:x["missing_tokens"]+=1
        if type(row.get("elapsed_s")) in (int,float):x["time_s"]+=row["elapsed_s"]
        else:x["missing_time"]+=1
    for row in rows:
        g=row.get("diagnostic")
        if g is None:
            buckets["transport_error"]+=1
            add_cost("transport_error",row)
            continue
        semantic="correct" if g["semantic_correct"] is True else "wrong" if g["semantic_correct"] is False else "unresolved"
        buckets[semantic+("/compliant" if g["format_compliant"] else "/noncompliant")]+=1
        flags.update(g["flags"]);groups.update(g["groups"])
        for flag in g["flags"]:add_cost(flag,row)
        if not g["joint_success"]:add_cost("joint_failure",row)
        if g["legacy"]["semantic_correct"]!=g["semantic_correct"]:transitions["semantic_changed"]+=1
        if g["legacy"]["joint_success"]!=g["joint_success"]:transitions["joint_changed"]+=1
        if g["legacy"]["format_compliant"]!=g["format_compliant"]:raise AssertionError("Contract changed")
    buckets["not_run"]=expected-len(rows)
    for x in cost.values():
        if x.pop("missing_tokens"):x["tokens"]=None
        if x.pop("missing_time"):x["time_s"]=None
    return {"n":expected,"attempted":len(rows),"semantic_correct":sum(v for k,v in buckets.items() if k.startswith("correct/")),"joint_success":sum(bool(r.get("diagnostic",{}).get("joint_success")) for r in rows),"format_compliant":sum(v for k,v in buckets.items() if k.endswith("/compliant")),"buckets":dict(sorted(buckets.items())),"flag_counts":dict(sorted(flags.items())),"group_counts":dict(sorted(groups.items())),"score_changes":dict(transitions),"cost_by_flag":dict(cost)}

def replay(run,kind,manifest=None):
    m=run["manifest"] if manifest is None else manifest
    if digest(m)!=run["manifest_sha256"]:raise ValueError("Manifest hash mismatch")
    if kind=="extraction":extraction.verify(m)
    tasks={t["id"]:t for t in m["tasks"]}
    rows=[];seen=set()
    for row in run["rows"]:
        ident=row["id"]
        if ident in seen or ident not in tasks:raise ValueError("Unexpected response")
        seen.add(ident)
        t=tasks[ident]
        r={"id":ident,"family":t["family"],"polarity":t.get("polarity"),"elapsed_s":row.get("elapsed_s"),"tokens":None}
        if "error" not in row:
            c=row["raw"]["choices"][0]
            r["tokens"]=(row["raw"].get("usage") or {}).get("completion_tokens")
            args=(t,c["message"].get("content"),c.get("finish_reason"),r["tokens"],run["budget"])
            r["diagnostic"]=extraction_grade(*args) if kind=="extraction" else reasoning_grade(t,args[1],run["mode"],*args[2:])
        rows.append(r)
    subsets={}
    for key in ("family","polarity"):
        subsets["by_"+key]={v:summarize([r for r in rows if r[key]==v],sum(t.get(key)==v for t in tasks.values())) for v in sorted({t[key] for t in tasks.values() if t.get(key) is not None})}
    return {"overall":summarize(rows,len(tasks)),**subsets,"rows":rows}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--extraction-dir",required=True);p.add_argument("--reasoning-dir",required=True);p.add_argument("--out",required=True)
    a=p.parse_args()
    report={"version":VERSION,"groups":GROUPS,"extraction":{},"reasoning":{}}
    for f in sorted(Path(a.extraction_dir).glob("qwen*.json")):
        if f.name.endswith("-report.json"):continue
        run=json.loads(f.read_text())
        report["extraction"][f.stem]={"raw_sha256":file_hash(f)["sha256"],**replay(run,"extraction")}
    src=Path(a.reasoning_dir);m=json.loads((src/"plan.json").read_text())["manifest"]
    for f in sorted(src.glob("*-raw.json")):
        run=json.loads(f.read_text())
        report["reasoning"][run["model"]]={"raw_sha256":file_hash(f)["sha256"],**replay(run,"reasoning",m)}
    save(a.out,report)
if __name__=="__main__":main()
