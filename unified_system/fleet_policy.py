"""Pure fail-closed fleet topology/placement plan. No network/process/database I/O."""
import math
import re

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_MODULES = frozenset(("grid", "strattester", "math", "terminan", "unified-system"))
_STATES = frozenset(("ACTIVE", "DRAINING", "SUSPECT", "OFFLINE", "RETIRED", "QUARANTINED"))

class FleetPolicyError(ValueError):
    pass

def _ratio(v):
    if type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1:
        raise FleetPolicyError("invalid utilization")
    return float(v)

def validate_node(node):
    if not isinstance(node, dict) or set(node) != {"id","state","cpu","memory","disk","modules","zone","last_heartbeat_ms","epoch"}:
        raise FleetPolicyError("invalid node schema")
    if type(node["id"]) is not str or not _ID.fullmatch(node["id"]):
        raise FleetPolicyError("invalid node id")
    if node["state"] not in _STATES:
        raise FleetPolicyError("invalid node state")
    if type(node["zone"]) is not str or not _ID.fullmatch(node["zone"]):
        raise FleetPolicyError("invalid zone")
    if type(node["epoch"]) is not int or node["epoch"] < 1:
        raise FleetPolicyError("invalid epoch")
    if type(node["last_heartbeat_ms"]) is not int or node["last_heartbeat_ms"] < 0:
        raise FleetPolicyError("invalid heartbeat")
    for key in ("cpu","memory","disk"):
        _ratio(node[key])
    mods=node["modules"]
    if not isinstance(mods,list) or len(mods)>len(_MODULES) or any(type(x) is not str or x not in _MODULES for x in mods) or len(mods)!=len(set(mods)):
        raise FleetPolicyError("invalid module list")
    return node

def topology(nodes, now_ms, ttl_ms=30000):
    if type(now_ms) is not int or now_ms < 0 or type(ttl_ms) is not int or not 1000 <= ttl_ms <= 600000:
        raise FleetPolicyError("invalid time")
    if not isinstance(nodes,list) or len(nodes)>256:
        raise FleetPolicyError("invalid fleet roster")
    ids=set()
    output=[]
    for node in nodes:
        validate_node(node)
        if node["id"] in ids:
            raise FleetPolicyError("duplicate machine")
        ids.add(node["id"])
        age=now_ms-node["last_heartbeat_ms"]
        effective=node["state"]
        if age < 0:
            effective="QUARANTINED"
        elif age > ttl_ms and effective=="ACTIVE":
            effective="SUSPECT"
        output.append({"id":node["id"],"zone":node["zone"],"state":effective,
                       "modules":list(node["modules"]),"cpu":node["cpu"],
                       "memory":node["memory"],"disk":node["disk"],
                       "age_ms":max(0,age),"epoch":node["epoch"]})
    return sorted(output,key=lambda x:x["id"])

def plan_placement(nodes,workloads,now_ms,*,quorum=False):
    """Observation-only; no assignable work without an externally verified quorum."""
    topo=topology(nodes,now_ms)
    if not isinstance(workloads,list) or len(workloads)>1024:
        raise FleetPolicyError("invalid workloads")
    if type(quorum) is not bool:
        raise FleetPolicyError("invalid quorum")
    ids=set()
    outcome=[]
    planned={n["id"]:0 for n in topo}
    for job in workloads:
        if not isinstance(job,dict) or set(job)!={"id","module","cpu_cost","memory_cost","zone_avoid"}:
            raise FleetPolicyError("invalid workload")
        ident,module=job["id"],job["module"]
        if type(ident) is not str or not _ID.fullmatch(ident) or ident in ids:
            raise FleetPolicyError("invalid workload identity")
        ids.add(ident)
        if module not in _MODULES:
            raise FleetPolicyError("invalid module")
        cpu=_ratio(job["cpu_cost"]); mem=_ratio(job["memory_cost"])
        avoided=job["zone_avoid"]
        if not isinstance(avoided,list) or any(type(x) is not str or not _ID.fullmatch(x) for x in avoided):
            raise FleetPolicyError("invalid zone avoidance")
        candidates=[n for n in topo if n["state"]=="ACTIVE" and n["age_ms"]<=30000
                    and module in n["modules"] and n["zone"] not in avoided
                    and n["cpu"]+cpu<=0.85 and n["memory"]+mem<=0.85 and n["disk"]<=0.85]
        candidates.sort(key=lambda n:(max(n["cpu"]+cpu,n["memory"]+mem)+planned[n["id"]]*0.05,n["id"]))
        selected=candidates[0]["id"] if candidates and quorum else None
        outcome.append({"workload":ident,"candidate":selected,
                        "state":"CANDIDATE_ONLY" if selected else ("NO_QUORUM" if not quorum else "NO_CAPACITY")})
        if selected: planned[selected]+=1
    return {"mode":"PLAN_ONLY","quorum_attested":False,"proposed":outcome,
            "execution_authorized":False,"total_nodes":len(topo),"active_nodes":sum(x["state"]=="ACTIVE" for x in topo)}
