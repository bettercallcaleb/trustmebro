import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

from reliability import safe_value,extract
from trustmebro import canonical,digest,save
from measurement import parse_json

VERSION="delivery-controls-draft-v0.1"
CONTRACTS={
    "bare":"Return only the canonical decimal integer. No label, explanation, Markdown, units, or leading zeros.",
    "label":"Return exactly one line: FINAL: followed by one space and the canonical decimal integer. No other text or Markdown.",
    "json":"Return only a JSON object with exactly two keys: answer (integer result) and tag (string, exactly the supplied tag). Key order and JSON whitespace do not matter. No Markdown or extra keys.",
}
CONDITIONS=("solve","supplied")

def generate(manifest):
    if manifest["version"]!="core-depth-draft-v0.1":raise ValueError("Unexpected source manifest")
    sources=[t for t in manifest["tasks"] if (t["root"].endswith("/v000") and t["level"]==2) or (t["root"].endswith("/v001") and t["level"]==4)]
    if len(sources)!=10:raise ValueError("Expected two roots per family")
    tasks=[]
    for source in sources:
        tag="T-"+hashlib.sha256((str(manifest["seed"])+":"+source["id"]).encode()).hexdigest()[:8].upper()
        body=source["prompt"]
        body,n=re.subn(r" Return [^.]+\.\s*$","",body)
        if n!=1:raise ValueError("Source task must end in an answer contract")
        for condition in CONDITIONS:
            for contract,instruction in CONTRACTS.items():
                supplied="" if condition=="solve" else f"\nThe verified result is {source['answer']}. Use this supplied result; do not solve again."
                tag_text=f"\nSupplied tag: {tag}." if contract=="json" else ""
                tasks.append({"id":f"delivery/{source['id']}/{condition}/{contract}","source_id":source["id"],"family":source["family"],"level":source["level"],"condition":condition,"contract":contract,"prompt":body+supplied+tag_text+"\n"+instruction,"answer":source["answer"],"tag":tag if contract=="json" else None})
    return {"version":VERSION,"source_digest":digest(manifest),"tasks":tasks}

def grade(task,content):
    s=content.strip() if isinstance(content,str) else ""
    scalar={"format":"integer","answer":task["answer"]}
    contract=task["contract"]
    v=None;compliant=False
    flags={}
    if contract=="json":
        from reliability import base
        body=base.strip_wrapper(s)
        obj=parse_json(body)
        if isinstance(obj,dict):
            val=obj.get("answer")
            if type(val) is int:v=str(val)
            elif isinstance(val,str):v=safe_value(val,scalar)
            flags={"extra_or_missing_keys":set(obj)!={"answer","tag"},"answer_type_error":type(val) is not int,"tag_error":obj.get("tag")!=task["tag"],"json_wrapped":body!=s}
            compliant=body==s and not any(flags.values())
        else:flags={"invalid_json_object":True}
    elif contract in ("bare","label"):
        ext=extract(s,scalar)
        v=ext["prediction"]
        pattern=r"-?(?:0|[1-9][0-9]{0,14})"
        compliant=bool(re.fullmatch(pattern if contract=="bare" else "FINAL: "+pattern,s))
        flags={"conflicting_declarations":ext["status"]=="conflicting_declarations","markdown_wrapper":bool(set(ext["styles"])&{"markdown_emphasis","inline_code","code_fence"})}
    else:raise ValueError("Unknown contract")
    correct=None if v is None else v==task["answer"]
    flags.update(format_noncompliant=not compliant,wrong_value=correct is False,answer_unresolved=correct is None,empty=not s)
    return {"semantic_correct":correct,"format_compliant":compliant,"joint_success":correct is True and compliant,"flags":flags}

def paired_report(manifest,rows):
    tasks={t["id"]:t for t in manifest["tasks"]}
    seen={}
    for row in rows:
        ident=row["id"]
        if ident not in tasks or ident in seen:raise ValueError("Unexpected or duplicate row")
        seen[ident]=grade(tasks[ident],row["content"])
    out={}
    for contract in CONTRACTS:
        cells={}
        transition=collections.Counter()
        for condition in CONDITIONS:
            subset=[t for t in tasks.values() if t["contract"]==contract and t["condition"]==condition]
            grades=[seen[t["id"]] for t in subset if t["id"] in seen]
            correct=sum(g["semantic_correct"] is True for g in grades)
            wrong=sum(g["semantic_correct"] is False for g in grades)
            cells[condition]={"n":len(subset),"attempted":len(grades),"confirmed_correct":correct,"confirmed_wrong":wrong,"unknown":len(subset)-correct-wrong,"joint_success":sum(g["joint_success"] for g in grades),"format_compliant":sum(g["format_compliant"] for g in grades)}
        roots={t["source_id"] for t in tasks.values()}
        for root in roots:
            a=seen.get(f"delivery/{root}/solve/{contract}")
            b=seen.get(f"delivery/{root}/supplied/{contract}")
            if a is None or b is None:transition["unpaired"]+=1
            else:
                key=("pass" if a["joint_success"] else "fail")+"->"+("pass" if b["joint_success"] else "fail")
                transition[key]+=1
        out[contract]={"conditions":cells,"paired_joint_transitions":dict(transition)}
    return out

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    save(a.out,generate(json.loads(Path(a.source).read_text())))
