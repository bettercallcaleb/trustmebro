import argparse
import collections
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

VERSION = "failure-corpus-v0.1"
EVALUATOR = {"reference_coverage_gap", "semantic_recognition_gap", "scorer_error"}
OBSERVATIONS = {"foreign_script_candidate", "role_prefix", "think_tag", "tool_tag", "chat_delimiter", "text_repeat", "repetition_heuristic", "multiple_json_objects", "numeric_stream", "interface_returned_cidr", "configuration_in_bit_answer", "json_placeholder", "markdown_fence", "unexpected_reasoning_field", "actual_tool_call_field", "comma_repeat"}
ALIASES = {"format_noncompliant":"contract_violation", "answer_unresolved":"unresolved_decision", "invalid_json_object":"invalid_json", "fabricated_quote":"quote_not_in_source", "json_wrapped":"markdown_wrapper", "think_tag_loop":"repeated_thinking_marker", "outer_whitespace":"extra_outer_whitespace", "answer_type_error":"wrong_answer_type", "extra_or_missing_keys":"json_key_set_mismatch", "wrong_json_root_type":"json_type_mismatch"}
DECLARATION = re.compile(r"(?i)^(?:final(?: answer)?|answer|return)\s*:\s*(.*)$")
FENCE = re.compile(r"\x60{3}(?:[A-Za-z0-9_-]+)?[ \t]*\n(.*?)\n\x60{3}",re.S)
FORMATS = {"hex4":r"[0-9A-Fa-f]+", "octal":r"[0-7]+", "error_code":r"[0-9]+", "bitstring":r"[01]+"}

def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def unwrap(value):
    match = FENCE.fullmatch(value)
    return match.group(1).strip() if match else value

def declared_values(text):
    return [m.group(1).strip() for line in text.splitlines() if (m:=DECLARATION.fullmatch(line.strip()))]

def output_value(text):
    stripped=text.strip()
    if not stripped:return ""
    last=stripped.splitlines()[-1]
    match=DECLARATION.fullmatch(last.strip())
    return unwrap(match.group(1).strip() if match else stripped)

