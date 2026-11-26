import collections
import json
import math
import re
from conceptladder.cli import load_suite
from conceptladder.exact import normalize_exact

VERSION="trustmebro-v0.2"
TRACKS=("core","ladder")
MODES=("strict","relaxed")
STRICT="Return only the requested value, without a label or explanation."
RELAXED="You may explain your reasoning. End with a single separate line FINAL: followed by the requested answer representation. This overrides answer-only instructions, not the required representation."
LABEL=re.compile(r"(?im)^[ \t]*(?:FINAL|ANSWER)[ \t]*:")
CODE=re.compile(r"\A"+re.escape(chr(96)*3)+r"(?:[A-Za-z0-9_-]+)?[ \t]*\n(.*?)\n"+re.escape(chr(96)*3)+r"\Z",re.S)

def generate(seed,variants,suite,ladder_variants):
    from trustmebro import generate as core_generate
    if suite not in ("core","ladder","all") or variants<1 or ladder_variants<1:
        raise ValueError("Invalid suite or variant count")
    tasks=[]
    if suite in ("core","all"):
        for t in core_generate(seed,variants)["tasks"]:
            family=t["family"]
            fmt={"arithmetic":"integer","schedule":"integer","modular":"integer","path":"integer","copy":"identifier","json":"json","order":"csv","filter":"csv_none"}[family]
            tasks.append({**t,"id":"core/"+t["id"],"track":"core","format":fmt,"domain":"reasoning" if family in ("arithmetic","schedule","modular","path") else "instruction"})
    if suite in ("ladder","all"):
        for t in load_suite("exact","all",seed,ladder_variants):
            tasks.append({"id":"ladder/"+t["id"],"track":"ladder","family":t["concept"].rsplit("-v",1)[0],"domain":t["pack"],"root":t["pack"]+"/"+t["concept"],"level":t["level"],"prompt":t["prompt"],"answer":t["correct"],"format":t["answer_format"],"source":t.get("source")})
    return {"version":VERSION,"seed":seed,"variants":variants,"ladder_variants":ladder_variants,"suite":suite,"tasks":tasks}

def protocol():
    return {"version":VERSION,"prompts":{"strict":STRICT,"relaxed":RELAXED},"temperature":0,"budget_kind":"output_token_ceiling","semantic_denominator":"all_planned_tasks","success":"confirmed_correct_and_format_compliant"}

def prompt_for(t,mode):
    return t["prompt"]+"\n"+protocol()["prompts"][mode]

def verify(m):
    if m!=generate(m["seed"],m["variants"],m["suite"],m["ladder_variants"]):
        raise ValueError("Manifest mismatch")

def strip_wrapper(s):
    s=s.strip()
    m=CODE.fullmatch(s)
    if m:s=m.group(1).strip()
    tick=chr(96)
    if len(s)>2 and s.startswith(tick) and s.endswith(tick) and tick not in s[1:-1]:s=s[1:-1].strip()
    return s

def parse_json(s):
    from trustmebro import no_duplicates
    def invalid(v):raise ValueError(v)
    try:return json.loads(s,object_pairs_hook=no_duplicates,parse_constant=invalid)
    except (TypeError,ValueError):return None

def value(s,t):
    fmt=t["format"]
    if fmt=="json":
        v=parse_json(s)
        return v if isinstance(v,dict) else None
    if fmt=="identifier":
        return s if re.fullmatch(r"ID-[A-Z0-9]+-[0-9]+",s,re.I) else None
    if fmt in ("csv","csv_none"):
        if fmt=="csv_none" and s.upper()=="NONE":return "NONE"
        if re.fullmatch(r"[+-]?[0-9]+(?:\s*,\s*[+-]?[0-9]+)*",s):
            return ",".join(str(int(v)) for v in s.split(","))
        return None
    return normalize_exact(s,fmt)

