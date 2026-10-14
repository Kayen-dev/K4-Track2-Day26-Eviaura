"""Reproduce Day26 checks without editing the team's submission or the kit.

Run with Python 3.12: python tools/audit_day26.py
Detailed local traces go to ignored runs/day26-audit/. No network/model calls.
"""
from __future__ import annotations

import argparse
from collections import Counter
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "runs" / "day26-audit"
WINDOWS_EXCLUSION = "test_run_probe_vectors_unsandboxed_baseline"


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def run(name, args):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0"}
    result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                            capture_output=True, text=True, encoding="utf-8")
    (OUT / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    return {"command": [sys.executable, *args], "exit_code": result.returncode,
            "log": f"runs/day26-audit/{name}.log"}


def capture(bot, role, seed):
    """Observe the original spar's returns; keep its planning/scoring unchanged."""
    import spar
    from eval.prosecute import prosecute
    from kit.referee.rubric import family_of, weight_of
    from kit.referee.verify import VerifyContext, verify_claims

    original = spar._exchange
    exchanges = []

    def observed(*args, **kwargs):
        result = original(*args, **kwargs)
        card, defender = args[4], args[1]
        trace = result["trace"]
        answer = next(e["p"] for e in trace if e["type"] == "answer")
        # Only evaluate our prosecutor when this role actually selects it.
        own_prosecutor = defender != "you" and role in ("prosecutor", "all")
        claims, gate, elapsed = [], [], None
        missed = []
        if own_prosecutor:
            start = time.perf_counter()
            claims = prosecute(trace, answer, card)["claims"]
            elapsed = (time.perf_counter() - start) * 1000
            gate = verify_claims(trace, claims, ctx=VerifyContext(
                card=card, act="learner:sv-0417", scopes=frozenset({"wiki.read"})))
            # No world supplied: spar anchors/results are synthetic. World-dependent
            # classes must remain unproven, never get a false ground-truth label.
            for hit in result["missed"]:
                chosen = [c["cls"] for c in claims if family_of(c["cls"]) == family_of(hit["cls"])]
                reason = "needs_review"
                if chosen and max(map(weight_of, chosen)) >= weight_of(hit["cls"]):
                    reason = "family_cap_heavier_or_equal_claim"
                missed.append({**hit, "reason": reason, "chosen_in_family": chosen})
        exchanges.append({"attacker": args[0], "defender": defender, "round": args[6],
                          "card": card, **result, "student_claims": claims,
                          "student_prosecutor_ms": elapsed, "gate1": gate,
                          "missed_analysis": missed})
        return result

    stream = io.StringIO()
    spar._exchange = observed
    try:
        with contextlib.redirect_stdout(stream):
            code = spar.main(["--bot", bot, "--as", role, "--rounds", "10", "--seed", str(seed)])
    finally:
        spar._exchange = original
    name = f"{bot}-{role}-seed{seed}"
    (OUT / f"{name}.log").write_text(stream.getvalue(), encoding="utf-8")
    save(OUT / f"{name}.json", exchanges)
    # Parse the actual CLI result rather than reimplementing HP arithmetic.
    result_line = next(line.strip() for line in stream.getvalue().splitlines() if "RESULT:" in line)
    verdicts = Counter(row["outcome"] for x in exchanges for row in x["gate1"])
    ms = [x["student_prosecutor_ms"] for x in exchanges if x["student_prosecutor_ms"] is not None]
    summary = {"bot": bot, "role": role, "seed": seed, "exit_code": code,
               "result": result_line, "rounds": len(exchanges) // 2,
               "gate1": dict(verdicts), "prosecutor_max_ms": max(ms, default=0),
               "missed": dict(Counter(m["reason"] for x in exchanges for m in x["missed_analysis"])),
               "credits_min": min(x["credits_left"] for x in exchanges if x["defender"] == "you"),
               "gateway_max_ms": max(e["p"].get("latency_ms", 0) for x in exchanges
                                     if x["defender"] == "you" for e in x["trace"] if e["type"] == "decision"),
               "trace": f"runs/day26-audit/{name}.json"}
    save(OUT / f"{name}-summary.json", summary)
    return code


def verify_bundle(team):
    path = ROOT / "submissions" / f"{team}.bundle"
    with zipfile.ZipFile(path) as bundle:
        manifest = json.loads(bundle.read("MANIFEST.json"))
        errors = []
        if manifest["team"] != team:
            errors.append("wrong manifest team")
        for row in manifest["files"]:
            content = bundle.read(row["path"])
            if hashlib.sha256(content).hexdigest() != row["sha256"]:
                errors.append(f"bundle hash: {row['path']}")
            if content != (ROOT / row["path"]).read_bytes():
                errors.append(f"local content: {row['path']}")
        for name, digest in manifest["kit_hashes"].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                errors.append(f"kit hash: {name}")
        expected = {p.relative_to(ROOT).as_posix() for directory in ("agent", "deck", "eval")
                    for p in (ROOT / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        if expected != {r["path"] for r in manifest["files"]}:
            errors.append("submission files missing or unexpected")
        return {"team": manifest["team"], "files": len(manifest["files"]),
                "kit_hashes": len(manifest["kit_hashes"]), "errors": errors,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--team", default="Eviaura")
    ap.add_argument("--seeds", nargs="+", type=int, default=[4, 5, 6])
    ap.add_argument("--capture", nargs=3, metavar=("BOT", "ROLE", "SEED"))
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.capture:
        return capture(args.capture[0], args.capture[1], int(args.capture[2]))
    if sys.version_info[:2] != (3, 12):
        ap.error("Use Python 3.12 as required by pyproject.toml")
    # Snapshot every already tracked file; new audit files are allowed.
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    before = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in tracked if p}
    worlds = sorted((ROOT / "kit/world").glob("*/manifest.json"))
    if not worlds:
        ap.error("Download the official world first; see README section 2")
    world = worlds[-1].parent
    if list((ROOT / "kit/world").glob("*/truth.json")):
        ap.error("Student world must not contain truth.json")
    from kit.world.loader import World
    from eval.prosecute import load_fixtures, prosecute, score_prosecutor
    loaded = World.load(world)
    manifest = json.loads((world / "manifest.json").read_text(encoding="utf-8"))
    report = {"python": sys.version, "world_id": manifest["world_id"],
              "pages": manifest["counts"]["__total__"], "world_load_ok": bool(loaded),
              "fixtures": score_prosecutor(prosecute, load_fixtures()), "checks": {}, "spar": []}
    report["checks"]["no_key"] = run("no-key", ["-m", "kit.gate_no_key"])
    # Do not put pytest's tmp_path under runs/: G-KEY intentionally skips that
    # directory, including the test fixtures planting violations there.
    report["checks"]["tests_full"] = run("tests-full", ["-m", "pytest", "tests/", "-q", "-rs", "--tb=short",
        "-o", "junit_family=xunit1", "--junitxml=runs/day26-audit/tests-full.xml"])
    if os.name == "nt" and report["checks"]["tests_full"]["exit_code"]:
        report["checks"]["tests_windows"] = run("tests-windows", ["-m", "pytest", "tests/", "-q", "--tb=short",
            "-rs", "-o", "junit_family=xunit1", "--junitxml=runs/day26-audit/tests-windows.xml",
            "-k", f"not {WINDOWS_EXCLUSION}"])
    report["checks"]["deck"] = run("deck", ["validate_deck.py", "deck/deck.json", "deck/lineup.json",
                                                   "--world", str(world)])
    for bot in ("rookie", "operator", "adversary"):
        for role in ("defender", "attacker", "prosecutor", "all"):
            for seed in args.seeds:
                name = f"{bot}-{role}-seed{seed}"
                summary = OUT / f"{name}-summary.json"
                check = run(name + "-driver", [__file__, "--capture", bot, role, str(seed)])
                report["spar"].append(json.loads(summary.read_text(encoding="utf-8"))
                                      if check["exit_code"] == 0 else check)
                print(name, check["exit_code"], flush=True)
    report["checks"]["submit"] = run("submit", ["-m", "kit.submit", "--team", args.team])
    if report["checks"]["submit"]["exit_code"] == 0:
        report["bundle"] = verify_bundle(args.team)
    report["tracked_files_changed"] = [p for p, digest in before.items()
        if not (ROOT / p).exists() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    save(OUT / "results.json", report)
    # A Windows accommodation never turns the full-suite failure into a pass.
    failed = [name for name, check in report["checks"].items() if check["exit_code"]]
    print("results:", OUT / "results.json", "failed:", failed)
    return int(bool(failed or report["tracked_files_changed"] or report.get("bundle", {}).get("errors")
                    or any(row["exit_code"] for row in report["spar"])))


if __name__ == "__main__":
    raise SystemExit(main())
