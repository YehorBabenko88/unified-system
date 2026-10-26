"""Offline release lock validation. Hashes do not authenticate publishers."""
import json
from .contracts import ContractError
from .registry import negotiate

def validate_lock(lock):
    if not isinstance(lock, dict) or set(lock) != {"lock_version", "modules"} or type(lock["lock_version"]) is not int or lock["lock_version"] != 1:
        raise ContractError("invalid lock")
    modules=lock["modules"]
    if not isinstance(modules, list) or len(modules)>3:
        raise ContractError("invalid module roster")
    seen=set()
    for item in modules:
        if not isinstance(item,dict) or set(item)!={"descriptor","artifact_sha256"}:
            raise ContractError("invalid locked module")
        desc=item["descriptor"]
        if not isinstance(desc,dict):
            raise ContractError("invalid descriptor")
        name=desc.get("module_id")
        if type(name) is not str or name in seen:
            raise ContractError("duplicate or invalid module")
        seen.add(name)
        negotiate(desc,expected_id=name)
        digest=item["artifact_sha256"]
        if type(digest) is not str or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ContractError("invalid artifact digest")
    return tuple(sorted(seen))

def parse_lock(raw):
    if not isinstance(raw,(bytes,str)) or len(raw)>65536:
        raise ContractError("lock too large")
    try:
        lock=json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    except (ValueError,TypeError,UnicodeDecodeError) as exc:
        raise ContractError("malformed lock") from exc
    validate_lock(lock)
    return lock
