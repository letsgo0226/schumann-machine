#!/usr/bin/env python3
"""Bounded, resumable synthetic computation for the Schumann operator VM.

This deliberately performs no browser login, networking, course recording,
deployment or access to private data. A GitHub-hosted runner is disposable:
the JSON checkpoint is the only state transferred between jobs/runs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys

SCHEMA = 1
ENGINE = "schumann-m45-inspired-checkpoint-v1"
SEED = hashlib.sha256(b"Schumann-operator-synthetic-seed-v1").hexdigest()
MAX_TARGET = 10000
MAX_STEPS_PER_JOB = 100

def transition(digest: str, n: int) -> str:
    return hashlib.sha256(bytes.fromhex(digest) + n.to_bytes(8, "big")).hexdigest()

def digest_at(n: int) -> str:
    result = SEED
    for step in range(1, n + 1):
        result = transition(result, step)
    return result

def validate(checkpoint: dict) -> int:
    if not isinstance(checkpoint, dict):
        raise ValueError("checkpoint must be an object")
    if checkpoint.get("schema") != SCHEMA or checkpoint.get("engine") != ENGINE:
        raise ValueError("checkpoint version mismatch")
    n = checkpoint.get("steps")
    if type(n) is not int or not 0 <= n <= MAX_TARGET:
        raise ValueError("invalid checkpoint step count")
    if checkpoint.get("seed") != SEED or checkpoint.get("digest") != digest_at(n):
        raise ValueError("checkpoint digest mismatch")
    if any(k not in {"schema", "engine", "seed", "steps", "digest", "target_steps", "completed", "last_os"} for k in checkpoint):
        raise ValueError("unexpected checkpoint field")
    return n

def advance(initial: dict | None, per_job: int, target: int, os_name: str) -> tuple[dict, dict]:
    if not 1 <= per_job <= MAX_STEPS_PER_JOB or not 1 <= target <= MAX_TARGET:
        raise ValueError("requested compute bounds exceeded")
    if initial is None:
        n = 0
        digest = SEED
    else:
        n = validate(initial)
        if n > target:
            raise ValueError("checkpoint exceeds new target")
        digest = initial["digest"]
    before = n
    for step in range(n + 1, min(target, n + per_job) + 1):
        digest = transition(digest, step)
        n = step
    state = {"schema": SCHEMA, "engine": ENGINE, "seed": SEED,
             "steps": n, "digest": digest, "target_steps": target,
             "completed": n == target, "last_os": os_name}
    report = {"engine": ENGINE, "os": os_name, "python": platform.python_version(),
              "steps_before": before, "steps_executed": n-before,
              "steps_after": n, "target_steps": target,
              "completed": n == target,
              "capabilities": {"ffmpeg": bool(shutil.which("ffmpeg")),
                               "powershell": bool(shutil.which("pwsh") or shutil.which("powershell")),
                               "power_bi_desktop": bool(shutil.which("PBIDesktop.exe"))}}
    return state, report

def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def self_test() -> None:
    a, _ = advance(None, 3, 8, "Linux")
    b, _ = advance(a, 3, 8, "Windows")
    c, _ = advance(b, 3, 8, "Linux")
    assert c["steps"] == 8 and c["completed"]
    assert validate(c) == 8 and c["digest"] == digest_at(8)
    bad = dict(c, digest="0" * 64)
    try:
        validate(bad)
    except ValueError:
        pass
    else:
        raise AssertionError("corrupt checkpoint was accepted")
    assert advance(c, 1, 8, "Windows")[1]["steps_executed"] == 0
    print("M45_CHECKPOINT_SELFTEST_PASS")

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-in", type=Path, help="Previously saved checkpoint JSON")
    p.add_argument("--state-out", type=Path, default=Path("artifacts/operator_state.json"))
    p.add_argument("--report", type=Path, default=Path("artifacts/operator_report.json"))
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--target", type=int, default=100)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test()
        return 0
    initial = json.loads(args.state_in.read_text(encoding="utf-8")) if args.state_in else None
    state, report = advance(initial, args.steps, args.target, platform.system())
    write_json(args.state_out, state)
    write_json(args.report, report)
    print("OPERATOR_CHECKPOINT", json.dumps(report, sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main())