def format_ok(s,t):
    fmt=t["format"]
    gold=t["answer"]
    if fmt=="json":
        v=parse_json(s)
        return isinstance(v,dict) and set(v)=={"id","count","enabled"} and type(v["id"]) is str and type(v["count"]) is int and type(v["enabled"]) is bool
    patterns={"integer":r"-?(?:0|[1-9][0-9]{0,14})","identifier":r"ID-[A-Z0-9]{9}-[0-9]+","csv":r"[0-9]+(?:,[0-9]+)*","csv_none":r"(?:NONE|[0-9]+(?:,[0-9]+)*)","bitstring":rf"[01]{{{len(str(gold))}}}","interface":r"if[0-9]{2}","text2":r"[a-z]{2}","hex4":r"[0-9A-F]{4}","octal":r"0[0-7]{3}","error_code":r"[0-9]{4}"}
    return re.fullmatch(patterns[fmt],s) is not None

def semantic_value(s,t):
    s=strip_wrapper(s)
    labels=list(LABEL.finditer(s))
    if labels:
        if len(labels)!=1:return None
        tail=s[labels[0].end():].strip()
        return value(strip_wrapper(tail),t)
    direct=value(s,t)
    if direct is not None:return direct
    m=re.fullmatch(r"(?is)(?:the\s+(?:final\s+)?answer\s+is|answer\s+is)\s+(.+?)\.?",s)
    if m:return value(strip_wrapper(m.group(1)),t)
    return None

