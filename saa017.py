"""SAA-017: distinguish formal identity, actual activity, and substrate freedom.
A finite countermodel checker, NOT an implementation of substrate-free computation.
"""
import itertools
import json

ATOMS=("completed","formal","active","substrate")
def implies(a,b): return (not a) or b
def worlds():
    for bits in itertools.product((False,True),repeat=4):
        yield dict(zip(ATOMS,bits))
def axioms(w):
    # Finite completion establishes a formal description, not ongoing activity.
    return implies(w["completed"],w["formal"])
def claims(w):
    return {
        "formal_from_completion":implies(w["completed"],w["formal"]),
        "activity_from_completion":implies(w["completed"],w["active"]),
        "substrate_free_activity_from_completion":implies(w["completed"],w["active"] and not w["substrate"])
    }
def check():
    admissible=[w for w in worlds() if axioms(w)]
    results={}
    for claim in ("formal_from_completion","activity_from_completion","substrate_free_activity_from_completion"):
        bad=next((w for w in admissible if not claims(w)[claim]),None)
        results[claim]={"entailed":bad is None,"countermodel":bad}
    assert results["formal_from_completion"]["entailed"]
    assert not results["activity_from_completion"]["entailed"]
    assert not results["substrate_free_activity_from_completion"]["entailed"]
    # Adding the target conclusion as an axiom yields entailment by construction only.
    strengthened=[w for w in admissible if implies(w["completed"],w["active"] and not w["substrate"])]
    assert all(claims(w)["substrate_free_activity_from_completion"] for w in strengthened)
    return {"model_count":len(admissible),"results":results,
            "bridge_axiom_status":"assumption_not_independent_evidence",
            "physical_substrate_free_computation":"not_demonstrated"}
if __name__=="__main__": print(json.dumps(check(),sort_keys=True))
