"""Validate coordinator input before an Actions job checks out a cohort."""
import json
import os
from pathlib import Path
import re

PATH = Path(__file__).with_name("crossrepo-cohort.json")
SCHEMA = "unified.crossrepo-cohort.v1"
REPOSITORIES = {
    "unified-system", "math", "bybit-cluster-grid", "Terminan", "meta_analyse", "strattester",
}


def validate(raw):
    if len(raw) > 4096:
        raise ValueError("Cohort manifest exceeds 4096 characters")
    manifest = json.loads(raw)
    if (type(manifest) is not dict or set(manifest) != {"schema", "heads"}
            or manifest["schema"] != SCHEMA):
        raise ValueError("Invalid cohort schema")
    heads = manifest["heads"]
    if type(heads) is not dict or set(heads) != REPOSITORIES:
        raise ValueError("Cohort must pin exactly the six known repositories")
    if any(type(sha) is not str or not re.fullmatch(r"[0-9a-f]{40}", sha) for sha in heads.values()):
        raise ValueError("Every cohort revision must be a full lowercase Git SHA")
    return heads


if __name__ == "__main__":
    raw = os.environ.get("REQUESTED_COHORT") or PATH.read_text(encoding="utf-8")
    heads = validate(raw)
    PATH.write_text(json.dumps({"schema": SCHEMA, "heads": heads}, indent=2) + "\n", encoding="utf-8")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        for name, sha in sorted(heads.items()):
            output.write(f"{name}={sha}\n")
