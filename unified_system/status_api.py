"""Opt-in WSGI status API. No listener, network client, or execution authority.

API v1 intentionally exposes *only* unqualified control-plane observation.
"""
import json
from .contracts import ContractError

_PATHS = frozenset(("/internal/v1/capabilities", "/internal/v1/health", "/internal/v1/status"))

class ReadOnlySupervisorApp:
    def __init__(self, provider=None):
        self.provider = provider

    def __call__(self, environ, start_response):
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")
        status = 503
        data = {"api_version":{"major":1,"minor":0},
                "producer":"unified-system",
                "read_only":True,"status":"UNAVAILABLE",
                "provenance":"UNVERIFIED",
                "trading_authorized":False,
                "physical_acceptance":"NOT_RUN"}
        if method != "GET":
            status = 405
            data["reason"] = "METHOD_NOT_ALLOWED"
        elif path not in _PATHS:
            status = 404
            data["reason"] = "NOT_FOUND"
        elif environ.get("QUERY_STRING",""):
            status = 400
            data["reason"] = "QUERY_NOT_SUPPORTED"
        elif path == "/internal/v1/capabilities":
            status = 200
            data["status"] = "AVAILABLE"
            data["capabilities"] = {"supervisor_status":True,
                                     "trading":False,
                                     "physical_deployment":False}
        else:
            # No operational transition can be authorized from this API.
            # Snapshot data is never trusted merely because a provider returned it.
            try:
                value = self.provider() if self.provider is not None else None
                if not isinstance(value, dict):
                    data["reason"] = "SUPERVISOR_UNAVAILABLE"
                else:
                    source_state = value.get("state")
                    if source_state not in ("INSTALLED","INFRA_READY","HANDOFF_VERIFIED","OBSERVING","DEGRADED","BLOCKED"):
                        data["reason"] = "INVALID_SUPERVISOR_STATE"
                    else:
                        status = 200
                        data["status"] = "AVAILABLE"
                        data["state"] = source_state
                        data["reason"] = "SOURCE_PROVENANCE_UNQUALIFIED"
            except (OSError, ValueError, ContractError):
                data["reason"] = "SUPERVISOR_UNAVAILABLE"
        body=json.dumps(data,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        labels={200:"OK",400:"Bad Request",404:"Not Found",405:"Method Not Allowed",503:"Service Unavailable"}
        headers=[("Content-Type","application/json"),
                 ("Content-Length",str(len(body))),
                 ("Cache-Control","no-store"),
                 ("X-Content-Type-Options","nosniff")]
        if status == 405:headers.append(("Allow","GET"))
        start_response(str(status)+" "+labels[status],headers)
        return [body]