def repetition_diagnostic(s):
    if len(s)<120:return False
    words=re.findall(r"\S+",s)
    for size in range(4,min(65,len(words)//4+1)):
        for j in range(len(words)-size*4+1):
            block=words[j:j+size]
            if block*4==words[j:j+size*4] and len(" ".join(block))>=24:
                return True
    return False

def grade(t,content,mode,finish_reason):
    from trustmebro import canonical
    s=content.strip() if isinstance(content,str) else ""
    gold=t["answer"]
    if t["format"]!="json":gold=value(str(gold),t)
    pred=semantic_value(s,t)
    correct=None if pred is None else canonical(pred)==canonical(gold)
    if mode=="strict":
        compliance=format_ok(s,t)
    else:
        lines=s.splitlines()
        labels=list(LABEL.finditer(s))
        compliance=bool(len(labels)==1 and lines and lines[-1].startswith("FINAL: ") and format_ok(lines[-1][7:],t))
    return {"semantic_correct":correct,"format_compliant":compliance,"joint_success":correct is True and compliance,"truncated":None if finish_reason is None else finish_reason=="length","empty":not s,"repetition_flag":repetition_diagnostic(s)}

def report(rows,expected):
    if expected<1 or len(rows)>expected:raise ValueError("Invalid denominator")
    counts=collections.Counter()
    matrix={f"{state}_{fmt}":0 for state in ("correct","wrong","unknown") for fmt in ("compliant","noncompliant")}
    tokens=[];times=[]
    for r in rows:
        if "error" in r:
            counts["transport_error"]+=1
            times.append(r.get("elapsed_s"))
            tokens.append(None)
            continue
        g=r["grade"]
        state="correct" if g["semantic_correct"] is True else "wrong" if g["semantic_correct"] is False else "unknown"
        counts[state if state!="unknown" else "unknown_answer"]+=1
        matrix[state+"_"+("compliant" if g["format_compliant"] else "noncompliant")]+=1
        for key in ("format_compliant","joint_success","empty","repetition_flag"):
            counts[key]+=int(g[key])
        counts["finish_known"]+=int(g["truncated"] is not None)
        counts["truncated"]+=int(g["truncated"] is True)
        times.append(r.get("elapsed_s"))
        tokens.append((r["raw"].get("usage") or {}).get("completion_tokens"))
    not_run=expected-len(rows)
    unknown=expected-counts["correct"]-counts["wrong"]
    joint=counts["joint_success"]
    total_tokens=sum(tokens) if not_run==0 and all(type(v) is int and v>=0 for v in tokens) else None
    total_time=sum(times) if not_run==0 and all(type(v) in (int,float) and math.isfinite(v) and v>=0 for v in times) else None
    return {"n":expected,"attempted":len(rows),"complete":not_run==0 and counts["transport_error"]==0,"confirmed_correct":counts["correct"],"confirmed_wrong":counts["wrong"],"unknown":unknown,"unknown_answer":counts["unknown_answer"],"error_matrix":matrix,"transport_error":counts["transport_error"],"not_run":not_run,"confirmed_correct_rate":counts["correct"]/expected,"confirmed_wrong_rate":counts["wrong"]/expected,"unknown_rate":unknown/expected,"answer_coverage":(expected-unknown)/expected,"accuracy_upper_bound":(counts["correct"]+unknown)/expected,"format_compliance":counts["format_compliant"]/expected,"joint_success":joint,"strict_accuracy":joint/expected,"truncation_rate":counts["truncated"]/expected,"finish_reason_coverage":counts["finish_known"]/expected,"truncation_upper_bound":(counts["truncated"]+expected-counts["finish_known"])/expected,"empty_rate":counts["empty"]/expected,"repetition_flag_rate":counts["repetition_flag"]/expected,"total_completion_tokens":total_tokens,"total_elapsed_s":total_time,"token_count_coverage":sum(type(t) is int and t>=0 for t in tokens)/expected,"tokens_per_success":total_tokens/joint if joint and total_tokens is not None else None,"time_per_success_s":total_time/joint if joint and total_time is not None else None}

def score(run):
    from trustmebro import digest
    m=run["manifest"];verify(m)
    if digest(m)!=run["manifest_sha256"]:raise ValueError("Manifest digest mismatch")
    if run.get("protocol")!=protocol():raise ValueError("Protocol mismatch")
    budgets=run["budgets"];modes=run["modes"]
    if not budgets or len(set(budgets))!=len(budgets) or any(type(b) is not int or b<1 for b in budgets):raise ValueError("Invalid budgets")
    if not modes or len(set(modes))!=len(modes) or any(v not in MODES for v in modes):raise ValueError("Invalid modes")
    tasks={t["id"]:t for t in m["tasks"]}
    indexed={}
    for r in run["rows"]:
        k=(r["mode"],r["budget"],r["id"])
        if k in indexed or k[0] not in modes or k[1] not in budgets or k[2] not in tasks:raise ValueError("Duplicate or unexpected row")
        if "error" not in r:
            c=r["raw"]["choices"][0]
            if not isinstance(c["message"].get("content"),(str,type(None))):raise ValueError("Unexpected content type")
            r={**r,"grade":grade(tasks[r["id"]],c["message"].get("content"),r["mode"],c.get("finish_reason"))}
        indexed[k]=r
    profiles=[]
    for mode in modes:
        for budget in budgets:
            for track in TRACKS:
                subset=[t for t in tasks.values() if t["track"]==track]
                if not subset:continue
                def get(ts):return [indexed[(mode,budget,t["id"])] for t in ts if (mode,budget,t["id"]) in indexed]
                p={"track":track,"mode":mode,"budget":budget,**report(get(subset),len(subset))}
                for key in ("family","domain"):
                    p["by_"+key]={}
                    for v in sorted(set(t[key] for t in subset)):
                        ts=[t for t in subset if t[key]==v]
                        p["by_"+key][v]=report(get(ts),len(ts))
                if track=="ladder":
                    p["by_level"]={}
                    roots=collections.defaultdict(dict)
                    for l in range(1,5):
                        ts=[t for t in subset if t["level"]==l]
                        p["by_level"][str(l)]=report(get(ts),len(ts))
                        for t in ts:
                            row=indexed.get((mode,budget,t["id"]),{})
                            roots[t["root"]][l]=row.get("grade",{}).get("semantic_correct")
                    low=[];high=[]
                    for levels in roots.values():
                        a=b=0
                        for l in range(1,5):
                            if levels.get(l) is not True:break
                            a+=1
                        for l in range(1,5):
                            if levels.get(l) is False:break
                            b+=1
                        low.append(a);high.append(b)
                    p["depth_lower"]=sum(low)/len(low);p["depth_upper"]=sum(high)/len(high)
                profiles.append(p)
    return profiles
