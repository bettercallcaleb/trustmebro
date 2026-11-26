import hashlib
import os
import sqlite3
import tempfile
from pathlib import Path

from .hardcases import alternatives, numeric, rng_for
from .hardgen import load_hard


def first_level(family, r):
    if family == "tcp-reassembly":
        start = r.choice((100, 200, 500, 1000))
        length = r.choice((10, 15, 20, 25, 30))
        prompt = f"A TCP receiver next expects sequence number {start}. One in-order TCP segment arrives with exactly {length} payload bytes and no SYN/FIN. What cumulative ACK number should it send?"
        return (prompt, *numeric(start + length))
    if family == "tcp-send-window":
        cwnd = r.choice((4000, 6000, 8000))
        rwnd = r.choice((2000, 3000))
        prompt = f"A TCP sender has congestion window {cwnd} bytes, advertised receive window {rwnd} bytes, and zero outstanding data. Ignore pacing, Nagle, and SWS. How many NEW payload bytes can it send now?"
        return (prompt, *numeric(rwnd, delta=1000))
    if family == "ipv4-fragment-offset":
        payload = r.choice((2000, 2200, 2400, 2600))
        prompt = f"An IPv4 datagram has a 20-byte header and {payload} bytes of payload. A router forwards it across MTU=1500 with DF=0 and no IP options. What is the number of fragments produced? (Each fragment gets its own header.)"
        return (prompt, *numeric(2))
    if family == "dns-ttl-chain":
        ttl = r.choice((40, 50, 60, 70, 80))
        elapsed = r.choice((10, 20))
        prompt = f"A DNS A record was cached at t=0 with TTL={ttl} seconds. No refresh or eviction occurs. At t={elapsed} seconds, how many seconds of TTL remain?"
        return (prompt, *numeric(ttl - elapsed, delta=10))
    if family == "sqlite-wal-snapshots":
        initial = r.choice((10, 20, 30, 40, 50))
        delta = r.choice((3, 5, 7))
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE kv(v INTEGER)")
            conn.execute("INSERT INTO kv VALUES (?)", (initial,))
            conn.execute("UPDATE kv SET v=v+?", (delta,))
            expected = conn.execute("SELECT v FROM kv").fetchone()[0]
        prompt = f"A SQLite table kv(v) starts with one row v={initial}. Connection A successfully updates v=v+{delta} and COMMITs. Connection B then starts a NEW read transaction and reads v. What integer does B see?"
        return (prompt, *numeric(expected))
    if family == "sqlite-window-frames":
        scores = r.sample((3, 5, 7, 9, 11), 3)
        selected = r.choice((1, 2, 3))
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE scores(id INTEGER PRIMARY KEY,score INTEGER)")
            conn.executemany("INSERT INTO scores VALUES (?,?)", list(enumerate(scores, 1)))
            expected = conn.execute("SELECT n FROM (SELECT id,ROW_NUMBER() OVER (ORDER BY score DESC) AS n FROM scores) WHERE id=?", (selected,)).fetchone()[0]
        prompt = ("SQLite scores(id,score) has exactly three rows: " + ", ".join(f"({i},{v})" for i, v in enumerate(scores, 1)) + ". Execute: SELECT n FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY score DESC) AS n FROM scores) WHERE id=" + str(selected) + "; What integer is returned?")
        return (prompt, *numeric(expected))
    if family == "sqlite-left-join-null":
        n = r.choice((2, 3))
        counts = [r.choice((1, 2)), 0] + ([1] if n == 3 else [])
        children = [(i+1, j+1) for i, count in enumerate(counts) for j in range(count)]
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE p(id INTEGER PRIMARY KEY)")
            conn.execute("CREATE TABLE c(pid INTEGER, item INTEGER)")
            conn.executemany("INSERT INTO p VALUES (?)", [(i,) for i in range(1, n+1)])
            conn.executemany("INSERT INTO c VALUES (?,?)", children)
            expected = conn.execute("SELECT COUNT(*) FROM p LEFT JOIN c ON p.id=c.pid").fetchone()[0]
        prompt = f"SQLite: parent p(id) rows are {list(range(1,n+1))}; child c(pid,item) rows are {children}. What integer does SELECT COUNT(*) FROM p LEFT JOIN c ON p.id=c.pid return?"
        return (prompt, *numeric(expected))
    if family == "posix-file-offsets":
        value = "".join(r.sample("abcdefghijkmnpqrstuvwxyz", 8))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bytes"
            path.write_text(value, encoding="ascii")
            fd = os.open(path, os.O_RDONLY)
            try:
                os.read(fd, 2)
                expected = os.read(fd, 2).decode("ascii")
            finally:
                os.close(fd)
        wrong = [value[i:i+2] for i in (0, 1, 3, 4, 5, 6)]
        prompt = f"A POSIX file contains the exact eight ASCII bytes '{value}'. fd=open(file,O_RDONLY); read(fd,2); answer=read(fd,2). What two-character string is in answer?"
        return (prompt, *alternatives(expected,wrong))
    if family == "unix-mode-bit-transforms":
        mask = r.choice((0o022, 0o027, 0o077, 0o002))
        expected = 0o666 & ~mask
        prompt = f"A POSIX process with umask 0{mask:03o} creates a NEW regular file with requested permission mode 0666. Ignore default ACLs. What resulting permission mode does the file have? Use four octal characters."
        value = f"0{expected:03o}"
        wrong = [f"0{(expected ^ bit)&0o777:03o}" for bit in (0o004, 0o040, 0o020, 0o002, 0o200)]
        return (prompt, *alternatives(value,wrong))
    if family == "jwt-boundary-validation":
        now = 100
        expiry = [r.choice((90, 95)), 100, r.choice((110, 120))]
        if r.randrange(2):
            expiry.append(r.choice((80, 130)))
        expected = sum(t > now for t in expiry)
        prompt = f"JWT NumericDate now={now}. Signatures verified; only exp is checked. Accept a token when now < exp (strict). The tokens have exp values {expiry}. How many are accepted?"
        return (prompt, *numeric(expected))
    if family == "kubernetes-rbac-scope":
        ns = r.choice(("alpha", "beta", "gamma"))
        other = "other-" + ns
        requests = [
            ("get", "pods", ns),
            ("list", "pods", ns),
            ("get", "pods", other),
            ("get", "pods/log", ns),
        ]
        r.shuffle(requests)
        expected = 1
        prompt = f"Kubernetes RoleBinding grants serviceaccount {ns}/runner ONLY the verb get on resource pods in namespace {ns}. No other permissions. Requests (verb,resource,namespace): {requests}. How many requests are authorized? Resource subresources and namespaces must match exactly."
        return (prompt, *numeric(expected))
    return None


def load_ladder(seed=17, variants=4, selected="all"):
    items = load_hard(seed, variants, selected)
    for item in items:
        item["calibration_version"] = "ladder-v0.3"
        if item["level"] != 1:
            continue
        family = item["concept"].rsplit("-v",1)[0]
        r = rng_for(seed, "ladder-v0.3:"+family, item["concept"])
        replacement = first_level(family, r)
        if replacement is None:
            continue
        prompt, correct, wrong = replacement
        item["prompt"] = prompt
        item["correct"] = str(correct)
        item["wrong"] = list(map(str, wrong))
        if len(set([item["correct"]] + item["wrong"])) != 4 or any(len(x) != len(item["correct"]) for x in item["wrong"]):
            raise ValueError(f"Bad choices: {item['id']}")
    return items
