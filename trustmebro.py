import argparse
import hashlib
import json
import random
import statistics
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

VERSION = "core-v0.1"
FAMILIES = ("arithmetic", "schedule", "modular", "path", "copy", "json", "order", "filter")

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()

def generate(seed, variants=20):
    rng = random.Random(seed)
    tasks = []
    for i in range(variants):
        a,b,c,d = [rng.randint(3,97) for _ in range(4)]
        edges = [rng.randint(2,25) for _ in range(5)]
        w,x,y,z,v = edges
        nums = rng.sample(range(10,100), 8)
        word = "".join(rng.choices("abcdefghjkmnpqrstuvwxyz23456789", k=9))
        items = [
            ("arithmetic", f"Compute ({a} * {b} - {c}) + {d} * {c}. Return only the integer.", str(a*b-c+d*c)),
            ("schedule", f"A machine runs every {a} minutes and another every {b} minutes, both starting at minute 0. At what first positive minute do both run together? Return only the integer.", str(__import__("math").lcm(a,b))),
            ("modular", f"What is the remainder when {a} raised to the power {b} is divided by {c}? Return only the integer.", str(pow(a,b,c))),
            ("path", f"Directed graph edges with costs: A->B {w}, A->C {x}, B->C {y}, B->D {z}, C->D {v}. Find minimum total cost from A to D. Return only the integer.", str(min(w+z,x+v,w+y+v))),
            ("copy", f"Return exactly this identifier, with its case unchanged and no quotes: ID-{word.upper()}-{a}", f"ID-{word.upper()}-{a}"),
            ("json", f"Return only a JSON object with exactly three keys: id (string {word}), count (integer {a}), enabled (boolean false).", {"id":word,"count":a,"enabled":False}),
            ("order", f"Return these integers in ascending order, separated by commas with no spaces: {nums}", ",".join(map(str,sorted(nums)))),
            ("filter", f"From {nums}, keep only even integers greater than 40, in their original order. Return comma-separated values without spaces, or NONE if empty.", ",".join(str(n) for n in nums if n>40 and n%2==0) or "NONE")
        ]
        for family,prompt,answer in items:
            tasks.append({"id":f"{family}-{i:03d}","family":family,"prompt":prompt,"answer":answer})
    rng.shuffle(tasks)
    return {"version":VERSION,"seed":seed,"variants":variants,"tasks":tasks}

def verify_manifest(manifest):
    if manifest != generate(manifest["seed"],manifest["variants"]):
        raise ValueError("Manifest does not match frozen generator")

def no_duplicates(pairs):
    out = {}
    for k,v in pairs:
        if k in out:
            raise ValueError("Duplicate JSON key")
        out[k]=v
    return out

def correct(task, content):
    if not isinstance(content,str):
        return False
    if task["family"] == "json":
        try:
            return canonical(json.loads(content,object_pairs_hook=no_duplicates)) == canonical(task["answer"])
        except (ValueError,TypeError):
            return False
    return content.strip() == task["answer"]

def file_hash(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""):
            h.update(chunk)
    return {"filename":Path(path).name,"bytes":Path(path).stat().st_size,"sha256":h.hexdigest()}

def save(path,obj):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    tmp.replace(p)

def request(url,model,task,budget,seed,timeout):
    body={"model":model,"messages":[{"role":"user","content":task["prompt"]}],"temperature":0,"max_tokens":budget,"seed":seed}
    req=urllib.request.Request(url.rstrip("/")+"/chat/completions",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    start=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw=json.load(r)
        choice=raw["choices"][0]
        message=choice["message"]
        if not isinstance(message,dict):
            raise ValueError("Invalid message")
        return {"id":task["id"],"budget":budget,"raw":raw,"elapsed_s":time.monotonic()-start}
    except Exception as exc:
        return {"id":task["id"],"budget":budget,"error":f"{type(exc).__name__}: {exc}","elapsed_s":time.monotonic()-start}

def score(run):
    manifest=run["manifest"]
    verify_manifest(manifest)
    if digest(manifest)!=run["manifest_sha256"]:
        raise ValueError("Manifest digest mismatch")
    tasks={t["id"]:t for t in manifest["tasks"]}
    budgets=run["budgets"]
    rows={}
    for row in run["rows"]:
        key=(row["budget"],row["id"])
        if key in rows or key[0] not in budgets or key[1] not in tasks:
            raise ValueError("Duplicate or unexpected result")
        rows[key]=row
    profiles=[]
    for budget in budgets:
        families={f:{"correct":0,"total":0} for f in FAMILIES}
        failures=0
        times=[]
        tokens=[]
        reasons=defaultdict(int)
        for ident,task in tasks.items():
            family=families[task["family"]]
            family["total"]+=1
            row=rows.get((budget,ident))
            if row is None or "error" in row:
                failures+=1
                continue
            raw=row["raw"]
            choice=raw["choices"][0]
            family["correct"]+=int(correct(task,choice["message"].get("content")))
            reasons[str(choice.get("finish_reason"))]+=1
            times.append(row["elapsed_s"])
            token=(raw.get("usage") or {}).get("completion_tokens")
            if type(token) is int and token>=0:
                tokens.append(token)
        total=len(tasks)
        passed=sum(x["correct"] for x in families.values())
        profiles.append({"budget":budget,"complete":failures==0,"failures":failures,"correct":passed,"total":total,"accuracy":passed/total,"families":families,"finish_reasons":dict(reasons),"median_elapsed_s":statistics.median(times) if times else None,"total_elapsed_s":sum(times),"reported_completion_tokens":sum(tokens) if tokens else None,"token_count_coverage":len(tokens),"reported_tokens_over_cap":sum(t>budget for t in tokens)})
    return profiles

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="command",required=True)
    g=sub.add_parser("generate")
    g.add_argument("--seed",type=int,default=17)
    g.add_argument("--out",required=True)
    r=sub.add_parser("run")
    for name in ("tasks","url","model","runtime","hardware","out"):
        r.add_argument("--"+name,required=True)
    r.add_argument("--artifact",action="append",required=True)
    r.add_argument("--budgets",default="128,512,2048")
    r.add_argument("--timeout",type=float,default=300)
    s=sub.add_parser("score")
    s.add_argument("run")
    args=p.parse_args()
    if args.command=="generate":
        save(args.out,generate(args.seed))
    elif args.command=="score":
        print(json.dumps(score(json.loads(Path(args.run).read_text())),indent=2))
    else:
        m=json.loads(Path(args.tasks).read_text())
        verify_manifest(m)
        if m["variants"]!=20:
            raise ValueError("Core requires 20 variants")
        budgets=list(map(int,args.budgets.split(",")))
        if any(b<=0 for b in budgets) or len(set(budgets))!=len(budgets):
            raise ValueError("Budgets must be positive and unique")
        out=Path(args.out)
        if out.exists():
            raise FileExistsError(out)
        run={"version":VERSION,"manifest":m,"manifest_sha256":digest(m),"model":args.model,"runtime":args.runtime,"hardware":args.hardware,"artifacts":[file_hash(x) for x in args.artifact],"temperature":0,"budgets":budgets,"rows":[]}
        save(out,run)
        for b in budgets:
            for task in m["tasks"]:
                run["rows"].append(request(args.url,args.model,task,b,m["seed"],args.timeout))
                save(out,run)
        print(json.dumps(score(run),indent=2))

if __name__=="__main__":
    main()
