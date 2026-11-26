import argparse
import collections
import functools
import hashlib
import itertools
import json
import random
import sqlite3
from contextlib import closing
from pathlib import Path

VERSION="core-depth-draft-v0.1"
FAMILIES=("routing","scheduling","ledger","relational","constraints")
NODES="ABCDEF"

def stable(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def rng_for(seed,family,variant):
    return random.Random(int(hashlib.sha256(f"{VERSION}:{seed}:{family}:{variant}".encode()).hexdigest(),16))

def route_ref(edges,level):
    best=[]
    for n in range(5):
        for mid in itertools.combinations(NODES[1:-1],n):
            path="A"+"".join(mid)+"F"
            try: pairs=[edges[(a,b)] for a,b in zip(path,path[1:])]
            except KeyError:continue
            if level>=2 and "C" not in path:continue
            if level>=3 and sum(t for _,t in pairs)>4:continue
            if level>=4 and any(a[1] and b[1] for a,b in zip(pairs,pairs[1:])):continue
            best.append(sum(w for w,_ in pairs))
    return min(best) if best else None

def route_dp(edges,level):
    @functools.lru_cache(None)
    def solve(node,visited,toll,prev):
        if node=="F":return 0 if level==1 or visited else None
        costs=[]
        for (a,b),(w,t) in edges.items():
            if a!=node:continue
            if level>=3 and toll+t>4:continue
            if level>=4 and prev and t:continue
            future=solve(b,visited or b=="C",toll+t,bool(t))
            if future is not None:costs.append(w+future)
        return min(costs) if costs else None
    return solve("A",False,0,False)

def routing(r):
    control=r.random()<.25
    for attempt in range(10000):
        edges={(a,b):(r.randint(1,16),r.randint(0,3)) for a,b in itertools.combinations(NODES,2) if r.random()<.8 or (a,b) in (("A","C"),("C","E"),("E","F"))}
        edges[("A","C")]=(r.randint(4,18),r.randint(1,2))
        edges[("C","E")]=(r.randint(4,18),0)
        edges[("E","F")]=(r.randint(4,18),r.randint(1,2))
        ans=[route_ref(edges,l) for l in range(1,5)]
        if None in ans or (control and not any(a==b for a,b in zip(ans,ans[1:]))) or (not control and not all(a<b for a,b in zip(ans,ans[1:]))):continue
        assert ans==[route_dp(edges,l) for l in range(1,5)]
        rows="; ".join(f"{a}->{b}: time {w}, toll {t}" for (a,b),(w,t) in sorted(edges.items()))
        base=f"Directed routes (only listed edges exist): {rows}. Travel from A to F. Minimize total time."
        rules=[""," You must visit C."," You must visit C and total toll must be at most 4."," You must visit C, total toll must be at most 4, and two successive edges cannot both have positive toll."]
        return [(base+rules[l-1]+" Return the minimum total time as an integer.",ans[l-1],{"previous_level_answer":ans[l-2] if l>1 else None,"active_constraint":None if l==1 else ans[l-1]!=ans[l-2],"control":control}) for l in range(1,5)]
    raise RuntimeError("routing rejection exhausted")

def schedule_ref(jobs,level,mandatory):
    best=0
    for bits in range(1<<len(jobs)):
        chosen=[j for i,j in enumerate(jobs) if bits>>i&1]
        if any(a[1]<b[2] and b[1]<a[2] for a,b in itertools.combinations(chosen,2)):continue
        if level>=3 and sum(j[4] for j in chosen)>8:continue
        ids={j[0] for j in chosen}
        if level>=2 and mandatory not in ids:continue
        if level>=4 and any(j[5]!="-" and j[5] not in ids for j in chosen):continue
        best=max(best,sum(j[3] for j in chosen))
    return best

def schedule_dp(jobs,level,mandatory):
    jobs=sorted(jobs,key=lambda j:(j[2],j[1],j[0]))
    @functools.lru_cache(None)
    def solve(i,last,budget,ids):
        if i==len(jobs):return 0 if level==1 or mandatory in ids else None
        name,start,end,reward,cost,dep=jobs[i]
        options=[solve(i+1,last,budget,ids)]
        if start>=last and (level<3 or cost<=budget) and (level<4 or dep=="-" or dep in ids):
            future=solve(i+1,end,budget-cost,tuple(sorted((*ids,name))))
            if future is not None:options.append(reward+future)
        return max((x for x in options if x is not None),default=None)
    return solve(0,0,8,()) or 0

def scheduling(r):
    control=r.random()<.25
    zero_control=r.random()<.12
    for attempt in range(10000):
        jobs=[]
        for name in "ABCDEFGH":
            start=r.randrange(0,12);end=start+r.randint(1,5)
            jobs.append([name,start,end,r.randint(2,18),r.randint(1,5),"-"])
        for j in jobs:
            candidates=[k[0] for k in jobs if k[2]<=j[1]]
            if candidates and r.random()<.65:j[5]=r.choice(candidates)
        mandatory=r.choice(jobs)[0]
        ans=[schedule_ref(jobs,l,mandatory) for l in range(1,5)]
        if (control and not any(a==b for a,b in zip(ans,ans[1:]))) or (not control and not all(a>b for a,b in zip(ans,ans[1:]))):continue
        if (ans[3]==0)!=zero_control:continue
        assert ans==[schedule_dp(jobs,l,mandatory) for l in range(1,5)]
        rows="; ".join(f"{n} ({a},{b},{v},{c},{d})" for n,a,b,v,c,d in jobs)
        base=f"Jobs: {rows}. Fields are (start,end,reward,cost,prerequisite), with '-' meaning none. Select jobs on one machine; intervals [start,end) cannot overlap. Each job can be selected at most once. Maximize total reward. If no feasible selection exists, the answer is 0."
        rules=[" Ignore cost and prerequisites.",f" Job {mandatory} must be selected. Ignore cost and prerequisites.",f" Job {mandatory} must be selected. Total cost must be at most 8. Ignore prerequisites.",f" Job {mandatory} must be selected. Total cost must be at most 8. A selected job with a prerequisite requires that prerequisite to be selected and finished before or at its start."]
        return [(base+rules[l-1]+" Return the optimal integer.",ans[l-1],{"previous_level_answer":ans[l-2] if l>1 else None,"active_constraint":None if l==1 else ans[l-1]!=ans[l-2],"control":control}) for l in range(1,5)]
    raise RuntimeError("scheduling rejection exhausted")

def ledger_int(start,events):
    balances=dict(start);holds={k:0 for k in balances};rejected=0
    def apply(e):
        op,a,n,*rest=e
        if op=="add":balances[a]+=n
        elif op=="spend":
            if balances[a]-holds[a]<n:return False
            balances[a]-=n
        elif op=="hold":
            if balances[a]-holds[a]<n:return False
            holds[a]+=n
        elif op=="release":
            if holds[a]<n:return False
            holds[a]-=n
        elif op=="transfer":
            if balances[a]-holds[a]<n:return False
            balances[a]-=n;balances[rest[0]]+=n
        else:raise ValueError(op)
        return True
    for batch in events:
        b,h=balances.copy(),holds.copy()
        if not all(apply(e) for e in batch):
            balances,holds=b,h;rejected+=1
    return balances["A"]-holds["A"],rejected

def ledger_units(start,events):
    accounts={k:[0]*v for k,v in start.items()};rejected=0
    for batch in events:
        trial={k:list(v) for k,v in accounts.items()}
        valid=True
        for op,a,n,*rest in batch:
            free=[i for i,v in enumerate(trial[a]) if v==0]
            held=[i for i,v in enumerate(trial[a]) if v==1]
            if op=="add":trial[a].extend([0]*n);continue
            ids=held if op=="release" else free
            if len(ids)<n:valid=False;break
            if op in ("hold","release"):
                for i in ids[:n]:trial[a][i]=1 if op=="hold" else 0
            else:
                for i in reversed(ids[:n]):trial[a].pop(i)
                if op=="transfer":trial[rest[0]].extend([0]*n)
        if valid:accounts=trial
        else:rejected+=1
    return accounts["A"].count(0),rejected

def ledger(r):
    initial={"A":r.randint(11,22),"B":r.randint(5,13)}
    results=[]
    for l in range(1,5):
        control=r.random()<.25
        for attempt in range(1000):
            ops=["add","spend"]+ (["hold","release"] if l>=2 else [])+(["transfer"] if l>=3 else [])
            events=[]
            for _ in range(8):
                batch=[]
                for j in range(r.randint(2,3) if l==4 and r.random()<.5 else 1):
                    op=r.choice(ops);a=r.choice("AB") if l>=3 else "A";n=r.randint(2,13)
                    batch.append([op,a,n,*([("B" if a=="A" else "A")] if op=="transfer" else [])])
                events.append(batch)
            ans,rejected=ledger_int(initial,events)
            assert (ans,rejected)==ledger_units(initial,events)
            if not rejected and not control:continue
            present={e[0] for b in events for e in b}
            if l>=2 and not {"hold","release"}<=present:continue
            if l>=3 and "transfer" not in present:continue
            rollback_changes=ledger_int(initial,[[e] for b in events for e in b])[0]!=ans
            if l==4 and rollback_changes==control:continue
            break
        else:raise RuntimeError("ledger rejection exhausted")
        def show(e):return " ".join([e[0].upper(),*map(str,e[1:])])
        rows="; ".join("["+", ".join(show(e) for e in b)+"]" for b in events)
        rules=" ADD increases balance. SPEND reduces balance if enough available funds exist."
        if l>=2:rules+=" Available = balance minus held. HOLD increases held if enough available. RELEASE reduces held if enough held."
        else:rules+=" Available equals balance."
        if l>=3:rules+=" TRANSFER source n destination reduces the source balance and increases the destination balance by n if the source has enough available; holds do not move."
        if l==4:rules+=" Each bracket is atomic: if any operation fails, undo all operations in that bracket; proceed to next bracket."
        else:rules+=" A failed operation has no effect."
        p=f"Initial balances A={initial['A']}, B={initial['B']}; initially held=0 in both accounts."+rules+f" Execute these brackets in order: {rows}. Return A's final available funds as an integer."
        results.append((p,ans,{"rejected_brackets":rejected,"rollback_changes_answer":rollback_changes,"control":control}))
    return results

def relational_py(users,events,level):
    events=[e for e in events if e[3]=="paid"] if level<3 else list({uid:max((e for e in events if e[0]==uid),key=lambda e:e[1]) for uid in {e[0] for e in events}}.values())
    active={uid for uid,g,status in users if status=="active"}
    selected=[e for e in events if e[3]=="paid" and e[2]>=5 and (level==1 or e[0] in active)]
    if level<4:return sum(e[2] for e in selected)
    groups=collections.defaultdict(int)
    lookup={u:g for u,g,s in users}
    for uid,seq,amount,status in selected:groups[lookup[uid]]+=amount
    blocked={g for uid,g,status in users if status=="blocked"}
    return sum(n for g,n in groups.items() if g not in blocked and n>=18)

def relational_sql(users,events,level):
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("create table users(uid text primary key,g text,status text)")
        db.execute("create table events(uid text,seq integer,amount integer,status text,primary key(uid,seq))")
        db.executemany("insert into users values(?,?,?)",users)
        db.executemany("insert into events values(?,?,?,?)",events)
        source="events e" if level<3 else "(select e.* from events e where not exists(select 1 from events f where f.uid=e.uid and f.seq>e.seq)) e"
        join="" if level==1 else " join users u on e.uid=u.uid"
        where=" where e.status='paid' and e.amount>=5"+(" and u.status='active'" if level>=2 else "")
        sql="select coalesce(sum(e.amount),0) from "+source+join+where
        if level==4:sql="select coalesce(sum(total),0) from (select sum(e.amount) total from "+source+join+where+" and not exists(select 1 from users b where b.g=u.g and b.status='blocked') group by u.g having sum(e.amount)>=18)"
        return db.execute(sql).fetchone()[0]


def relational(r):
    control=r.random()<.25
    zero_control=r.random()<.12
    for attempt in range(10000):
        users=[(uid,r.choice("XYZ"),r.choice(["active","active","active","blocked"])) for uid in "ABCDEFGH"]
        events=[(uid,s,r.randint(1,28),r.choice(["paid","paid","paid","void"])) for uid,_,_ in users for s in range(1,r.randint(2,4)+1)]
        ans=[relational_py(users,events,l) for l in range(1,5)]
        if (control and not any(a==b for a,b in zip(ans,ans[1:]))) or (not control and not all(a>b for a,b in zip(ans,ans[1:]))):continue
        if (ans[3]==0)!=zero_control:continue
        assert ans==[relational_sql(users,events,l) for l in range(1,5)]
        table1="; ".join(" ".join(map(str,u)) for u in users)
        table2="; ".join(" ".join(map(str,e)) for e in events)
        base=f"Users (id,group,status): {table1}. Events (user,sequence,amount,status): {table2}."
        rules=[" Sum amounts of all paid events with amount >=5."," Sum amounts of all paid events with amount >=5 belonging to active users."," For each user, first retain only the event with largest sequence, regardless of status. Then sum amounts of retained paid events with amount >=5 belonging to active users."," For each user, first retain only the event with largest sequence, regardless of status. Keep retained paid events with amount >=5 belonging to active users. Sum amounts within each group. Exclude any group containing any blocked user, even if that user has no qualifying event. Also exclude groups with total below 18. Sum the remaining group totals."]
        return [(base+rules[l-1]+" Return the resulting integer.",ans[l-1],{"previous_level_answer":ans[l-2] if l>1 else None,"active_constraint":None if l==1 else ans[l-1]!=ans[l-2],"control":control}) for l in range(1,5)]
    raise RuntimeError("relational rejection exhausted")

def position_ok(p,c):
    op,a,b=c
    if op=="before":return p[a]<p[b]
    if op=="adjacent":return abs(p[a]-p[b])==1
    if op=="notadj":return abs(p[a]-p[b])!=1
    if op=="notpos":return p[a]!=b
    if op=="either_before":
        x,y=b
        return (p[a]<p[x])!=(p[a]<p[y])
    raise ValueError(op)

def logic_ref(people,cs):
    return sum(all(position_ok(dict(zip(order,range(1,len(order)+1))),c) for c in cs) for order in itertools.permutations(people))

def logic_dfs(people,cs):
    def valid(order,c):
        op,a,b=c
        if op=="notpos":return len(order)<b or order[b-1]!=a
        if op=="either_before":
            x,y=b
            if not all(v in order for v in (a,x,y)):return True
            return (order.index(a)<order.index(x)) != (order.index(a)<order.index(y))
        if a not in order or b not in order:
            if op=="before" and b in order and a not in order:return False
            return True
        i,j=order.index(a),order.index(b)
        return i<j if op=="before" else abs(i-j)==1 if op=="adjacent" else abs(i-j)!=1
    def solve(order,remaining):
        if not all(valid(order,c) for c in cs):return 0
        if not remaining:return 1
        return sum(solve(order+x,remaining.replace(x,"")) for x in remaining)
    return solve("",people)

def constraints(r):
    x=r.random()
    kind="unsat" if x<.12 else "redundant" if x<.32 else "active"
    control=kind!="active"
    people="ABCDEFG"[:r.randint(5,7)]
    for attempt in range(10000):
        witness=list(people);r.shuffle(witness);p={a:i for i,a in enumerate(witness,1)}
        pairs=list(itertools.combinations(witness,2));r.shuffle(pairs)
        cs=[("before",*ab) for ab in pairs[:r.randint(2,4)]]
        levels=[list(cs)]
        a,b=r.choice(list(zip(witness,witness[1:])));cs.append(("adjacent",a,b))
        levels.append(list(cs))
        a=r.choice(witness);j=r.choice([k for k in range(1,len(people)+1) if k!=p[a]]);cs.append(("notpos",a,j))
        a,b=r.choice([(a,b) for a,b in pairs if abs(p[a]-p[b])>1]);cs.append(("notadj",a,b))
        levels.append(list(cs))
        a=r.choice(witness[1:-1]);x=r.choice(witness[:p[a]-1]);y=r.choice(witness[p[a]:]);cs.append(("either_before",a,(x,y)))
        if kind=="unsat":
            cs[-1]=("either_before",witness[0],tuple(r.sample(witness[1:],2)))
        levels.append(list(cs))
        ans=[logic_ref(people,c) for c in levels]
        if not ans[2]:continue
        if kind=="unsat" and ans[-1]!=0:continue
        if kind=="redundant" and (not ans[-1] or not any(a==b for a,b in zip(ans,ans[1:]))):continue
        if kind=="active" and (not ans[-1] or not all(a>b for a,b in zip(ans,ans[1:]))):continue
        assert ans==[logic_dfs(people,c) for c in levels]
        def show(c):
            op,a,b=c
            if op=="before":return f"{a} is before {b}"
            if op=="adjacent":return f"{a} and {b} occupy adjacent slots"
            if op=="notadj":return f"{a} and {b} do not occupy adjacent slots"
            if op=="notpos":return f"{a} is not in slot {b}"
            x,y=b
            return f"exactly one of these statements is true: {a} is before {x}; {a} is before {y}"
        return [(f"Arrange {','.join(people)} into slots 1 through {len(people)}, each used exactly once. Before means a smaller slot number. Rules: {'; '.join(show(c) for c in levels[l-1])}. How many distinct arrangements satisfy every rule? Return the count as an integer.",ans[l-1],{"previous_level_answer":ans[l-2] if l>1 else None,"active_constraint":None if l==1 else ans[l-1]!=ans[l-2],"control":control}) for l in range(1,5)]
    raise RuntimeError("constraint rejection exhausted")

def generate(seed,variants=2):
    if not 1<=variants<=100:raise ValueError("variants must be 1..100")
    tasks=[]
    seen=set()
    for family in FAMILIES:
        fn=globals()[family]
        for v in range(variants):
            rng=rng_for(seed,family,v)
            for attempt in range(1000):
                group=fn(rng)
                prompts={row[0] for row in group}
                if len(prompts)==4 and not (prompts & seen):break
            else:raise RuntimeError("Duplicate scenario rejection exhausted")
            seen.update(prompts)
            for l,(prompt,answer,diagnostic) in enumerate(group,1):
                tasks.append({"id":f"core-depth/{family}/v{v:03d}/L{l}","track":"core-depth","family":family,"level":l,"root":f"{family}/v{v:03d}","prompt":prompt,"answer":str(answer),"format":"integer","design_checks":diagnostic})
    return {"version":VERSION,"seed":seed,"variants":variants,"tasks":tasks}

def validate_panel(manifests):
    seen=set()
    for manifest in manifests:
        for task in manifest["tasks"]:
            if task["prompt"] in seen:raise ValueError("Duplicate prompt across panel: "+task["id"])
            seen.add(task["prompt"])
    return len(seen)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=17)
    p.add_argument("--variants",type=int,default=2)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    Path(args.out).write_text(json.dumps(generate(args.seed,args.variants),indent=2)+"\n")
if __name__=="__main__":main()
