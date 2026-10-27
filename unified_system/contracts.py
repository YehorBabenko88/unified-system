"""Strict offline handoff validation; no filesystem or network access."""
import hashlib
import json
import re

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")

class ContractError(ValueError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def seal(payload):
    return hashlib.sha256(canonical(payload)).hexdigest()

def validate_handoff(envelope, expected_dataset):
    if not isinstance(envelope, dict) or set(envelope) != {"schema_version", "producer", "run_id", "dataset_fingerprint", "status", "capabilities", "payload", "sha256"}:
        raise ContractError("invalid envelope fields")
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
        raise ContractError("incompatible schema")
    if not isinstance(envelope["producer"], str) or envelope["producer"] != "strattester":
        raise ContractError("invalid producer")
    if not isinstance(envelope["run_id"], str) or not _ID.fullmatch(envelope["run_id"]):
        raise ContractError("invalid run id")
    if not isinstance(envelope["dataset_fingerprint"], str) or not _SHA.fullmatch(envelope["dataset_fingerprint"]):
        raise ContractError("invalid dataset fingerprint")
    if not isinstance(expected_dataset, str) or not _SHA.fullmatch(expected_dataset) or envelope["dataset_fingerprint"] != expected_dataset:
        raise ContractError("dataset mismatch")
    if envelope["status"] != "SEALED":
        raise ContractError("unsealed research")
    if envelope["capabilities"] != ["historical_research"]:
        raise ContractError("unsupported capability")
    if not isinstance(envelope["payload"], dict):
        raise ContractError("invalid payload")
    digest = envelope["sha256"]
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ContractError("invalid digest")
    try:
        actual = seal({k:v for k,v in envelope.items() if k != "sha256"})
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError("noncanonical payload") from exc
    if actual != digest:
        raise ContractError("tampered handoff")
    return {"run_id":envelope["run_id"], "status":"VERIFIED_SYNTHETIC", "dataset_fingerprint":expected_dataset}
