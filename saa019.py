"""SAA-019: L5 substrate-free dynamic existence is NOT inferred from completion."""
import itertools
import json
from functools import reduce

def G(b):
    return reduce(lambda n,v:n*257+v+1,b,1)

def D(n):
    a=[]
    while n>1:
        n,r=divmod(n,257)
        if not r: raise ValueError("invalid Godel code")
        a.append(r-1)
    return bytes(a[::-1])

def step(s):
    return {"q":(s["q"]+1)%3,"t":s["t"]+1}

def experiment():
    s={"q":0,"t":0}
    b=json.dumps(s,sort_keys=True).encode()
    assert D(G(b))==b
    direct=step(step(s))
    restored=json.loads(D(G(json.dumps(step(s),sort_keys=True).encode())))
    assert step(restored)==direct
    names=("completed","formal","active","substrate")
    worlds=[dict(zip(names,bits)) for bits in itertools.product((False,True),repeat=4)]
    admissible=[w for w in worlds if not w["completed"] or w["formal"]]
    counter=next(w for w in admissible if w["completed"] and not w["active"] and not w["substrate"])
    return {"godel_roundtrip":True,"resume_equivalent":True,
            "admissible_models":len(admissible),"L5_dynamic_entailed":False,
            "countermodel":counter,"substrate_free_actual_activity":"not_established",
            "status":"bounded_formal_test_only"}

if __name__=="__main__":
    print(json.dumps(experiment(),sort_keys=True))
