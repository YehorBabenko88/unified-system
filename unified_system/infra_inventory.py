"""Strict read-only inventory normalization for an owner-approved office fleet."""
import re
from .fleet_policy import FleetPolicyError, topology

_KEY=re.compile(r"[A-Za-z0-9_.:-]{1,80}\Z")

def summarize_fleet(nodes,now_ms,databases=()):
    t=topology(nodes,now_ms)
    if not isinstance(databases,(tuple,list)) or len(databases)>128:
        raise FleetPolicyError("invalid databases")
    db=[]
    seen=set()
    for item in databases:
        if not isinstance(item,dict) or set(item)!={"id","engine","size_bytes","status","owner"}:
            raise FleetPolicyError("invalid database observation")
        ident=item["id"]
        if type(ident) is not str or not _KEY.fullmatch(ident) or ident in seen:
            raise FleetPolicyError("invalid database id")
        seen.add(ident)
        if item["engine"] not in ("postgresql","sqlite") or item["status"] not in ("OBSERVED","UNAVAILABLE","STALE"):
            raise FleetPolicyError("invalid database status")
        size=item["size_bytes"]
        if size is not None and (type(size) is not int or not 0<=size<=2**63-1):
            raise FleetPolicyError("invalid size")
        if type(item["owner"]) is not str or not _KEY.fullmatch(item["owner"]):
            raise FleetPolicyError("invalid db owner")
        db.append(dict(item))
    return {"schema_version":1,"mode":"READ_ONLY_PLAN_ONLY",
            "nodes":t,"total_nodes":len(t),
            "active_nodes":sum(n["state"]=="ACTIVE" for n in t),
            "databases":sorted(db,key=lambda d:d["id"]),
            "database_total_bytes_observed":sum(d["size_bytes"] for d in db if d["size_bytes"] is not None),
            "unknown_database_sizes":sum(d["size_bytes"] is None for d in db),
            "network_links":[],"network_topology_status":"NOT_ATTESTED",
            "deployment_authorized":False,"trading_authorized":False}
