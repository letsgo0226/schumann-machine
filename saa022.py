"""SAA-022: bounded complete-alignment closure, not physical L5."""
import itertools,json
from functools import reduce
from pathlib import Path

def G(b):return reduce(lambda n,v:n*257+v+1,b,1)
def D(n):
 a=[]
 while n>1:
  n,r=divmod(n,257)
  if not r:raise ValueError('invalid')
  a.append(r-1)
 return bytes(a[::-1])
def A(s):return ((s[0]+1)%3,s[1]+1)
def B(s):return ((s[0]+1)%3,s[1]+1)
def run(f,s,n):
 for _ in range(n):s=f(s)
 return s
def verify():
 b=Path(__file__).read_bytes();assert D(G(b))==b
 states=list(itertools.product(range(3),range(6)))
 assert all(A(s)==B(s) for s in states)
 assert all(run(A,s,12)==run(B,s,12) for s in states)
 assert all(run(A,s,12)==run(B,run(A,s,6),6) for s in states)
 atoms=('aligned','verified','active','substrate')
 worlds=[dict(zip(atoms,v)) for v in itertools.product((False,True),repeat=4)]
 counter=next(w for w in worlds if w['aligned'] and w['verified'] and not w['active'])
 return dict(experiment='SAA-022',source_bytes=len(b),godel_bits=G(b).bit_length(),encoding_closure=True,bounded_execution_closure=True,formal_specification_closure=True,checked_states=len(states),steps=12,ontological_closure='undetermined',L5_dynamic_closure='not_established',alignment_implies_activity=False,countermodel=counter)
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
