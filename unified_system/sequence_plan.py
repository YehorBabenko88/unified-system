"""Pure five-module lifecycle visibility and dependency gates; no process launches."""
from .contracts import ContractError

STAGES=("INFRA_PREFLIGHT","INFRA_READY","STRAT_PREPARE","STRAT_HISTORY_SYNC",
        "STRAT_RESEARCH","STRAT_RESULT_SEALED","HANDOFF_VERIFY",
        "GRID_MARKET_READY","TERMINAN_OBSERVING","STEADY_STATE")
VALID=frozenset(("NOT_STARTED","RUNNING","WAITING","BLOCKED","DEGRADED","COMPLETE"))
# Terminan is an independent observer after infrastructure readiness. It must
# remain operational even when research/handoff/market stages are blocked.
DEPENDENCIES={
    "INFRA_READY":("INFRA_PREFLIGHT",),
    "STRAT_PREPARE":("INFRA_READY",),
    "STRAT_HISTORY_SYNC":("STRAT_PREPARE",),
    "STRAT_RESEARCH":("STRAT_HISTORY_SYNC",),
    "STRAT_RESULT_SEALED":("STRAT_RESEARCH",),
    "HANDOFF_VERIFY":("STRAT_RESULT_SEALED",),
    "GRID_MARKET_READY":("HANDOFF_VERIFY",),
    "TERMINAN_OBSERVING":("INFRA_READY",),
    "STEADY_STATE":("GRID_MARKET_READY",),
}

def describe_progress(stage_status):
    if not isinstance(stage_status,dict) or set(stage_status)-set(STAGES):
        raise ContractError("unknown lifecycle stages")
    for stage,value in stage_status.items():
        if type(value) is not str or value not in VALID:
            raise ContractError("invalid lifecycle status")
    for stage,deps in DEPENDENCIES.items():
        value=stage_status.get(stage,"NOT_STARTED")
        if value in ("RUNNING","COMPLETE"):
            for dep in deps:
                previous=stage_status.get(dep,"NOT_STARTED")
                # This view is non-authorizing. Allow historical snapshots with
                # unknown predecessors, but reject explicit blocked dependency.
                if previous=="BLOCKED":
                    raise ContractError("stage progressed despite blocked dependency")
    return {"schema_version":1,"mode":"READ_ONLY_PLAN_ONLY",
            "stages":[{"stage":stage,"status":stage_status.get(stage,"NOT_STARTED")} for stage in STAGES],
            "execution_authorized":False,"trading_authorized":False,
            "paper_trading_authorized":False}
