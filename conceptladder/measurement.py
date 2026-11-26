import argparse
import collections
import hashlib
import importlib
import json
import os
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

from .cli import load_suite, fingerprint
from .exact import normalize_exact

VERSION = "measurement-v0.5"
REPORT_VERSION = "measurement-report-v0.5.1"
KNOWLEDGE_SYSTEM = (
    "Solve the technical problem. You may reason and explain before giving your answer. "
    "The last nonempty line should be FINAL: followed by the requested value. "
    "This response protocol overrides requests in the question to output only the value, "
    "but does not change its required value representation."
)
LABEL = re.compile(r"(?im)^[ \t]*(?:FINAL|ANSWER)[ \t]*:[ \t]*(\S+)[ \t]*$")
LABEL_START = re.compile(r"(?im)^[ \t]*(?:FINAL|ANSWER)[ \t]*:")

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def representation(fmt, width):
    return {
        "integer": r"-?(?:0|[1-9][0-9]{0,14})",
        "bitstring": rf"[01]{{{width}}}",
        "interface": r"if[0-9]{2}",
        "text2": r"[a-z]{2}",
        "hex4": r"[0-9A-F]{4}",
        "octal": r"0[0-7]{3}",
        "error_code": r"[0-9]{4}",
    }[fmt]

def unwrap(s):
    s = s.strip()
    tick = chr(96)
    match = re.fullmatch(re.escape(tick * 3) + r"(?:[a-zA-Z0-9_-]+)?[ \t]*\n(.*?)\n" + re.escape(tick * 3), s, re.S)
    if match:
        s = match.group(1).strip()
    if len(s) > 2 and s.startswith(tick) and s.endswith(tick) and tick not in s[1:-1]:
        s = s[1:-1].strip()
    return s

def extract(content, fmt):
    s = unwrap(content)
    labels = list(LABEL.finditer(s))
    if LABEL_START.search(s):
        if len(labels) != 1 or len(LABEL_START.findall(s)) != 1:
            return None
        value = unwrap(labels[0].group(1))
    else:
        value = s
    return normalize_exact(value, fmt)

def knowledge_grade(item, content, finish_reason=None):
    fmt = item["answer_format"]
    gold = normalize_exact(item["correct"], fmt)
    width = len(gold) if fmt == "bitstring" else 0
    s = content.strip()
    pred = extract(s, fmt)
    labels = list(LABEL.finditer(s))
    final = bool(len(labels) == 1 and len(LABEL_START.findall(s)) == 1
                 and labels[0].end() == len(s)
                 and re.fullmatch(r"FINAL: " + representation(fmt, width), labels[0].group(0)))
    return {
        "prediction": pred,
        "answer_available": pred is not None,
        "semantic_correct": None if pred is None else pred == gold,
        "strict_final_format": final,
        "truncated": None if finish_reason is None else finish_reason == "length",
        "empty": not s,
    }

def mean(values):
    a = list(values)
    return sum(a) / len(a) if a else None

def knowledge_metrics(rows, expected_n):
    if expected_n < 1 or len(rows) > expected_n:
        raise ValueError("Invalid expected question count")
    correct = sum(r["semantic_correct"] is True for r in rows)
    wrong = sum(r["semantic_correct"] is False for r in rows)
    missing = expected_n - len(rows)
    unknown = expected_n - correct - wrong
    strict = sum(r["strict_final_format"] for r in rows)
    joint = sum(r["semantic_correct"] is True and r["strict_final_format"] for r in rows)
    finish_known = sum(r["truncated"] is not None for r in rows)
    truncated = sum(r["truncated"] is True for r in rows)
    tokens = [r.get("usage", {}).get("completion_tokens") for r in rows]
    times = [r.get("latency_s") for r in rows]
    token_total = sum(tokens) if len(rows) == expected_n and all(type(v) is int and v >= 0 for v in tokens) else None
    time_total = sum(times) if len(rows) == expected_n and all(type(v) in (int, float) and v >= 0 for v in times) else None
    out = {
        "n": len(rows),
        "expected_n": expected_n,
        "not_run_count": missing,
        "confirmed_correct_count": correct,
        "confirmed_wrong_count": wrong,
        "unknown_count": unknown,
        "unknown_answer_count": unknown - missing,
        "confirmed_correct_rate": correct / expected_n,
        "confirmed_wrong_rate": wrong / expected_n,
        "unknown_rate": unknown / expected_n,
        "answer_coverage": (correct + wrong) / expected_n,
        "accuracy_lower_bound": correct / expected_n,
        "accuracy_upper_bound": (correct + unknown) / expected_n,
        "strict_final_format": strict / expected_n,
        "joint_accuracy": joint / expected_n,
        "joint_success_count": joint,
        "truncation_rate": truncated / expected_n,
        "truncation_upper_bound": (truncated + expected_n - finish_known) / expected_n,
        "finish_reason_coverage": finish_known / expected_n,
        "empty_rate": sum(r["empty"] for r in rows) / expected_n,
        "total_completion_tokens": token_total,
        "total_latency_s": time_total,
        "tokens_per_success": token_total / joint if token_total is not None and joint else None,
        "time_per_success_s": time_total / joint if time_total is not None and joint else None,
    }
    return out

