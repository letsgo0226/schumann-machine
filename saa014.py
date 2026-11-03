"""SAA-014: bounded, non-repeating finite-model research with resumable checkpoints."""
import argparse
import hashlib
import itertools
import json
import os
import tempfile
from pathlib import Path

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def examine(n):
    if n not in (2,3): raise ValueError("only 2 or 3 states supported")
    counts=[0,0,0]
    total=0
    for bits in itertools.product((False,True),repeat=n+n*n+1):
        p=bits[:n]
        edges=bits[n:n+n*n]
        start=int(bits[-1])
        a=(p[start],
           all(any(edges[i*n+j] for j in range(n)) for i in range(n)),
           all(not(p[i] and edges[i*n+j]) or p[j] for i in range(n) for j in range(n)))
        total+=1
        for k,v in enumerate(a): counts[k]+=int(v)
    return {"states":n,"model_count":total,"axiom_true_counts":counts,"scope":"all labeled finite models","epistemic_status":"bounded_model_check_only"}

def load(path):
    p=Path(path)
    if not p.exists(): return {"schema":1,"next_round":0,"records":[]}
    obj=json.loads(p.read_text())
    if obj.get("next_round")!=len(obj.get("records",[])): raise ValueError("invalid checkpoint length")
    for i,r in enumerate(obj["records"]):
        if r.get("round")!=i: raise ValueError("nonsequential checkpoint")
        old=hashlib.sha256(json.dumps(r["result"],sort_keys=True).encode()).hexdigest()
        if r.get("sha256") not in (old,digest(r["result"])): raise ValueError("checkpoint digest mismatch")
    return obj

def run(path):
    obj=load(path)
    done={r["result"].get("states") for r in obj["records"] if "states" in r["result"]}
    todo=next((n for n in (2,3) if n not in done),None)
    if todo is None:
        print(json.dumps({"status":"complete","next_round":obj["next_round"],"tasks_completed":sorted(done)}))
        return
    result=examine(todo)
    obj["records"].append({"round":obj["next_round"],"result":result,"sha256":digest(result)})
    obj["next_round"]+=1
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=str(p.parent))
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(obj,f,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print(json.dumps({"status":"advanced","states":todo,"next_round":obj["next_round"],"model_count":result["model_count"]}))

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--checkpoint",default="research/saa014.json")
    run(parser.parse_args().checkpoint)
