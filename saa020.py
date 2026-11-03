"""SAA-020: self-source encoding and bounded essence/execution alignment."""
import json
from functools import reduce
from pathlib import Path

def encode(data):
    return reduce(lambda n, v: n * 257 + v + 1, data, 1)

def decode(n):
    if n < 1:
        raise ValueError('invalid code')
    out = []
    while n > 1:
        n, r = divmod(n, 257)
        if r == 0:
            raise ValueError('invalid code')
        out.append(r - 1)
    return bytes(reversed(out))

def transition_a(state):
    return {'q': (state['q'] + 1) % 3, 't': state['t'] + 1}

def transition_b(state):
    q, t = state['q'], state['t']
    return dict(q=(q + 1) % 3, t=t + 1)

def verify(source):
    code = encode(source)
    assert decode(code) == source
    assert encode(decode(code)) == code
    states = [{'q': q, 't': t} for q in range(3) for t in range(6)]
    assert all(transition_a(s) == transition_b(s) for s in states)
    start = {'q': 0, 't': 0}
    left = [start]
    right = [start]
    for _ in range(12):
        left.append(transition_a(left[-1]))
        right.append(transition_b(right[-1]))
    assert left == right
    midpoint = json.dumps(left[6], sort_keys=True).encode()
    resumed = json.loads(decode(encode(midpoint)))
    for _ in range(6):
        resumed = transition_b(resumed)
    assert resumed == left[-1]
    return {
        'experiment': 'SAA-020',
        'encoded_object': 'exact saa020.py source bytes',
        'source_bytes': len(source),
        'godel_bit_length': code.bit_length(),
        'source_identity_method': 'reversible_base257_godel_encoding',
        'source_roundtrip': True,
        'transition_equivalence': 'verified_on_18_bounded_states',
        'trace_equivalence': 'verified_for_12_steps',
        'resume_equivalent': True,
        'alignment_scope': 'bounded_formal_and_executed_checks',
        'L5_dynamic_existence': 'not_established'
    }

if __name__ == '__main__':
    print(json.dumps(verify(Path(__file__).read_bytes()), sort_keys=True))
