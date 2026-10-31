"""Strict capability negotiation without importing module implementations."""
import re
from .contracts import ContractError
from .module_catalog import MODULE_IDS

_MODULES = MODULE_IDS
_SHA = re.compile(r"[0-9a-f]{64}\Z")

def negotiate(descriptor, *, expected_id, supported_major=1):
    if not isinstance(descriptor, dict) or set(descriptor) != {"module_id", "api_major", "api_minor", "source_sha", "capabilities"}:
        raise ContractError("invalid descriptor")
    if expected_id not in _MODULES or type(descriptor["module_id"]) is not str or descriptor["module_id"] != expected_id:
        raise ContractError("module identity mismatch")
    if type(descriptor["api_major"]) is not int or descriptor["api_major"] != supported_major:
        raise ContractError("incompatible major version")
    if type(descriptor["api_minor"]) is not int or not 0 <= descriptor["api_minor"] <= 1000:
        raise ContractError("invalid minor version")
    if not isinstance(descriptor["source_sha"], str) or not _SHA.fullmatch(descriptor["source_sha"]):
        raise ContractError("invalid source sha")
    caps = descriptor["capabilities"]
    if not isinstance(caps, list) or len(caps) > 64 or any(type(c) is not str or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", c) for c in caps) or len(caps) != len(set(caps)):
        raise ContractError("invalid capabilities")
    return {"module_id":expected_id, "api_major":supported_major, "api_minor":descriptor["api_minor"], "capabilities":tuple(caps), "verified":"SCHEMA_ONLY"}
