"""Contract-only cross-repository compatibility; no runtime provenance claims."""
from .contracts import ContractError

EXPECTED = {"strattester":"strattester","grid":"bybit-cluster-grid","supervisor":"unified-system"}
ROUTES = {"strattester":("capabilities","health"),"grid":("capabilities","health"),"supervisor":("capabilities","health","status")}

def validate_response(name, endpoint, http_status, payload):
    if name not in EXPECTED or endpoint not in ROUTES[name]:
        raise ContractError("unknown source or endpoint")
    if type(http_status) is not int or http_status not in (200,503):
        raise ContractError("unsupported status")
    if not isinstance(payload,dict):
        raise ContractError("invalid payload")
    version=payload.get("api_version")
    if not isinstance(version,dict) or type(version.get("major")) is not int or version["major"]!=1 or type(version.get("minor")) is not int or version["minor"]!=0:
        raise ContractError("incompatible API")
    if payload.get("producer")!=EXPECTED[name] or payload.get("read_only") is not True:
        raise ContractError("producer identity mismatch")
    if payload.get("status") not in ("AVAILABLE","UNAVAILABLE"):
        raise ContractError("unknown source state")
    if http_status==503 and payload["status"]!="UNAVAILABLE":
        raise ContractError("false available")
    if endpoint=="health" and name in ("grid","strattester") and payload["status"]!="UNAVAILABLE":
        raise ContractError("source provenance not qualified")
    if name=="supervisor" and (payload.get("trading_authorized") is not False or payload.get("physical_acceptance")!="NOT_RUN"):
        raise ContractError("unexpected authority")
    return {"name":name,"endpoint":endpoint,"contract":"V1_SHAPE_VALID","source_provenance":"UNVERIFIED","production_ready":False}
