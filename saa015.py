"""SAA-015: bounded computational-state continuity experiment (not consciousness)."""
import hashlib
import json

RULES = {(0, '1'): (0, 'X', 1), (0, '_'): (1, '_', 0)}

def encode(data):
    n = 1
    for byte in data:
        n = 257*n + byte + 1
    return n

def decode(n):
    if n < 1: raise ValueError('invalid code')
    out = []
    while n > 1:
        n, r = divmod(n, 257)
        if r == 0: raise ValueError('invalid code')
        out.append(r - 1)
    return bytes(reversed(out))

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def initial(length=4):
    return {'state': 0, 'head': 0, 'tape': {'%d'%i: '1' for i in range(length)}, 'steps': 0}

def step(s):
    s = json.loads(canonical(s))
    if s['state'] == 1: return s
    key = (s['state'], s['tape'].get(str(s['head']), '_'))
    state, write, move = RULES[key]
    if write == '_': s['tape'].pop(str(s['head']), None)
    else: s['tape'][str(s['head'])] = write
    s['state'] = state
    s['head'] += move
    s['steps'] += 1
    return s

def resume(s, budget):
    for _ in range(budget):
        if s['state'] == 1: break
        s = step(s)
    return s

def experiment():
    source = initial()
    uninterrupted = resume(source, 20)
    midpoint = resume(source, 2)
    payload = canonical(midpoint)
    code = encode(payload)
    restored = json.loads(decode(code))
    migrated = resume(restored, 18)
    assert restored == midpoint
    assert migrated == uninterrupted
    assert migrated['state'] == 1
    return {'experiment': 'bounded_cross_runtime_serialization',
            'godel_roundtrip': True, 'continuation_equivalent': True,
            'steps': migrated['steps'], 'final_state_sha256': hashlib.sha256(canonical(migrated)).hexdigest(),
            'epistemic_status': 'software_state_equivalence_only',
            'substrate_free_existence': 'not_established'}

if __name__ == '__main__':
    print(json.dumps(experiment(), sort_keys=True))
