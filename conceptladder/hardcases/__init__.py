import hashlib
import random


def rng_for(seed, family, variant):
    digest = hashlib.sha256(f"{seed}:{family}:{variant}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def alternatives(answer, candidates):
    answer = str(answer)
    distinct = []
    for value in candidates:
        value = str(value)
        if value != answer and value not in distinct:
            distinct.append(value)
    if len(distinct) < 3:
        raise ValueError(f"Too few distractors for {answer}: {distinct}")
    return answer, distinct[:3]


def numeric(answer, delta=1):
    value = int(answer)
    width = len(str(value))
    offsets = [delta, -delta, 2 * delta, -2 * delta, 3 * delta, -3 * delta, 4 * delta, -4 * delta, 5 * delta, -5 * delta]
    candidates = [value + x for x in offsets if value + x >= 0 and len(str(value + x)) == width]
    if len(set(candidates)) < 3:
        candidates += [value + x for x in range(1, 16) if len(str(value + x)) == width]
    return alternatives(value, candidates)


def code(answer, candidates):
    return alternatives(answer, candidates)
