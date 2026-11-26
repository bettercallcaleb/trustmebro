from collections import Counter, defaultdict

from .cli import fingerprint, grade, materialize
from .exact import load_exact


def blind_audit(train_seeds=(17, 41), test_seeds=(91, 123, 777), variants=4, packs="all"):
    train = tuple(int(x) for x in train_seeds)
    test = tuple(int(x) for x in test_seeds)
    if not train or not test or set(train) & set(test):
        raise ValueError("Train and test seeds must be nonempty and disjoint")
    counts = defaultdict(Counter)
    for seed in train:
        for item in load_exact(seed, variants, packs):
            family = item["concept"].rsplit("-v", 1)[0]
            counts[(family, item["level"])][item["correct"]] += 1
    guesses = {key: sorted(ct.items(), key=lambda x: (-x[1], x[0]))[0][0]
               for key, ct in counts.items()}
    results = []
    for seed in test:
        items = load_exact(seed, variants, packs)
        choices = []
        for item in items:
            family = item["concept"].rsplit("-v", 1)[0]
            choices.append({"id": item["id"], "prediction": guesses[(family, item["level"])]})
            prompt, _ = materialize(item, seed)
            if any(line.startswith(("A. ", "B. ", "C. ", "D. ")) for line in prompt.splitlines()):
                raise ValueError(f"Multiple-choice options leaked into exact question: {item['id']}")
        fake = {"dataset_sha256": fingerprint(items), "seed": seed, "responses": choices}
        score = grade(fake, items)
        results.append({
            "seed": seed, "correct": score["correct"],
            "total": score["total"], "accuracy": score["accuracy"],
            "mean_contiguous_depth": score["mean_contiguous_depth"],
        })
    totals = sum(x["total"] for x in results)
    hits = sum(x["correct"] for x in results)
    return {
        "suite": "exact",
        "baseline": "Most frequent answer per concept family and level, learned from training seeds without ever reading prompts",
        "train_seeds": list(train), "test_seeds": list(test),
        "variants": variants, "packs": packs,
        "results": results,
        "aggregate_accuracy": round(hits / totals, 6),
        "aggregate_correct": hits,
        "aggregate_total": totals,
        "limits": "This attacks one simple shortcut, not all forms of dataset leakage or memorization.",
    }
