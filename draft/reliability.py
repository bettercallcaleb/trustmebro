import collections
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import measurement as base
from trustmebro import canonical

VERSION="reliability-draft-v0.3.1"
LABEL=re.compile(r"(?i)^(final(?: answer)?|answer)[ \t]*:[ \t]*(.*)$")
PHRASE=re.compile(r"(?i)^(?:the )?(?:final )?answer is[ \t]+(.+)$")
FENCE_OPEN=re.compile(r"^"+re.escape(chr(96)*3)+r"(?:[A-Za-z0-9_-]+)?$")
FENCE_CLOSE=chr(96)*3
MARKERS=("**","__","*","_",chr(96))

def unwrap_inline(text):
    s=text.strip()
    styles=[]
    for _ in range(4):
        for w in MARKERS:
            if s.startswith(w) and s.endswith(w) and len(s)>2*len(w) and w not in s[len(w):-len(w)]:
                s=s[len(w):-len(w)].strip()
                styles.append("inline_code" if w==chr(96) else "markdown_emphasis")
                break
        else:break
    return s,styles

def safe_value(s,task):
    try:
        v=base.value(s,task)
        if v is not None:canonical(v)
        return v
    except (ValueError,TypeError,OverflowError):return None

def parse_declaration(line,task):
    s=line.strip()
    heading=re.match(r"^#{1,6}\s+",s)
    if heading:s=s[heading.end():]
    s,styles=unwrap_inline(s)
    if re.match(r"(?i)^(?:\*\*|__)(?:final(?: answer)?|answer):(?:\*\*|__)\s*",s):
        s=re.sub(r"(?i)^(\*\*|__)((?:final(?: answer)?|answer):)\1",r"\2",s)
        styles.append("markdown_emphasis")
    match=LABEL.fullmatch(s)
    if match:
        label,body=match.groups()
        if not body and (heading or label.lower()=="final answer"):return None
        body,inner=unwrap_inline(body)
        return {"value":safe_value(body,task),"styles":styles+inner+["explicit_label"],"raw":body}
    phrase=PHRASE.fullmatch(s)
    if phrase:
        body=phrase.group(1)
        if body.endswith("."):body=body[:-1]
        body,inner=unwrap_inline(body)
        return {"value":safe_value(body,task),"styles":styles+inner+["answer_phrase"],"raw":body}
    return None

def extract(content,task):
    s=content.strip() if isinstance(content,str) else ""
    if not s:return {"prediction":None,"status":"empty","styles":[],"declarations":0}
    lines=s.splitlines()
    decl=[]
    terminal=len(lines)-1
    in_fence=False
    fenced=set()
    unbalanced=False
    for i,line in enumerate(lines):
        z=line.strip()
        if in_fence and z==FENCE_CLOSE:
            if i==len(lines)-1:terminal=i-1
            in_fence=False
            continue
        if FENCE_OPEN.fullmatch(z):
            in_fence=True
            continue
        if in_fence:fenced.add(i)
        d=parse_declaration(line,task)
        if d is not None:
            if i in fenced:d["styles"].append("code_fence")
            decl.append((i,d))
    unbalanced=in_fence
    if decl:
        vals={canonical(d["value"]) for _,d in decl if d["value"] is not None}
        flags=sorted({x for _,d in decl for x in d["styles"]})
        out={"prediction":None,"status":"malformed_declaration","styles":flags,"declarations":len(decl)}
        if len(vals)>1:out["status"]="conflicting_declarations"
        elif any(d["value"] is None for _,d in decl):pass
        elif decl[-1][0]!=terminal or unbalanced:out["status"]="nonterminal_declaration"
        elif vals:
            out.update(prediction=decl[-1][1]["value"],status="explicit_answer")
        return out
    body=base.strip_wrapper(s)
    styles=["code_fence" if s.startswith(FENCE_CLOSE) else "inline_code"] if body!=s else []
    body,more=unwrap_inline(body)
    v=safe_value(body,task)
    return {"prediction":v,"status":"standalone_value" if v is not None else "no_explicit_answer","styles":sorted(set(styles+more)),"declarations":0}

def repeated_line(s):
    lines=[x.strip() for x in s.splitlines() if x.strip()]
    for i in range(len(lines)-2):
        if len(lines[i])>=35 and lines[i]==lines[i+1]==lines[i+2]:return True
    return False

