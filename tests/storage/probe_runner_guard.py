"""Negative source guard probes ONLY in a separate owned temporary .git clone."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

SOURCE = Path(__file__).resolve().parents[2]


def git(root, *args, input=None):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(root), *args], input=input)


def main():
    with tempfile.TemporaryDirectory(prefix="storage-stage1-guard-clone-") as directory:
        clone = Path(directory) / "isolated-clone"
        subprocess.run(["git", "--no-replace-objects", "clone", "--no-local", "--no-hardlinks", str(SOURCE), str(clone)], check=True, capture_output=True)
        # Before the first source commit, overlay ONLY this allocation's staged files.
        paths = git(SOURCE, "diff", "--cached", "--name-only").decode().splitlines()
        for relative in paths:
            if not relative.startswith(("unified_system/storage/", "tests/storage/", "docs/storage/")):
                raise RuntimeError("PROBE_SCOPE_REJECTED")
            target = clone / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, target)
        git(clone, "add", "--", "unified_system/storage", "tests/storage", "docs/storage")
        if git(clone, "diff", "--cached", "--name-only").strip():
            git(clone, "-c", "user.name=Stage1Fixture", "-c", "user.email=stage1-fixture@example.invalid", "commit", "-m", "Disposable Stage1 guard fixture")
        def run():
            return subprocess.run([sys.executable, "-B", "tests/storage/run_stage1.py"], cwd=clone, capture_output=True)
        baseline = run()
        if baseline.returncode or json.loads(baseline.stdout)["tests_run"] != 26:
            raise RuntimeError("ISOLATED_GUARD_BASELINE_FAILED")
        outcomes = []
        for kind, expression in (("blob", "HEAD:unified_system/storage/contracts.py"), ("tree", "HEAD^{tree}")):
            original = git(clone, "rev-parse", expression).decode().strip()
            raw = git(clone, "cat-file", kind, original)
            if kind == "blob":
                replacement = git(clone, "hash-object", "-w", "--stdin", input=raw+b"\n# disposable replacement probe\n").decode().strip()
            else:
                listing = git(clone, "ls-tree", original)
                blob = git(clone, "hash-object", "-w", "--stdin", input=b"disposable guard probe\n").decode().strip()
                replacement = git(clone, "mktree", input=listing+f"100644 blob {blob}\tguard-probe.txt\n".encode()).decode().strip()
            # This clone has its own .git; never touch the source's replace refs.
            git(clone, "replace", original, replacement)
            result = run()
            if result.returncode == 0 or b"REPLACE_REFS_REJECTED_BEFORE_TESTS" not in result.stderr or b"Ran 26 tests" in result.stderr:
                raise RuntimeError("REPLACEMENT_WAS_NOT_REJECTED_BEFORE_TESTS")
            outcomes.append({"replacement": kind, "rejected_before_tests": True})
            git(clone, "replace", "-d", original)
        print(json.dumps({"evidence_class": "ISOLATED_GIT_CLONE_NEGATIVE_PROBES", "model_cases": 26, "outcomes": outcomes}))


if __name__ == "__main__":
    main()
