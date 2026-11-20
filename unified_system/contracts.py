"""Shared contract errors and canonical integrity bytes."""
import hashlib
import json


class ContractError(ValueError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def seal(payload):
    return hashlib.sha256(canonical(payload)).hexdigest()

