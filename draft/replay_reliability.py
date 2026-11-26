import argparse
import json
from pathlib import Path
from reliability import replay,report,VERSION
from trustmebro import save,digest,file_hash

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--run-dir",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    src=Path(args.run_dir)
    plan=json.loads((src/"plan.json").read_text())
    if digest(plan["manifest"])!=plan["manifest_sha256"]:raise ValueError("Manifest hash mismatch")
    tasks=plan["manifest"]["tasks"]
    out={"scorer":VERSION,"manifest_sha256":plan["manifest_sha256"],"models":{}}
    for f in sorted(src.glob("*-raw.json")):
        record=json.loads(f.read_text())
        if record["manifest_sha256"]!=plan["manifest_sha256"]:raise ValueError("Run manifest mismatch")
        rows=replay(tasks,record["rows"],record["mode"],record["budget"])
        def group(items):
            ids={t["id"] for t in items}
            return report([r for r in rows if r["id"] in ids],len(ids))
        out["models"][record["model"]]={"raw_file_sha256":file_hash(f)["sha256"],"overall":group(tasks),"levels":{str(l):group([t for t in tasks if t["level"]==l]) for l in range(1,5)},"families":{name:group([t for t in tasks if t["family"]==name]) for name in sorted({t["family"] for t in tasks})},"diagnostics":[{"id":r["id"],"grade":r.get("grade"),"legacy_grade":r.get("legacy_grade")} for r in rows]}
    save(args.out,out)
if __name__=="__main__":main()
