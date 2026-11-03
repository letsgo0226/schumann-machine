"""SAA-013: bounded offline experiment. Standard library only."""
import hashlib, itertools, json, os, tempfile
from pathlib import Path

def models():
    for bits in itertools.product((False, True), repeat=7):
        p=bits[:2]; edges=bits[2:6]; start=int(bits[6])
        def edge(i,j): return edges[2*i+j]
        a1=p[start]
        a2=all(any(edge(i,j) for j in range(2)) for i in range(2))
        a3=all(not (p[i] and edge(i,j)) or p[j] for i in range(2) for j in range(2))
        yield (a1,a2,a3)

def report():
    vals=list(models())
    return {"model_count":len(vals),"scope":"all labeled 2-state models",
            "axiom_true_counts":[sum(v[i] for v in vals) for i in range(3)],
            "epistemic_status":"bounded_model_check_only"}

def digest(r):
    return hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()

def load(path):
    p=Path(path)
    if not p.exists(): return {"next_round":0,"records":[]}
    obj=json.loads(p.read_text())
    if obj["next_round"]!=len(obj["records"]): raise ValueError("invalid checkpoint")
    for i,rec in enumerate(obj["records"]):
        if rec["round"]!=i or rec["sha256"]!=digest(rec["result"]):
            raise ValueError("checkpoint verification failed")
    return obj

def run(path):
    p=Path(path); obj=load(p); r=report()
    obj["records"].append({"round":obj["next_round"],"result":r,"sha256":digest(r)})
    obj["next_round"]+=1
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=str(p.parent))
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(obj,f,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print(json.dumps({"next_round":obj["next_round"],"model_count":r["model_count"]}))

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint",default="research/checkpoint.json")
    args=ap.parse_args()
    run(args.checkpoint)
