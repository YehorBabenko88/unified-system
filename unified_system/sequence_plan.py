"""Pure five-module lifecycle visibility and gate planner; no process launches."""
from .contracts import ContractError

STAGES=("INFRA_PREFLIGHT","INFRA_READY","STRAT_PREPARE","STRAT_HISTORY_SYNC",
        "STRAT_RESEARCH","STRAT_RESULT_SEALED","HANDOFF_VERIFY",
        "GRID_MARKET_READY","TERMINAN_OBSERVING","STEADY_STATE")
VALID=frozenset(("NOT_STARTED","RUNNING","WAITING","BLOCKED","DEGRADED","COMPLETE"))
def describe_progress(stage_status):
    if not isinstance(stage_status,dict) or set(stage_status)-set(STAGES):
        raise ContractError("unknown lifecycle stages")
    out=[]
    blocked=False
    for stage in STAGES:
        value=stage_status.get(stage,"NOT_STARTED")
        if value not in VALID:
            raise ContractError("invalid lifecycle status")
        if blocked and value in ("RUNNING","COMPLETE"):
            raise ContractError("downstream progressed after block")
        out.append({"stage":stage,"status":value})
        if value=="BLOCKED":blocked=True
    return {"schema_version":1,"mode":"READ_ONLY_PLAN_ONLY","stages":out,
            "execution_authorized":False,"trading_authorized":False,
            "paper_trading_authorized":False}