def knowledge_report(rows, items):
    indexed = {i["id"]: i for i in items}
    out = knowledge_metrics(rows, len(items))
    by_root = collections.defaultdict(dict)
    by_level = collections.defaultdict(list)
    level_counts = collections.Counter(i["level"] for i in items)
    for i in items:
        by_root[(i["pack"], i["concept"])][i["level"]] = None
    for r in rows:
        i = indexed[r["id"]]
        by_root[(i["pack"], i["concept"])][i["level"]] = r["semantic_correct"]
        by_level[i["level"]].append(r)
    depths = []
    for levels in by_root.values():
        low = high = 0
        for level in range(1, 5):
            if levels.get(level) is not True:
                break
            low += 1
        for level in range(1, 5):
            if levels.get(level) is False:
                break
            high += 1
        depths.append((low, high))
    out.update(contiguous_depth_lower=mean(d[0] for d in depths),
               contiguous_depth_upper=mean(d[1] for d in depths),
               roots=len(depths),
               levels={str(k): knowledge_metrics(by_level[k], n) for k, n in sorted(level_counts.items())})
    return out

def official(root):
    root = Path(root).resolve()
    folder = root / "instruction_following_eval"
    files = ["evaluation_lib.py", "instructions.py", "instructions_registry.py", "instructions_util.py", "data/input_data.jsonl"]
    hashes = {f: sha(folder / f) for f in files}
    sys.path.insert(0, str(root))
    try:
        from instruction_following_eval import evaluation_lib
        from langdetect import DetectorFactory
    except ImportError as e:
        raise RuntimeError("Install upstream IFEval requirements and set --ifeval-root to its checkout parent") from e
    if Path(evaluation_lib.__file__).resolve() != folder / "evaluation_lib.py":
        raise RuntimeError("Different IFEval module already imported")
    DetectorFactory.seed = 0
    source = evaluation_lib.read_prompt_list(str(folder / "data/input_data.jsonl"))
    if len(source) != 541 or len({i.key for i in source}) != 541:
        raise ValueError("Expected official 541-prompt IFEval dataset")
    return evaluation_lib, source, hashes

def ifeval_items(root, limit=None):
    ev, source, hashes = official(root)
    if limit is not None:
        if not 1 <= limit <= len(source):
            raise ValueError("IFEval limit must be between 1 and 541")
        source = sorted(source, key=lambda x: hashlib.sha256(
            ("gguf-healer-validation-v1|" + str(x.key)).encode()).hexdigest())[:limit]
    items = [{"id": str(i.key), "prompt": i.prompt, "instruction_ids": i.instruction_id_list,
              "kwargs": i.kwargs} for i in source]
    return ev, source, items, hashes

def ifeval_grade(ev, item, content):
    random.seed(137)
    strict = ev.test_instruction_following_strict(item, {item.prompt: content})
    random.seed(137)
    loose = ev.test_instruction_following_loose(item, {item.prompt: content})
    return {"strict_prompt": bool(strict.follow_all_instructions),
            "loose_prompt": bool(loose.follow_all_instructions),
            "strict_instructions": list(strict.follow_instruction_list),
            "loose_instructions": list(loose.follow_instruction_list),
            "instruction_ids": list(item.instruction_id_list)}

def ifeval_report(rows):
    groups = collections.defaultdict(lambda: {"strict": [], "loose": []})
    for r in rows:
        for k, s, l in zip(r["instruction_ids"], r["strict_instructions"], r["loose_instructions"]):
            groups[k]["strict"].append(s)
            groups[k]["loose"].append(l)
    return {"n": len(rows), "strict_prompt": mean(r["strict_prompt"] for r in rows),
            "loose_prompt": mean(r["loose_prompt"] for r in rows),
            "strict_instruction": mean(x for r in rows for x in r["strict_instructions"]),
            "loose_instruction": mean(x for r in rows for x in r["loose_instructions"]),
            "truncation_rate": mean(r["finish_reason"] == "length" for r in rows if r.get("finish_reason") is not None),
            "by_instruction": {k: {"n": len(v["strict"]), "strict": mean(v["strict"]),
                                   "loose": mean(v["loose"])} for k, v in sorted(groups.items())}}

def prepare(args):
    ev = None
    source = None
    hashes = None
    if args.track == "knowledge":
        items = load_suite("exact", args.packs, args.seed, args.variants)
    else:
        if not args.ifeval_root:
            raise ValueError("--ifeval-root is required for IFEval")
        ev, source, items, hashes = ifeval_items(args.ifeval_root, args.limit)
    return items, ev, source, hashes

