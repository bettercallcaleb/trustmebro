import json
import math
import sqlite3
import tempfile
from pathlib import Path

from .calibrated import load_ladder
from .hardcases import rng_for
from .exact_balanced import rebalance


FORMATS = {
    "ipv4-lpm": "interface",
    "posix-file-offsets": "text2",
    "unix-mode-bit-transforms": "octal",
    "endian-signed-bitfields": "hex4",
}


def _better_l1(item, seed):
    family = item["concept"].rsplit("-v", 1)[0]
    if family not in ("ipv4-fragment-offset", "kubernetes-rbac-scope", "tcp-send-window"):
        return
    r = rng_for(seed, "exact-v0.4:"+family, item["concept"])
    if family == "ipv4-fragment-offset":
        payload = r.randrange(1700, 6800, 8)
        mtu = r.choice([576, 704, 960, 1280, 1500])
        limit = ((mtu - 20) // 8) * 8
        item["correct"] = str(math.ceil(payload / limit))
        item["prompt"] = (f"An IPv4 datagram has a 20-byte header and {payload} payload bytes. "
                          f"It is forwarded over an MTU of {mtu} bytes with DF=0 and no header options. "
                          "Non-final fragments must have payload sizes divisible by eight. "
                          "How many outgoing IPv4 fragments are required?")
    elif family == "kubernetes-rbac-scope":
        ns = r.choice(("alpha", "beta", "gamma", "delta"))
        other = "external-" + ns
        verb = r.choice(("get", "list", "watch"))
        requests = [
            (verb, "pods", ns),
            (verb, "pods", ns),
            ("patch", "pods", ns),
            (verb, "pods", other),
            (verb, "pods/log", ns),
            (verb, "deployments", ns),
            (verb, "pods", ns),
        ]
        sample = r.sample(requests, r.randrange(3, 8))
        r.shuffle(sample)
        count = sum((v == verb and resource == "pods" and namespace == ns) for v, resource, namespace in sample)
        item["correct"] = str(count)
        item["prompt"] = (
            f"Kubernetes RoleBinding grants serviceaccount {ns}/runner ONLY the verb {verb} on "
            f"core resource pods in namespace {ns}. There are no other permissions. "
            f"Authorization requests (verb, resource, namespace): {sample}. "
            "How many requests are authorized? Subresources and namespace must match exactly."
        )
    elif family == "tcp-send-window":
        cwnd = r.randrange(1600, 9600, 200)
        rwnd = r.randrange(1400, 9800, 200)
        outstanding = r.randrange(0, min(cwnd, rwnd), 200)
        item["correct"] = str(min(cwnd, rwnd) - outstanding)
        item["prompt"] = (
            f"A TCP sender has congestion window {cwnd} bytes, receive window {rwnd} bytes, "
            f"and {outstanding} bytes currently outstanding. No Nagle/SWS/pacing constraints. "
            "How many ADDITIONAL new payload bytes may it send?"
        )


def _harder_cases(item, seed):
    family = item["concept"].rsplit("-v", 1)[0]
    level = item["level"]
    if (family, level) not in (("sqlite-wal-snapshots", 3), ("kubernetes-rbac-scope", 4)):
        return
    r = rng_for(seed, f"exact-v0.4:L{level}:"+family, item["concept"])
    if family == "sqlite-wal-snapshots":
        kind = r.randrange(3)
        initial = r.randrange(80, 600)
        change = r.randrange(11, 90)
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "case.db"
            a = sqlite3.connect(db, isolation_level=None, timeout=0)
            b = sqlite3.connect(db, isolation_level=None, timeout=0)
            try:
                assert a.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
                a.execute("CREATE TABLE kv(v INTEGER NOT NULL)")
                a.execute("INSERT INTO kv VALUES(?)", (initial,))
                if kind == 0:
                    a.execute("BEGIN")
                    a.execute("SELECT v FROM kv").fetchone()
                    b.execute("BEGIN IMMEDIATE")
                    b.execute("UPDATE kv SET v=v+?", (change,))
                    b.execute("COMMIT")
                    before = "A BEGIN and SELECT v. B BEGIN IMMEDIATE, UPDATE v=v+"+str(change)+", COMMIT. A then attempts UPDATE v=v+1 in its original read transaction."
                    operation = lambda: a.execute("UPDATE kv SET v=v+1")
                elif kind == 1:
                    b.execute("BEGIN IMMEDIATE")
                    b.execute("UPDATE kv SET v=v+?", (change,))
                    before = "B BEGIN IMMEDIATE and UPDATE v=v+"+str(change)+" without COMMIT or ROLLBACK. A then attempts BEGIN IMMEDIATE."
                    operation = lambda: a.execute("BEGIN IMMEDIATE")
                else:
                    a.execute("BEGIN")
                    a.execute("SELECT v FROM kv").fetchone()
                    b.execute("BEGIN IMMEDIATE")
                    b.execute("UPDATE kv SET v=v+?", (change,))
                    b.execute("COMMIT")
                    a.execute("ROLLBACK")
                    before = "A BEGIN and SELECT v. B BEGIN IMMEDIATE, UPDATE v=v+"+str(change)+", COMMIT. A then ROLLBACK and attempts BEGIN IMMEDIATE followed by UPDATE v=v+1 and COMMIT."
                    def operation():
                        a.execute("BEGIN IMMEDIATE")
                        a.execute("UPDATE kv SET v=v+1")
                        a.execute("COMMIT")
                try:
                    operation()
                    code = 0
                except sqlite3.Error as exc:
                    code = getattr(exc, "sqlite_errorcode", None)
                    if code is None:
                        if "locked" not in str(exc).lower() or kind not in (0, 1):
                            raise
                        code = 517 if kind == 0 else 5
            finally:
                a.close()
                b.close()
        item["correct"] = f"{code:04d}"
        item["prompt"] = (f"SQLite WAL mode with busy_timeout=0 and one-row table kv(v)={initial}. "
                          f"Connection states and operations: {before} "
                          "What SQLite extended result code does A receive for its attempted operation(s)? "
                          "Return 0000 if all attempted operations succeed; otherwise the FOUR-digit decimal code.")
    else:
        namespace = r.choice(("alpha", "beta", "gamma"))
        other = "other-" + namespace
        rules = [
            {"scope":"RoleBinding","ns":namespace,"group":"","resources":["pods"],"verbs":["get","list"]},
            {"scope":"RoleBinding","ns":other,"group":"","resources":["pods/log"],"verbs":["get"]},
            {"scope":"ClusterRoleBinding","ns":"*","group":"","resources":["configmaps"],"verbs":["get","list"]},
            {"scope":"RoleBinding","ns":namespace,"group":"apps","resources":["deployments"],"verbs":["get","patch"]},
            {"scope":"ClusterRoleBinding","ns":"*","group":"","resources":["pods"],"verbs":["watch"]},
        ]
        def authorized(req):
            return any((policy["scope"]=="ClusterRoleBinding" or policy["ns"]==req["ns"])
                       and policy["group"]==req["group"]
                       and req["resource"] in policy["resources"]
                       and req["verb"] in policy["verbs"] for policy in rules)
        pool = [
            {"ns":ns,"group":group,"resource":resource,"verb":verb}
            for ns in (namespace, other)
            for group, resource in (("", "pods"), ("", "pods/log"), ("", "configmaps"),
                                    ("apps","deployments"),("","services"))
            for verb in ("get", "list", "watch", "patch")
        ]
        yes = [req for req in pool if authorized(req)]
        no = [req for req in pool if not authorized(req)]
        yes_count = r.randrange(2, 7)
        requests = r.sample(yes, yes_count) + r.sample(no, 9-yes_count)
        r.shuffle(requests)
        item["correct"] = str(sum(authorized(req) for req in requests))
        item["prompt"] = (
            f"Kubernetes RBAC for serviceaccount {namespace}/runner. All following bindings target it. "
            "RoleBindings apply only to their namespace, ClusterRoleBindings are cluster-wide. "
            "Match apiGroup, resource/subresource and verb exactly; no wildcards. "
            f"Bindings: {json.dumps(rules,separators=(',',':'))}. "
            f"Nine authorization requests: {json.dumps(requests,separators=(',',':'))}. "
            "How many are allowed?"
        )


def load_exact(seed=17, variants=4, selected="all"):
    items = load_ladder(seed=seed, variants=variants, selected=selected)
    for item in items:
        if item["level"] == 1:
            _better_l1(item, seed)
        _harder_cases(item, seed)
        rebalance(item, seed)
        family = item["concept"].rsplit("-v", 1)[0]
        answer_format = FORMATS.get(family, "integer")
        if family == "sqlite-wal-snapshots" and item["level"] == 3:
            answer_format = "error_code"
        item["answer_format"] = item.get("answer_format", answer_format)
        item["response_mode"] = "exact"
        item["calibration_version"] = "exact-v0.4"
        del item["wrong"]
    return items


def normalize_exact(value, answer_format):
    import re
    if not isinstance(value, str):
        return None
    value = value.strip()
    if answer_format == "bitstring":
        return value if re.fullmatch(r"[01]{2,16}", value) else None
    if answer_format == "integer":
        return str(int(value)) if re.fullmatch(r"[+-]?\d{1,15}", value) else None
    if answer_format == "error_code":
        return value.zfill(4) if re.fullmatch(r"\d{1,4}", value) else None
    if answer_format == "interface":
        return value.lower() if re.fullmatch(r"if\d{2}", value, re.I) else None
    if answer_format == "text2":
        return value if re.fullmatch(r"[a-z]{2}", value) else None
    if answer_format == "hex4":
        token = value[2:] if value.lower().startswith("0x") else value
        return token.upper().zfill(4) if re.fullmatch(r"[0-9a-fA-F]{1,4}", token) else None
    if answer_format == "octal":
        token = value.lower()
        token = token[2:] if token.startswith("0o") else token
        return f"0{int(token, 8):03o}" if re.fullmatch(r"[0-7]{3,4}", token) and int(token, 8) <= 0o777 else None
    raise ValueError("Unknown format: " + str(answer_format))


def parse_exact_response(content, item):
    import re
    if isinstance(content, list):
        content = " ".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
    if not isinstance(content, str) or not content.strip():
        return None
    raw = content.strip()
    first = raw.splitlines()[0].strip()
    match = re.fullmatch(r"(?:(?:final|answer)\s*:\s*)?(\S+)", first, re.I)
    if match:
        parsed = normalize_exact(match.group(1), item["answer_format"])
        if parsed is not None:
            return parsed
    finals = re.findall(r"(?im)^\s*FINAL\s*:\s*(\S+)\s*$", raw)
    if finals:
        return normalize_exact(finals[-1], item["answer_format"])
    return None