def periodic(value):
    if not re.fullmatch(r"[0-9\s,+-]{32,}",value):return False
    compact=re.sub(r"\s+","",value)
    for n in range(1,min(16,len(compact)//4)+1):
        if compact[-n:]*4==compact[-n*4:]:return True
    vals=re.findall(r"-?[0-9]+",value)
    return any(vals[-n:]*4==vals[-n*4:] for n in range(1,min(8,len(vals)//4)+1))

def decode_json(value):
    def pairs(items):
        obj={}
        for k,v in items:
            if k in obj:raise ValueError("duplicate_json_keys")
            obj[k]=v
        return obj
    def invalid(x):
        raise ValueError("nonfinite_json_number")
    def floating(x):
        v=float(x)
        if not math.isfinite(v):invalid(x)
        return v
    return json.loads(value,object_pairs_hook=pairs,parse_constant=invalid,parse_float=floating)

def json_shape(got,want):
    if type(got) is not type(want):return {"json_type_mismatch"}
    flags=set()
    if isinstance(want,dict):
        if set(got)!=set(want):flags.add("json_key_set_mismatch")
        for k in set(got)&set(want):flags.update(json_shape(got[k],want[k]))
        string_values={v for v in want.values() if type(v) is str}
        if (set(got)-set(want))&string_values:flags.add("value_used_as_key")
    elif isinstance(want,list):
        if len(got)!=len(want):flags.add("json_array_length_mismatch")
        for a,b in zip(got,want):flags.update(json_shape(a,b))
    return flags

def json_candidate(value):
    value=unwrap(value.strip())
    if value.startswith(("{","[","\"")) or value in ("null","true","false") or re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?",value):
        try:return decode_json(value),set()
        except (ValueError,TypeError,OverflowError,RecursionError) as e:
            return None,{"duplicate_json_keys" if str(e)=="duplicate_json_keys" else "invalid_json"}
    return None,set()

def diagnose(task,reply,prior=None):
    prior=prior or {}
    text=reply.get("content")
    if text is None:text=""
    if not isinstance(text,str):raise TypeError("Expected text content")
    finish=reply.get("finish_reason")
    flags={ALIASES.get(f,f) for f in prior.get("flags",[])}
    evaluator=flags&EVALUATOR
    observations=flags&OBSERVATIONS
    flags-=EVALUATOR|OBSERVATIONS
    g=prior.get("score",{})
    if g.get("format_compliant") is False:flags.add("contract_violation")
    if g.get("semantic_correct") is None and "semantic_correct" in g:flags.add("unresolved_decision")
    if g.get("semantic_correct") is False and not flags&{"false_extraction","false_abstention","wrong_value"}:flags.add("wrong_value")
    if not text.strip():flags.add("empty_output")
    if finish=="length":flags.add("length_limit")
    if finish is None:observations.add("finish_reason_missing")
    if finish not in (None,"stop","length"):observations.add("other_finish_reason")
    tokens=reply.get("completion_tokens");budget=task.get("budget")
    if type(tokens) is int and type(budget) is int and tokens>budget:observations.add("reported_tokens_over_cap")
    if re.search(r"</?think>",text,re.I):flags.add("thinking_marker_in_visible_output")
    if len(re.findall(r"</?think>",text,re.I))>=3:flags.add("repeated_thinking_marker")
    if re.search(r"</?tool_(?:call|response)>",text,re.I):flags.add("tool_marker_in_visible_output")
    if re.search(r"<\|(?:im_start|im_end|endoftext|assistant|user|system)\|>",text):flags.add("chat_marker_in_visible_output")
    if re.match(r"(?i)^(?:assistant|user|system)(?:\s*:|\s*\n)",text.strip()):flags.add("leading_role_marker")
    if re.fullmatch(r"(?i)(?:FINAL|ANSWER|RETURN):\s*",text.strip()):flags.add("empty_final_label")
    if reply.get("tool_calls"):observations.add("actual_tool_call_field")
    if reply.get("reasoning_content"):observations.add("unexpected_reasoning_field")
    fmt=task.get("format");gold=task.get("answer")
    value=output_value(text)
    if periodic(value) and value!=gold:flags.add("periodic_numeric_output")
    if fmt=="interface" and re.fullmatch(r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}(?:,\s*(?:[0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2})*\.?",value):flags.add("wrong_output_entity_cidr")
    if fmt in FORMATS and re.fullmatch(FORMATS[fmt],value):
        width=len(gold) if fmt=="bitstring" and isinstance(gold,str) else 4
        if len(value)!=width:flags.add({"hex4":"hex_width","bitstring":"bit_width","octal":"octal_width","error_code":"error_code_width"}[fmt])
    if fmt=="bitstring" and re.fullmatch(r"[01](?:[\s,]+[01])+",value):flags.add("bit_delimiter")
    if fmt in ("csv","csv_none") and re.fullmatch(r"[0-9]+(?:,\s*[0-9]+)*",value):
        if ", " in value:flags.add("csv_space")
        if isinstance(gold,str) and gold!="NONE" and len(value.split(","))!=len(gold.split(",")):flags.add("csv_length_mismatch")
        if re.search(r"(?<![0-9])([0-9]+)(?:,\s*\1){3,}(?![0-9])",value) and isinstance(gold,str) and not re.search(r"(?<![0-9])([0-9]+)(?:,\s*\1){3,}(?![0-9])",gold):flags.add("repeated_csv_value")
    if task.get("kind")=="protocol" and isinstance(gold,str):
        if "\t" in gold and "\t" not in text and "," in text:flags.add("tab_to_comma_substitution")
        if text!=gold and text.strip()==gold:flags.add("extra_outer_whitespace")
        if text!=gold and text.casefold()==gold.casefold():flags.add("case_only_mismatch")
        if text!=gold and unicodedata.normalize("NFC",text)==unicodedata.normalize("NFC",gold):flags.add("unicode_normalization_difference")
        if re.fullmatch(r"0[0-9]+",gold) and re.fullmatch(r"[0-9]+",text.strip()) and len(text.strip())<len(gold) and (text.strip().lstrip("0") or "0")== (gold.lstrip("0") or "0"):flags.add("leading_zero_loss")
    if fmt=="json" or task.get("contract")=="json" or task.get("kind")=="extraction":
        if re.search(r"(?m)^\$\$|\\[{}]",text) and ("{" in text or "[" in text):observations.add("math_wrapped_json_candidate")
        candidates=[value]
        if text.lstrip().startswith(("{","[")) and value!=text.strip():candidates.append(text.strip())
        for z in candidates:
            got,errors=json_candidate(z)
            flags.update(errors)
            if not errors and (got is not None or z.strip()=="null") and fmt=="json" and isinstance(gold,(dict,list)):flags.update(json_shape(got,gold))
    declarations=declared_values(text)
    if len(declarations)>=2:
        complete=declarations[:-1] if finish=="length" and declarations[-1] and any(v.startswith(declarations[-1]) and v!=declarations[-1] for v in declarations[:-1]) else declarations
        tail_partial=len(complete)<len(declarations)
        if len(complete)>=2 and len(set(complete))==1 and complete[0]:
            flags.add("repeated_answer_declaration")
            flags.discard("conflicting_declarations")
            if tail_partial:flags.add("truncated_declaration_prefix")
        elif len(set(complete))>1:
            observations.add("distinct_declaration_text")
    if "repeated_answer_declaration" in flags and g.get("semantic_correct") is None:observations.add("semantic_review_required")
    return {"labels":sorted(flags),"observations":sorted(observations),"evaluator_flags":sorted(evaluator),"response_sha256":digest(text),"score_unchanged":g}

def summarize(records):
    counts=collections.Counter();obs=collections.Counter();evals=collections.Counter();models=collections.Counter();unique=set();anomalous=set();attempts=0;seen=set();anomalous_attempts=0
    for r in records:
        if r["id"] in seen:raise ValueError("Duplicate record ID")
        seen.add(r["id"]);attempts+=1;models[r["model"]]+=1
        d=diagnose(r["task"],r["reply"],r.get("prior"))
        unique.add(d["response_sha256"]);counts.update(d["labels"]);obs.update(d["observations"]);evals.update(d["evaluator_flags"])
        if d["labels"]:anomalous.add(d["response_sha256"]);anomalous_attempts+=1
    return {"version":VERSION,"attempted":attempts,"by_model":dict(sorted(models.items())),"unique_response_texts":len(unique),"anomalous_attempts":anomalous_attempts,"unique_anomalous_texts":len(anomalous),"label_counts":dict(sorted(counts.items())),"observation_counts":dict(sorted(obs.items())),"evaluator_flags":dict(sorted(evals.items()))}

def records(path):
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():yield json.loads(line)

def diagnose_run(run):
    import sys
    import measurement
    measurement.score(run)
    sys.path.insert(0,str(Path(__file__).resolve().parent/"draft"))
    import response_taxonomy
    tasks={t["id"]:t for t in run["manifest"]["tasks"]}
    output=[]
    for r in run["rows"]:
        t={**tasks[r["id"]],"kind":"reasoning","mode":r["mode"],"budget":r["budget"]}
        entry={"id":r["id"],"mode":r["mode"],"budget":r["budget"]}
        if "error" in r:
            output.append({**entry,"transport_error":True})
            continue
        ch=r["raw"]["choices"][0]
        reply={**ch["message"],"finish_reason":ch.get("finish_reason"),"completion_tokens":(r["raw"].get("usage") or {}).get("completion_tokens")}
        legacy=measurement.grade(t,reply.get("content"),r["mode"],reply["finish_reason"])
        provisional=response_taxonomy.reasoning_grade(t,reply.get("content"),r["mode"],reply["finish_reason"],reply["completion_tokens"],r["budget"])
        prior={"score":{k:legacy[k] for k in ("semantic_correct","format_compliant","joint_success")},"flags":provisional["flags"]}
        output.append({**entry,**diagnose(t,reply,prior),"experimental_semantic_correct":provisional["semantic_correct"]})
    planned=len(tasks)*len(run["modes"])*len(run["budgets"])
    return {"version":VERSION,"planned":planned,"attempted":len(output),"not_run":planned-len(output),"rows":output}

def main():
    p=argparse.ArgumentParser(description="Offline response diagnostics; does not alter benchmark scores.")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("summarize");a.add_argument("corpus");a.add_argument("--out")
    a=sub.add_parser("inspect");a.add_argument("record")
    a=sub.add_parser("diagnose-run");a.add_argument("run");a.add_argument("--out")
    args=p.parse_args()
    if args.cmd=="summarize":
        result=summarize(records(args.corpus))
    elif args.cmd=="diagnose-run":
        result=diagnose_run(json.loads(Path(args.run).read_text(encoding="utf-8")))
    else:
        r=json.loads(Path(args.record).read_text(encoding="utf-8"))
        result=diagnose(r["task"],r["reply"],r.get("prior"))
    s=json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n"
    if getattr(args,"out",None):Path(args.out).write_text(s,encoding="utf-8")
    else:print(s,end="")

if __name__=="__main__":main()
