"""Offline read-only source adapters; explicit data provenance, no I/O."""
from .contracts import ContractError

def normalize_source(name, snapshot):
    if name not in ("strattester", "grid") or not isinstance(snapshot, dict):
        raise ContractError("invalid source")
    if set(snapshot) != {"source", "status", "timestamp_ms", "items", "synthetic"}:
        raise ContractError("invalid source snapshot")
    if snapshot["source"] != name or snapshot["status"] not in ("READY","STALE","UNAVAILABLE"):
        raise ContractError("source identity/status mismatch")
    if type(snapshot["timestamp_ms"]) is not int or not 0 <= snapshot["timestamp_ms"] <= 4102444800000:
        raise ContractError("invalid UTC milliseconds")
    if type(snapshot["synthetic"]) is not bool or snapshot["synthetic"] is not True:
        raise ContractError("unverified real source forbidden")
    items=snapshot["items"]
    if not isinstance(items,list) or len(items)>100 or any(not isinstance(x,dict) for x in items):
        raise ContractError("invalid items")
    if snapshot["status"] == "UNAVAILABLE" and items:
        raise ContractError("unavailable source cannot publish items")
    return {"source":name,"status":snapshot["status"],"timestamp_ms":snapshot["timestamp_ms"],"count":len(items),"provenance":"SYNTHETIC_ONLY"}

def compose_dashboard(strattester=None,grid=None):
    sources={}
    for name,data in (("strattester",strattester),("grid",grid)):
        sources[name]={"status":"UNAVAILABLE","provenance":"NONE"} if data is None else normalize_source(name,data)
    return {"mode":"READ_ONLY_SYNTHETIC","sources":sources,"trading_authorized":False}
