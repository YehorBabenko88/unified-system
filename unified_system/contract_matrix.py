"""Pure cross-repo compatibility matrix, conservative and non-authorizing."""
from .compatibility import validate_response
from .contracts import ContractError
from .provenance_v11 import inspect_historical_receipt, inspect_market_data_snapshot

def evaluate(*, terminan_health, market_data_health, unified_system_health,
             research_record=None, owner_receipts=(), market_data_snapshot=None):
    sources={}
    for name,payload in (("terminan",terminan_health),("market_data",market_data_health),
                         ("unified_system",unified_system_health)):
        try:
            result=validate_response(name,"health",503 if payload.get("status")=="UNAVAILABLE" else 200,payload)
            sources[name]={"status":payload["status"],"contract":result["contract"]}
        except (ContractError,AttributeError,TypeError):
            sources[name]={"status":"UNAVAILABLE","contract":"INVALID"}
    research=inspect_historical_receipt(research_record,owner_receipts)
    market_data=inspect_market_data_snapshot(market_data_snapshot)
    return {"contract_version":"integration-matrix.v1",
            "sources":sources,"research":research,"market_data_snapshot":market_data,
            "production_ready":False,"trading_authorized":False,
            "physical_acceptance":"NOT_RUN"}