def read_rows(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate response IDs")
    return rows

def grade_rows(track, items, rows, ev=None, source=None, partial=False):
    by_id = {i["id"]: i for i in items}
    got = {r["id"] for r in rows}
    if not got or not got <= set(by_id) or (not partial and got != set(by_id)):
        raise ValueError("Missing or unexpected response IDs")
    official_by_id = {str(i.key): i for i in source} if source else {}
    graded = []
    for r in rows:
        c = r["content"]
        if not isinstance(c, str):
            raise ValueError("Non-string response")
        a = knowledge_grade(by_id[r["id"]], c, r.get("finish_reason")) if track == "knowledge" else ifeval_grade(ev, official_by_id[r["id"]], c)
        graded.append({**r, **a})
    out = knowledge_report(graded, items) if track == "knowledge" else ifeval_report(graded)
    return {"track": track, "expected_n": len(items), "complete": len(rows) == len(items),
            "dataset_sha256": fingerprint(items), **out}

def save(path, obj):
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    os.replace(tmp, p)

def request(url, model, messages, max_tokens, timeout, api_key):
    endpoint = url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    payload = {"model": model, "temperature": 0, "max_tokens": max_tokens, "messages": messages}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    q = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers=headers)
    t = time.monotonic()
    with urllib.request.urlopen(q, timeout=timeout) as f:
        r = json.load(f)
    ch = r["choices"][0]
    msg = ch["message"]
    return {"content": msg.get("content") or "", "reasoning_content": msg.get("reasoning_content"),
            "finish_reason": ch.get("finish_reason"), "usage": r.get("usage", {}),
            "latency_s": time.monotonic() - t, "timings": r.get("timings", {})}

def main(argv=None):
    p = argparse.ArgumentParser(prog="conceptladder measure")
    p.add_argument("action", choices=["run", "score"])
    p.add_argument("--track", choices=["knowledge", "ifeval"], required=True)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--variants", type=int, default=4)
    p.add_argument("--packs", default="all")
    p.add_argument("--ifeval-root")
    p.add_argument("--limit", type=int)
    p.add_argument("--out", required=True, help="Raw JSONL path; manifest and report are adjacent")
    p.add_argument("--model")
    p.add_argument("--url", default="http://127.0.0.1:8080/v1")
    p.add_argument("--max-tokens", type=int, default=2048)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--profile", default="unspecified", help="Describe the engine, chat template, reasoning and decoding settings")
    p.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", ""))
    p.add_argument("--partial", action="store_true")
    a = p.parse_args(argv)
    if a.track == "knowledge" and a.limit is not None:
        p.error("--limit is only for IFEval")
    items, ev, source, hashes = prepare(a)
    path = Path(a.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = path.with_suffix(path.suffix + ".manifest.json")
    report = path.with_suffix(path.suffix + ".report.json")
    if a.action == "run":
        if not a.model or a.max_tokens < 1:
            p.error("--model and positive --max-tokens required")
        manifest = {"version": VERSION, "track": a.track, "model": a.model, "profile": a.profile,
                    "dataset_sha256": fingerprint(items), "ifeval_source_hashes": hashes,
                    "max_tokens": a.max_tokens, "temperature": 0,
                    "system": KNOWLEDGE_SYSTEM if a.track == "knowledge" else None}
        if meta.exists():
            if json.loads(meta.read_text()) != manifest:
                raise ValueError("Run protocol differs from manifest")
        elif path.exists():
            raise ValueError("Existing responses without a manifest")
        else:
            save(meta, manifest)
        done = {r["id"] for r in read_rows(path)} if path.exists() else set()
        if not done <= {i["id"] for i in items}:
            raise ValueError("Unexpected response IDs")
        for i in items:
            if i["id"] in done:
                continue
            msgs = ([{"role": "system", "content": KNOWLEDGE_SYSTEM}] if a.track == "knowledge" else [])
            msgs.append({"role": "user", "content": i["prompt"]})
            row = {"id": i["id"], **request(a.url, a.model, msgs, a.max_tokens, a.timeout, a.api_key)}
            with path.open("a") as f:
                f.write(json.dumps(row) + "\n")
            done.add(i["id"])
            if len(done) % 12 == 0 or len(done) == len(items):
                print(a.track, a.model, len(done), len(items), flush=True)
    elif meta.exists():
        m = json.loads(meta.read_text())
        if m["dataset_sha256"] != fingerprint(items) or m.get("ifeval_source_hashes") != hashes or m.get("track") != a.track:
            raise ValueError("Scoring protocol differs from manifest")
    rows = read_rows(path)
    result = grade_rows(a.track, items, rows, ev, source, a.partial)
    result.update(version=VERSION, report_version=REPORT_VERSION, ifeval_source_hashes=hashes)
    save(report, result)
    print(json.dumps(result, indent=2), flush=True)

if __name__ == "__main__":
    main()
