"""SAA-016: finite correspondence and ontological bridge countermodel."""
import json
from functools import reduce

def G(b):
    return reduce(lambda n,v:n*257+v+1,b,1)

def D(n):
    if n<1: raise ValueError("invalid")
    a=[]
    while n>1:
        n,r=divmod(n,257)
        if not r: raise ValueError("invalid")
        a.append(r-1)
    return bytes(a[::-1])

def T(s):
    s=dict(s)
    s["x"]=(s["x"]+1)%4
    s["t"]+=1
    return s

def experiment():
    s={"x":0,"t":0}
    b=json.dumps(s,sort_keys=True).encode()
    assert D(G(b))==b
    p=T(T(s))
    q=json.loads(D(G(json.dumps(T(s),sort_keys=True).encode())))
    assert T(q)==p
    worlds=[{"computed":c,"independent":i} for c in (False,True) for i in (False,True)]
    counter=[w for w in worlds if w["computed"] and not w["independent"]]
    assert counter
    return {"godel_roundtrip":True,"resumption_equivalent":True,
            "bridge_entailment":False,"countermodel":counter[0],
            "epistemic_status":"finite_formal_model_only",
            "substrate_free_existence":"not_established"}

if __name__=="__main__":
    print(json.dumps(experiment(),sort_keys=True))
