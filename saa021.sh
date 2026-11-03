#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
s="\"\"\"SAA-021: SHA-free self-reproducing source and bounded transitions.\"\"\"\nimport json\nfrom functools import reduce\nG=lambda b:reduce(lambda n,v:n*257+v+1,b,1)\ndef D(n):\n a=[]\n while n>1:\n  n,r=divmod(n,257)\n  if not r:raise ValueError(\"invalid\")\n  a.append(r-1)\n return bytes(a[::-1])\nsource=('s=%r;exec(s)'%s).encode()\nassert D(G(source))==source\nA=lambda s:((s[0]+1)%3,s[1]+1)\ndef B(s):return ((s[0]+1)%3,s[1]+1)\nassert all(A((i,j))==B((i,j)) for i in range(3) for j in range(6))\na=b=(0,0)\nfor _ in range(12):a=A(a);b=B(b)\nassert a==b\nx=(0,0)\nfor _ in range(6):x=A(x)\nx=json.loads(D(G(json.dumps(x).encode())))\nfor _ in range(6):x=B(x)\nassert tuple(x)==a\nprint(json.dumps(dict(name=\"L5-GTM\",source_roundtrip=True,source_bytes=len(source),godel_bits=G(source).bit_length(),bounded_equivalence=True,resume_equivalent=True,L5_dynamic=\"not_established\"),sort_keys=True))"
exec(s)
PY
