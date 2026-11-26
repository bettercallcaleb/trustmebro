import ipaddress
import json

from .hardcases import rng_for


def rebalance(item, seed):
    family = item["concept"].rsplit("-v", 1)[0]
    level = item["level"]
    r = rng_for(seed, "exact-balanced-v04:"+family, item["concept"]+f"/L{level}")

    if family == "ipv4-cidr-boundaries" and level in (1, 2):
        p = r.randrange(25, 31)
        ip = ipaddress.IPv4Address(f"172.{r.randrange(20,220)}.{r.randrange(20,220)}.{r.randrange(1,255)}")
        net = ipaddress.ip_network(f"{ip}/{p}", strict=False)
        answer = net.network_address if level == 1 else net.broadcast_address
        edge = "network" if level == 1 else "broadcast"
        item["prompt"] = f"For IPv4 address {ip}/{p}, what is the LAST OCTET (0–255) of the {edge} address?"
        item["correct"] = str(int(answer) & 255)

    if family == "tcp-send-window" and level == 3:
        cwnd = r.randrange(2500, 9600, 100)
        old_rwnd = r.randrange(1700, 9300, 100)
        outstanding = r.randrange(1000, min(cwnd, old_rwnd), 100)
        new_rwnd = r.randrange(800, 9500, 100)
        item["correct"] = str(max(0, min(cwnd, new_rwnd) - outstanding))
        item["prompt"] = (
            f"TCP sender cwnd={cwnd} bytes, advertised receive window initially={old_rwnd} bytes, "
            f"and {outstanding} bytes outstanding. Peer sends a window update changing rwnd to {new_rwnd} bytes "
            "without acknowledging any data. Ignore probes/retransmits/Nagle/pacing. "
            "How many ADDITIONAL new payload bytes may be sent immediately?"
        )

    if family == "unix-mode-bit-transforms" and level == 4:
        request = r.choice((0o666, 0o777, 0o755, 0o640, 0o700))
        mask = r.choice((0o022, 0o027, 0o077, 0o002, 0o000))
        mode = request & ~mask
        action = r.choice(("u-w", "u-x", "g-w", "o-r", "o-w"))
        mode = (mode & ~0o070) | (((mode >> 6) & 0o7) << 3)
        mode = (mode & ~0o007) | ((mode >> 3) & 0o7)
        remove = {"u-w":0o200,"u-x":0o100,"g-w":0o020,"o-r":0o004,"o-w":0o002}[action]
        mode &= ~remove
        item["correct"] = f"0{mode:03o}"
        item["prompt"] = (
            f"POSIX process umask=0{mask:03o} creates a NEW regular file with requested mode 0{request:03o}. "
            f"Then executes in order: chmod g=u; chmod o=g; chmod {action}. Ignore ACLs and special bits. "
            "What is the final four-digit octal permission mode?"
        )

    if family == "dns-ttl-chain" and level in (3, 4):
        t0 = 1000
        n = 2 if level == 3 else 4
        ttl = [r.randrange(20, 120) for _ in range(n)]
        refresh = r.randrange(1010, 1080)
        check = r.randrange(refresh + 1, 1190)
        refreshed = r.randrange(n)
        expires = [t0 + t for t in ttl]
        expires[refreshed] = refresh + ttl[refreshed]
        names = (["CNAME", "A"] if level == 3 else ["CNAME1", "CNAME2", "CNAME3", "A"])
        mask = "".join("1" if check >= t else "0" for t in expires)
        item["correct"] = mask
        item["answer_format"] = "bitstring"
        item["prompt"] = (
            f"DNS resolver caches {n} records at t={t0} in this order: {names}, with TTLs {ttl} seconds. "
            f"At t={refresh}, ONLY record #{refreshed+1} is refreshed with a fresh TTL={ttl[refreshed]}s; "
            f"no other record is refreshed. At t={check}, which records have expired? "
            f"Return exactly {n} binary digits in original record order: 1=expired, 0=not expired. "
            "Expiry time itself counts as expired; do not assume automatic dependent refresh."
        )

    if family == "kubernetes-rbac-scope" and level in (2, 3, 4):
        ns = r.choice(("alpha", "beta", "gamma"))
        other = "other-" + ns
        rules = [
            {"scope":"RoleBinding","namespace":ns,"group":"","resources":["pods"],"verbs":["get","list"]},
            {"scope":"RoleBinding","namespace":other,"group":"","resources":["pods/log"],"verbs":["get"]},
            {"scope":"ClusterRoleBinding","namespace":"ALL","group":"","resources":["configmaps"],"verbs":["get","list"]},
            {"scope":"RoleBinding","namespace":ns,"group":"apps","resources":["deployments"],"verbs":["get","patch"]},
            {"scope":"ClusterRoleBinding","namespace":"ALL","group":"","resources":["pods"],"verbs":["watch"]},
        ]
        active = rules[:{2:2,3:4,4:5}[level]]
        def authorized(q):
            return any((rule["scope"]=="ClusterRoleBinding" or q["namespace"]==rule["namespace"])
                       and q["group"]==rule["group"]
                       and q["resource"] in rule["resources"]
                       and q["verb"] in rule["verbs"] for rule in active)
        pool = [
            {"namespace":nspace,"group":grp,"resource":resource,"verb":verb}
            for nspace in (ns,other)
            for grp,resource in (("", "pods"), ("", "pods/log"),("", "configmaps"),("apps","deployments"),("","services"))
            for verb in ("get", "list", "watch", "patch")
        ]
        yes = [q for q in pool if authorized(q)]
        no = [q for q in pool if not authorized(q)]
        n = {2:5, 3:7, 4:9}[level]
        ycount = r.randrange(1, min(n,len(yes))+1)
        requests = r.sample(yes,ycount) + r.sample(no,n-ycount)
        r.shuffle(requests)
        item["correct"] = "".join("1" if authorized(q) else "0" for q in requests)
        item["answer_format"] = "bitstring"
        item["prompt"] = (
            f"Kubernetes RBAC: all bindings below apply to serviceaccount {ns}/runner. "
            "RoleBindings are namespace-limited and ClusterRoleBindings cluster-wide. "
            f"Rules: {json.dumps(active,separators=(',',':'))}. "
            f"Requests in order: {json.dumps(requests,separators=(',',':'))}. "
            f"Return exactly {n} binary digits, one per request: 1=authorized, 0=denied. "
            "Match namespace, apiGroup, resource/subresource and verb exactly."
        )

    if family == "kubernetes-scheduling-filters":
        n={1:3, 2:4, 3:5, 4:6}[level]
        zone=r.choice(("east","west"))
        disk=r.choice(("ssd","hdd"))
        cpu = r.choice((500,700,900,1100))
        mem = r.choice((512,1024,1536))
        selectors={"zone":zone}
        if level>=2:
            selectors["disk"]=disk
        tolerations=(["dedicated=ai:NoSchedule"] if level==3 else
                     ["dedicated=ml:NoSchedule"] if level==4 else [])
        nodes=[]
        for idx in range(n):
            node={"id":f"n{idx+1}","zone":zone,"disk":disk,
                  "free_cpu_m":cpu+r.randrange(0,1500,100),
                  "free_mem_mib":mem+r.randrange(0,1600,256),
                  "taints":[]}
            fault=r.choice((0,0,1,2,3,4))
            if fault==1:node["zone"]="west" if zone=="east" else "east"
            if fault==2 and level>=2:node["disk"]="hdd" if disk=="ssd" else "ssd"
            if fault==3:node["free_cpu_m"]=max(0,cpu-100)
            if fault==4:node["taints"]=["dedicated=ml:NoSchedule" if level==3 else "dedicated=ai:NoSchedule"]
            if r.randrange(5)==0:node["taints"].append("spot=true:PreferNoSchedule")
            nodes.append(node)
        def eligible(node):
            return (all(node[key]==val for key,val in selectors.items())
                    and node["free_cpu_m"]>=cpu and node["free_mem_mib"]>=mem
                    and all(taint.endswith(":PreferNoSchedule") or taint in tolerations for taint in node["taints"]))
        item["correct"] = "".join("1" if eligible(node) else "0" for node in nodes)
        item["answer_format"] = "bitstring"
        item["prompt"] = (
            "Kubernetes scheduler HARD feasibility filters only. Every node must match nodeSelectors, "
            "have enough unallocated CPU/memory for Pod requests, and tolerate all NoSchedule taints. "
            "PreferNoSchedule is a soft preference and never disqualifies a node. "
            f"Selectors={json.dumps(selectors)}, request CPU={cpu}m, memory={mem}MiB, "
            f"exact tolerations={json.dumps(tolerations)}. "
            f"Nodes in order={json.dumps(nodes,separators=(',',':'))}. "
            f"Return exactly {n} binary digits, one per node: 1=eligible, 0=ineligible."
        )

    if family == "jwt-boundary-validation" and level in (3,4):
        now=1700000000
        issuer="https://issuer.example"
        audience="payments"
        n=6
        tokens=[]
        for idx in range(n):
            valid=r.randrange(2)==0
            token={"id":f"T{idx+1}","exp":now+r.choice((5,20,60)),
                   "nbf":now-r.choice((0,5,30)),"iss":issuer,"aud":audience}
            if not valid:
                case=r.randrange(4 if level==4 else 3)
                if case==0:token["exp"]=now-r.choice((0,1,5))
                elif case==1:token["nbf"]=now+r.choice((1,20,60))
                elif case==2:token["iss"]="https://other.example"
                else:token["aud"]=r.choice(("admin",["admin","audit"]))
            if level==4 and r.randrange(5)==0 and valid:
                token["aud"]=["payments","audit"]
            tokens.append(token)
        def accepted(token):
            audience_claim=token["aud"]
            auds=[audience_claim] if isinstance(audience_claim,str) else audience_claim
            return token["nbf"] <= now < token["exp"] and token["iss"]==issuer and audience in auds
        item["correct"]="".join("1" if accepted(t) else "0" for t in tokens)
        item["answer_format"]="bitstring"
        item["prompt"]=(
            f"JWT signatures verified. Current NumericDate={now}. Required issuer={issuer}, audience={audience}; "
            "aud matches a string claim or membership in an array. No clock skew. "
            "Accept iff nbf<=now<exp, issuer correct, and audience matches. "
            f"Token claims in order: {json.dumps(tokens,separators=(',',':'))}. "
            f"Return exactly {n} binary digits: 1=accepted, 0=rejected."
        )
