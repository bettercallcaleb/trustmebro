import json

from . import numeric


def jwt(r):
    now=r.randrange(1700000000,1999999999)
    expected_iss="https://issuer.example"
    expected_aud="payments"
    def valid(token):
        audience=token.get("aud")
        if isinstance(audience,str):
            audience=[audience]
        return (token["exp"]>now and token.get("nbf",0)<=now and token.get("iss",expected_iss)==expected_iss and expected_aud in (audience or [expected_aud]))
    out=[]
    for level in range(1,5):
        tokens=[]
        for i in range(6 if level>=3 else 5):
            nbf=now+r.choice([-120,-1,0,1,80])
            exp=now+r.choice([-180,-1,0,1,120])
            token={"id":f"T{i+1}","exp":exp}
            if level>=2:
                token["nbf"]=nbf
            if level>=3:
                token["iss"]=r.choice([expected_iss,"https://other.example",expected_iss])
                token["aud"]=r.choice([expected_aud,"admin",["payments","audit"],["admin","audit"]])
            if level>=4 and i in (1,4):
                token["nbf"]=now
                token["exp"]=now+(1 if i==1 else 0)
            tokens.append(token)
        if level==1:
            explanation=f"JWT exp claims only. No nbf/audience/issuer validation is applied. Valid iff now < exp."
        elif level==2:
            explanation="JWT exp and nbf claims only. No audience or issuer check. A token is valid iff nbf <= now < exp."
        else:
            explanation=f"JWT verifier requires issuer '{expected_iss}', audience '{expected_aud}' (string or array membership), and nbf <= now < exp. No clock skew; signatures already verified."
        answer=sum(valid(t) for t in tokens)
        prompt=f"{explanation} Current NumericDate={now}. Token claims: {json.dumps(tokens,separators=(',',':'))}. How many tokens are accepted?"
        out.append((prompt,*numeric(answer)))
    return ("security-hard","jwt-boundary-validation","https://www.rfc-editor.org/rfc/rfc7519.html",out)


def rbac(r):
    namespace=r.choice(["alpha","beta","gamma"])
    other={"alpha":"beta","beta":"gamma","gamma":"alpha"}[namespace]
    rules=[
        {"binding":"RoleBinding","namespace":namespace,"group":"","resources":["pods"],"verbs":["get","list"]},
        {"binding":"RoleBinding","namespace":other,"group":"","resources":["pods","pods/log"],"verbs":["get"]},
        {"binding":"ClusterRoleBinding","namespace":"ALL","group":"","resources":["configmaps"],"verbs":["get","list"]},
        {"binding":"RoleBinding","namespace":namespace,"group":"","resources":["pods/log"],"verbs":["get"]},
        {"binding":"RoleBinding","namespace":namespace,"group":"apps","resources":["deployments"],"verbs":["get","patch"]},
        {"binding":"ClusterRoleBinding","namespace":"ALL","group":"","resources":["pods"],"verbs":["watch"]},
    ]
    requests=[
        {"ns":namespace,"group":"","resource":"pods","verb":"get"},
        {"ns":other,"group":"","resource":"pods","verb":"list"},
        {"ns":namespace,"group":"","resource":"pods/log","verb":"get"},
        {"ns":other,"group":"","resource":"pods/log","verb":"get"},
        {"ns":namespace,"group":"apps","resource":"deployments","verb":"patch"},
        {"ns":other,"group":"apps","resource":"deployments","verb":"get"},
        {"ns":other,"group":"","resource":"configmaps","verb":"get"},
        {"ns":other,"group":"","resource":"pods","verb":"watch"},
    ]
    r.shuffle(requests)
    def allowed(req, active):
        return any((rule["binding"]=="ClusterRoleBinding" or req["ns"]==rule["namespace"])
                   and req["group"]==rule["group"]
                   and req["resource"] in rule["resources"]
                   and req["verb"] in rule["verbs"] for rule in active)
    out=[]
    for level in range(1,5):
        active=rules[:[1,2,4,6][level-1]]
        selected=requests[:[4,5,7,8][level-1]]
        if level>=3:
            r.shuffle(selected)
        if level==4:
            selected.append({"ns":namespace,"group":"","resource":"pods/status","verb":"get"})
        count=sum(allowed(req,active) for req in selected)
        prompt=("Kubernetes RBAC: every listed binding targets service account "+namespace+"/runner. "
                "RoleBindings grant only in their binding namespace, even when referring to a ClusterRole. "
                "ClusterRoleBindings grant cluster-wide. Exact apiGroup, resource (including subresource), and verb must match; none are wildcards. "
                "Bindings/rules: "+json.dumps(active,separators=(',',':'))
                +". Authorization requests: "+json.dumps(selected,separators=(',',':'))
                +". How many requests are authorized for that service account?")
        out.append((prompt,*numeric(count)))
    return ("security-hard","kubernetes-rbac-scope","https://kubernetes.io/docs/reference/access-authn-authz/rbac/",out)


def scheduling(r):
    zone=r.choice(["east","west"])
    disk=r.choice(["ssd","hdd"])
    nodes=[]
    for i in range(6):
        nodes.append({
            "id":f"n{i+1}",
            "zone":r.choice(["east","west"]),
            "disk":r.choice(["ssd","hdd"]),
            "free_cpu_m":r.choice([600,800,1200,1800,2400]),
            "free_mem_mib":r.choice([512,1024,2048,3072]),
            "taints":r.sample(["dedicated=ai:NoSchedule","dedicated=ml:NoSchedule","spot=true:PreferNoSchedule"],r.randrange(0,3)),
        })
    def can_schedule(n, selectors, cpu, mem, tolerations):
        if any(n[key]!=value for key,value in selectors.items()):
            return False
        if n["free_cpu_m"]<cpu or n["free_mem_mib"]<mem:
            return False
        return all(taint.endswith(":PreferNoSchedule") or taint in tolerations for taint in n["taints"])
    out=[]
    for level in range(1,5):
        selectors={"zone":zone}
        if level>=2:
            selectors["disk"]=disk
        cpu=[500,700,1000,1100][level-1]
        mem=[512,512,1024,1024][level-1]
        tolerations=[]
        if level>=3:
            tolerations=["dedicated=ai:NoSchedule"]
        if level>=4:
            tolerations=["dedicated=ml:NoSchedule"]
        selected=nodes[:[3,4,5,6][level-1]]
        ans=sum(can_schedule(n,selectors,cpu,mem,tolerations) for n in selected)
        prompt=(
            "Kubernetes scheduling HARD feasibility only. A node qualifies when ALL nodeSelectors match, enough free request-capacity remains, "
            "and each :NoSchedule taint is explicitly tolerated. :PreferNoSchedule is SOFT and does not disqualify a node. "
            "Node free resources already account for previous Pod requests. "
            f"Pod selectors={selectors}, cpu request={cpu}m, memory request={mem}MiB, exact tolerations={tolerations}. "
            f"Nodes={json.dumps(selected,separators=(',',':'))}. "
            "How many nodes pass every hard filter? Do not predict the scheduler's scoring choice."
        )
        out.append((prompt,*numeric(ans)))
    return ("security-hard","kubernetes-scheduling-filters","https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/",out)


BUILDERS=[jwt,rbac,scheduling]