def grade(task,content,mode,finish_reason=None):
    s=content.strip() if isinstance(content,str) else ""
    ext=extract(s,task)
    gold=task["answer"] if task["format"]=="json" else safe_value(str(task["answer"]),task)
    if gold is None:raise ValueError("Invalid gold")
    correct=None if ext["prediction"] is None else canonical(ext["prediction"])==canonical(gold)
    if mode=="strict":
        compliant=base.format_ok(s,task)
    elif mode=="relaxed":
        lines=s.splitlines()
        compliant=bool(lines and ext["declarations"]==1 and lines[-1].startswith("FINAL: ") and base.format_ok(lines[-1][7:],task))
    else:raise ValueError("Unknown mode")
    last=s.splitlines()[-1] if s else ""
    flags={
        "format_noncompliant":not compliant,
        "wrong_value":correct is False,
        "answer_unresolved":correct is None,
        "empty_visible_answer":not s,
        "multiple_declarations":ext["declarations"]>1,
        "conflicting_declarations":ext["status"]=="conflicting_declarations",
        "malformed_declaration":ext["status"]=="malformed_declaration",
        "nonterminal_declaration":ext["status"]=="nonterminal_declaration",
        "markdown_emphasis": "markdown_emphasis" in ext["styles"],
        "code_fence":"code_fence" in ext["styles"],
        "inline_code":"inline_code" in ext["styles"],
        "missing_canonical_final_marker":mode=="relaxed" and not last.startswith("FINAL: "),
        "answer_phrase":"answer_phrase" in ext["styles"],
        "strict_extra_text":mode=="strict" and ext["prediction"] is not None and not compliant and (ext["declarations"]>0 or "answer_phrase" in ext["styles"] or len(s.splitlines())>1),
        "representation_deviation":ext["prediction"] is not None and not compliant and ext["status"]=="standalone_value",
        "length_limit":finish_reason=="length",
        "finish_reason_missing":finish_reason is None,
        "other_finish_reason":finish_reason not in (None,"stop","length"),
        "repeated_text_heuristic":base.repetition_diagnostic(s) or repeated_line(s),
    }
    return {"semantic_correct":correct,"format_compliant":compliant,"joint_success":correct is True and compliant,"truncated":None if finish_reason is None else finish_reason=="length","empty":not s,"repetition_flag":flags["repeated_text_heuristic"],"extraction":ext,"flags":flags}

def report(rows,expected):
    out=base.report(rows,expected)
    flags=collections.Counter()
    extract_status=collections.Counter()
    recover=collections.Counter()
    failure_tokens=0
    failure_time=0.0
    token_known=True
    time_known=True
    for row in rows:
        if "error" in row:
            flags["transport_error"]+=1
            token_known=False
        else:
            g=row["grade"]
            flags.update(k for k,v in g["flags"].items() if v)
            extract_status[g["extraction"]["status"]]+=1
            old=row.get("legacy_grade")
            if old:
                a=old["semantic_correct"];b=g["semantic_correct"]
                if a!=b:recover[f"{a}->{b}"]+=1
                if old["joint_success"]!=g["joint_success"]:recover["joint_changed"]+=1
        if "error" in row or not row["grade"]["joint_success"]:
            token=(row.get("raw",{}).get("usage") or {}).get("completion_tokens")
            elapsed=row.get("elapsed_s")
            if type(token) is int and token>=0:failure_tokens+=token
            else:token_known=False
            if type(elapsed) in (int,float) and elapsed>=0:failure_time+=elapsed
            else:time_known=False
    out.update(scorer_version=VERSION,flag_counts=dict(sorted(flags.items())),flag_rates={k:v/expected for k,v in sorted(flags.items())},extraction_status=dict(sorted(extract_status.items())),legacy_semantic_transitions=dict(recover),failed_attempt_tokens=failure_tokens if token_known and len(rows)==expected else None,failed_attempt_time_s=failure_time if time_known and len(rows)==expected else None)
    return out

def replay(tasks,rows,mode,budget=None):
    indexed={t["id"]:t for t in tasks}
    if len(indexed)!=len(tasks):raise ValueError("Duplicate task")
    seen=set();graded=[]
    for r in rows:
        ident=r["id"]
        if ident not in indexed or ident in seen:raise ValueError("Unexpected or duplicate response")
        seen.add(ident)
        if "error" in r:graded.append(r);continue
        choice=r["raw"]["choices"][0]
        s=choice["message"].get("content")
        if not isinstance(s,(str,type(None))):raise ValueError("Unexpected content")
        task=indexed[ident]
        g=grade(task,s,mode,choice.get("finish_reason"))
        old=base.grade(task,s,mode,choice.get("finish_reason"))
        usage=(r["raw"].get("usage") or {}).get("completion_tokens")
        g["flags"]["reported_tokens_over_cap"]=budget is not None and type(usage) is int and usage>budget
        graded.append({**r,"grade":g,"legacy_grade":old})
    return graded
