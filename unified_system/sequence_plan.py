"""Pure four-module lifecycle visibility and dependency gates; no process launches."""
from .contracts import ContractError

STAGES=("INFRA_PREFLIGHT","INFRA_READY","ANALYSIS_PREPARE","MARKET_HISTORY_SYNC",
        "ANALYSIS_RESEARCH","ANALYSIS_RESULT_SEALED","HANDOFF_VERIFY",
        "MARKET_DATA_READY","TERMINAN_OBSERVING","STEADY_STATE")
VALID=frozenset(("NOT_STARTED","RUNNING","WAITING","BLOCKED","DEGRADED","COMPLETE"))
# Terminan is an independent observer after infrastructure readiness. It must
# remain operational even when research/handoff/market stages are blocked.
DEPENDENCIES={
    "INFRA_READY":("INFRA_PREFLIGHT",),
    "ANALYSIS_PREPARE":("INFRA_READY",),
    "MARKET_HISTORY_SYNC":("ANALYSIS_PREPARE",),
    "ANALYSIS_RESEARCH":("MARKET_HISTORY_SYNC",),
    "ANALYSIS_RESULT_SEALED":("ANALYSIS_RESEARCH",),
    "HANDOFF_VERIFY":("ANALYSIS_RESULT_SEALED",),
    "MARKET_DATA_READY":("HANDOFF_VERIFY",),
    "TERMINAN_OBSERVING":("INFRA_READY",),
    "STEADY_STATE":("MARKET_DATA_READY",),
}

def describe_progress(stage_status):
    if not isinstance(stage_status,dict) or set(stage_status)-set(STAGES):
        raise ContractError("unknown lifecycle stages")
    for stage,value in stage_status.items():
        if type(value) is not str or value not in VALID:
            raise ContractError("invalid lifecycle status")
    def blocked_ancestor(stage, visited=None):
        visited=set() if visited is None else visited
        if stage in visited:
            raise ContractError("cyclic lifecycle dependencies")
        visited.add(stage)
        for dep in DEPENDENCIES.get(stage,()):
            if stage_status.get(dep)=="BLOCKED" or blocked_ancestor(dep,set(visited)):
                return True
        return False
    for stage in DEPENDENCIES:
        if stage_status.get(stage) in ("RUNNING","COMPLETE") and blocked_ancestor(stage):
            raise ContractError("stage progressed despite blocked ancestor")
    return {"schema_version":1,"mode":"READ_ONLY_PLAN_ONLY",
            "stages":[{"stage":stage,"status":stage_status.get(stage,"NOT_STARTED")} for stage in STAGES],
            "execution_authorized":False,"trading_authorized":False,
            "paper_trading_authorized":False}
