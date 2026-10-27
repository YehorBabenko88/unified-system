"""Conservative read-only provenance v1.1 adapter.

Canonical digest equality is integrity only; no producer authenticity is inferred.
"""
import hashlib
import json
import re
from .contracts import ContractError

HEX40=re.compile(r"[0-9a-f]{40}\Z")
HEX64=re.compile(r"[0-9a-f]{64}\Z")

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def qualify_historical(record, admitted=()):
    denied={"status":"UNAVAILABLE","reason":"HISTORICAL_PROVENANCE_UNQUALIFIED","trading_authorized":False}
    if not isinstance(record,dict):
        return denied
    try:
        version=record["api_version"]
        if type(version.get("major")) is not int or type(version.get("minor")) is not int or version!={"major":1,"minor":1}:
            return dict(denied,reason="INCOMPATIBLE_RECORD_VERSION")
        if record.get("producer")!="strattester" or record.get("mode")!="HISTORICAL" or record.get("execution_authority") is not False:
            return denied
        revision=record["source_revision"]; receipt=record["completion_receipt"]; dataset=record["dataset"]
        if type(revision) is not str or not HEX40.fullmatch(revision) or type(receipt) is not str or not HEX64.fullmatch(receipt):
            return denied
        if type(dataset.get("fingerprint")) is not str or not HEX64.fullmatch(dataset["fingerprint"]):
            return denied
        if dataset.get("coverage")!="COMPLETE" or dataset.get("missing_data")!=[]:
            return dict(denied,reason="GAP")
        if receipt!=_digest({k:v for k,v in record.items() if k!="completion_receipt"}):
            return dict(denied,reason="RECEIPT_INTEGRITY_FAILED")
        pin=(record["producer_identity"],revision,record["run_id"],receipt)
        if pin not in admitted:
            return dict(denied,reason="OWNER_RECEIPT_NOT_ADMITTED")
        # This adapter intentionally does not reproduce the full source-owned
        # input-snapshot oracle; do not label the record QUALIFIED or READY.
        return {"status":"UNAVAILABLE","reason":"SOURCE_ORACLE_NOT_INDEPENDENTLY_VERIFIED",
                "receipt_integrity":"PASS","owner_pin":"MATCHED",
                "trading_authorized":False}
    except (KeyError,TypeError,ValueError,OverflowError,RecursionError,AttributeError):
        return denied

def inspect_grid_snapshot(payload):
    denied={"status":"UNAVAILABLE","reason":"GRID_PROVENANCE_UNQUALIFIED","trading_authorized":False}
    if not isinstance(payload,dict) or payload.get("producer")!="bybit-cluster-grid":
        return denied
    version=payload.get("api_version")
    if not isinstance(version,dict) or type(version.get("major")) is not int or version.get("major")!=1:
        return denied
    if type(version.get("minor")) is not int or version["minor"]!=1:
        return denied
    status=payload.get("status")
    if status not in ("PARTIAL","STALE","GAP","UNAVAILABLE"):
        return dict(denied,reason="UNATTESTED_AVAILABLE_FORBIDDEN")
    return {"status":status,"reason":payload.get("reason") if type(payload.get("reason")) is str else "SOURCE_UNQUALIFIED",
            "trading_authorized":False,"market_truth":"NOT_ATTESTED"}
