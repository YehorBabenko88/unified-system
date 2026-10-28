"""Pinned source contract fixture validator; never executes imported source code."""
from .contracts import ContractError
from .compatibility import validate_response

PINNED = {
    "strattester": "943095d00d5d56276f3832c42b36b290bea77a84",
    "grid": "bf9f108b6777085d6725675eac778d61ec55f42b",
}

def inspect_source_envelope(name, response, *, source_sha):
    if name not in PINNED or source_sha != PINNED[name]:
        raise ContractError("source revision not pinned")
    if not isinstance(response, dict):
        raise ContractError("invalid source response")
    status=response.get("status")
    if status not in ("UNAVAILABLE","AVAILABLE"):
        raise ContractError("invalid response status")
    result=validate_response(name,"health",503 if status=="UNAVAILABLE" else 200,response)
    return {"source":name,"source_sha":source_sha,"contract":result["contract"],
            "source_provenance":"UNVERIFIED","production_ready":False}
