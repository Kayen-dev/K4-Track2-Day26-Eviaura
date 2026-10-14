"""Package the official bundle and the short team dossier for local handoff."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.audit_day26 import verify_bundle


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--team", default="Eviaura", choices=["Eviaura"])
    args = ap.parse_args()
    check = verify_bundle(args.team)
    if check["errors"]:
        ap.error("Bundle does not match local submission: " + "; ".join(check["errors"]))
    deck = json.loads((ROOT / "deck/deck.json").read_text(encoding="utf-8"))
    if deck["team"] != args.team:
        ap.error("Deck team and bundle team differ")
    files = ["SUBMISSION.md", "TEAMMATES.md", "TEAM_PLAN.md", "docs/DAY26_REVIEW.md",
             "tests/test_day26_supplement.py", "tests/test_day26_mechanics_integration.py",
             "tests/test_prosecute.py", "tests/test_day26_audit.py",
             "tools/audit_day26.py", "tools/package_submission.py", ".github/workflows/day26-linux.yml"]
    mapping = {name: ROOT / name for name in files}
    mapping[f"{args.team}.bundle"] = ROOT / "submissions" / f"{args.team}.bundle"
    for path in sorted((ROOT / "runs/day26-audit").iterdir()):
        if path.is_file() and path.suffix in {".log", ".json", ".xml"}:
            mapping[f"evidence/{path.name}"] = path
    evidence = json.loads(mapping["evidence/results.json"].read_text(encoding="utf-8"))
    if not evidence["python"].startswith("3.12") or any(c["exit_code"] for c in evidence["checks"].values()):
        ap.error("The dossier requires passing Python 3.12 conformance checks")
    if "tests_windows" in evidence["checks"]:
        ap.error("The dossier requires the full Linux audit, not a Windows exclusion run")
    if evidence.get("bundle", {}).get("sha256") != check["sha256"]:
        ap.error("Audit evidence refers to an older bundle; rerun the audit")
    if evidence["tracked_files_changed"] or any(row["exit_code"] for row in evidence["spar"]):
        ap.error("Audit detected changed files or a failed spar")
    full_match_bots = {row.get("bot") for row in evidence["spar"] if row.get("role") == "all"}
    if ("lethality_warnings" not in evidence or not {"rookie", "adversary"} <= full_match_bots
            or any("hp_bot" not in row for row in evidence["spar"])):
        ap.error("Audit has no current full-match lethality evidence; rerun it")
    out = ROOT / "submissions" / f"{args.team}-hoso.zip"
    manifest = {"team": args.team, "official_bundle": f"{args.team}.bundle",
                "lethality_warnings": evidence["lethality_warnings"], "files": []}
    # Read all inputs first so an absent file cannot produce a partial dossier.
    contents = {name: path.read_bytes() for name, path in mapping.items()}
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as package:
        for name, content in contents.items():
            package.writestr(name, content)
            manifest["files"].append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
        package.writestr("DOSSIER_MANIFEST.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(out) as package:
        for row in manifest["files"]:
            assert hashlib.sha256(package.read(row["path"])).hexdigest() == row["sha256"]
    print(f"Wrote {out} ({len(contents)} files; hashes verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
