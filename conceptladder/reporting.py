import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .cli import grade, items_for_run, load_run, materialize, parse_answer


def inspect_runs(paths, reparse_raw=True):
    entries = []
    buckets = defaultdict(list)
    suite_shape = None
    for path in paths:
        run = load_run(path)
        items = items_for_run(run)
        shape = (run.get("suite", "classic"), len(items), tuple(sorted({x["pack"] for x in items})))
        if suite_shape is None:
            suite_shape = shape
        elif shape != suite_shape:
            raise ValueError("Calibration runs must use the same suite, pack selection, and question count")
        if reparse_raw:
            item_by_id = {item["id"]:item for item in items}
            run = dict(run)
            run["responses"] = [dict(row) for row in run["responses"]]
            for row in run["responses"]:
                if row.get("prediction") is None and row.get("raw_response"):
                    repaired = parse_answer(row["raw_response"], item_by_id[row["id"]], run.get("answer_seed",run["seed"]))
                    if repaired:
                        row["prediction"] = repaired
                        row["error"] = None
        stats = grade(run, items)
        correct_by_level = defaultdict(lambda: [0, 0])
        correct_by_family = defaultdict(lambda: [0, 0])
        answers = defaultdict(lambda: [0, 0])
        preds = {r["id"]: r["prediction"] for r in run["responses"]}
        for item in items:
            yes = int(stats["pass"][item["id"]])
            correct_by_level[str(item["level"])][0] += yes
            correct_by_level[str(item["level"])][1] += 1
            family = item["concept"].rsplit("-v", 1)[0] if item.get("hard") else item["concept"]
            correct_by_family[family][0] += yes
            correct_by_family[family][1] += 1
            answer = materialize(item, run.get("answer_seed", run["seed"]))[1]
            if item.get("response_mode") != "exact":
                answers[answer][0] += int(preds[item["id"]] == answer)
                answers[answer][1] += 1
        entry = {
            "path": str(path),
            "model": run["model"],
            "suite": run.get("suite", "classic"),
            "question_seed": run["seed"],
            "answer_seed": run.get("answer_seed", run["seed"]),
            "variants": run.get("variants", 4),
            "dataset_sha256": run["dataset_sha256"],
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": stats["accuracy"],
            "invalid": stats["invalid"],
            "mean_contiguous_depth": stats["mean_contiguous_depth"],
            "levels": {k: {"correct": a, "total": b} for k, (a, b) in sorted(correct_by_level.items())},
            "families": {k: {"correct": a, "total": b} for k, (a, b) in sorted(correct_by_family.items())},
            "answer_positions": {k: {"correct": a, "total": b} for k, (a, b) in sorted(answers.items())},
            "packs": stats["packs"],
        }
        entries.append(entry)
        buckets[run["model"]].append(entry)
    per_model = {}
    for model, values in sorted(buckets.items()):
        same_questions = defaultdict(list)
        same_order = defaultdict(list)
        for e in values:
            same_questions[e["dataset_sha256"]].append(e)
            same_order[e["answer_seed"]].append(e)
        ranges = []
        for rows in same_questions.values():
            if len(rows) > 1 and len({r["answer_seed"] for r in rows}) > 1:
                ranges.append({
                    "question_seed": rows[0]["question_seed"],
                    "answer_seeds": [x["answer_seed"] for x in rows],
                    "score_range_pp": round(100 * (max(x["accuracy"] for x in rows) - min(x["accuracy"] for x in rows)), 3),
                })
        per_model[model] = {
            "runs": len(values),
            "accuracy_min": min(v["accuracy"] for v in values),
            "accuracy_max": max(v["accuracy"] for v in values),
            "accuracy_mean": round(sum(v["accuracy"] for v in values) / len(values), 6),
            "level_accuracy": {
                level: round(sum(v["levels"][level]["correct"] for v in values) /
                             sum(v["levels"][level]["total"] for v in values), 6)
                for level in sorted(values[0]["levels"])
            },
            "option_order_sensitivity": ranges,
        }
    pairs = []
    by_form = defaultdict(list)
    for e in entries:
        by_form[(e["suite"],e["dataset_sha256"],e["question_seed"],e["answer_seed"])].append(e)
    for entries_for_form in by_form.values():
        for a,b in combinations(entries_for_form,2):
            if a["model"] == b["model"]:
                continue
            pairs.append({
                "suite":a["suite"],"question_seed":a["question_seed"],"answer_seed":a["answer_seed"],
                "first_model":a["model"],"second_model":b["model"],
                "first_correct":a["correct"],"second_correct":b["correct"],
                "second_minus_first_pp":round(100*(b["accuracy"]-a["accuracy"]),3),
            })
    return {
        "format":"conceptladder-calibration-v1",
        "source_runs":len(entries),
        "models":per_model,
        "forms":entries,
        "matched_pairs":pairs,
        "interpretation":"These forms share templates and are not statistically independent. Position sensitivity is measured only when question fingerprints match. No claim of validated psychometric depth is implied.",
    }
