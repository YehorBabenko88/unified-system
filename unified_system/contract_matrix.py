"""Pure cross-repo compatibility matrix, conservative and non-authorizing."""
from .compatibility import validate_response
from .contracts import ContractError
from .provenance_v11 import qualify_historical, inspect_grid_snapshot

def evaluate(*, strattester_health, grid_health, supervisor_health,
             research_record=None, owner_receipts=(), grid_snapshot=None):
    sources={}
    for name,payload in (("strattester",strattester_health),("grid",grid_health),
                         ("supervisor",supervisor_health)):
        try:
            result=validate_response(name,"health",503 if payload.get("status")=="UNAVAILABLE" else 200,payload)
            sources[name]={"status":payload["status"],"contract":result["contract"]}
        except (ContractError,AttributeError,TypeError):
            sources[name]={"status":"UNAVAILABLE","contract":"INVALID"}
    research=qualify_historical(research_record,owner_receipts)
    grid=inspect_grid_snapshot(grid_snapshot)
    return {"contract_version":"integration-matrix.v1",
            "sources":sources,"research":research,"grid_snapshot":grid,
            "production_ready":False,"trading_authorized":False,
            "physical_acceptance":"NOT_RUN"}
