from collections import Counter

from .hardcases import rng_for
from .hardcases.database import BUILDERS as DATABASE
from .hardcases.network import BUILDERS as NETWORK
from .hardcases.security import BUILDERS as SECURITY
from .hardcases.systems import BUILDERS as SYSTEMS

BUILDERS = NETWORK + DATABASE + SYSTEMS + SECURITY
PACKS = ("net-hard", "db-hard", "sys-hard", "security-hard")


def load_hard(seed=17, variants=4, selected="all"):
    if not (1 <= variants <= 32):
        raise ValueError("variants must be between 1 and 32")
    if selected == "all":
        chosen = set(PACKS)
    else:
        chosen = {x.strip() for x in selected.split(",") if x.strip()}
        if not chosen or chosen - set(PACKS):
            raise ValueError("Unknown hard pack(s): " + ", ".join(sorted(chosen - set(PACKS))))
    items=[]
    ids=set()
    for builder in BUILDERS:
        for variant in range(1, variants+1):
            rng=rng_for(seed,builder.__name__,variant)
            pack, concept, source, questions=builder(rng)
            if pack not in chosen:
                continue
            if len(questions)!=4:
                raise ValueError(f"{concept} should have 4 levels")
            for level, (prompt,correct,wrong) in enumerate(questions,1):
                concept_id=f"{concept}-v{variant:02d}"
                item_id=f"{pack}/{concept_id}/L{level}"
                if item_id in ids:
                    raise ValueError(f"Duplicate item: {item_id}")
                ids.add(item_id)
                correct=str(correct)
                wrong=list(map(str,wrong))
                if not prompt.strip() or len(wrong)!=3 or len(set([correct]+wrong))!=4 or any(len(s)!=len(correct) for s in wrong):
                    raise ValueError(f"Invalid answers: {item_id}: {correct}, {wrong}")
                items.append({
                    "id":item_id,"pack":pack,"concept":concept_id,"level":level,
                    "prompt":prompt,"correct":correct,"wrong":wrong,"source":source,
                    "hard":True
                })
    if not items:
        raise ValueError("No hard questions available")
    return items
