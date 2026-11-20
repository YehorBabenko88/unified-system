"""Actual pinned Strattester digest + Grid receiver synthetic positive/negative."""
import pathlib
import sys
import uuid

def main(root):
    root=pathlib.Path(root).resolve()
    sys.path.insert(0,str(root/"strattester"))
    sys.path.insert(0,str(root/"grid"))
    try:
        from strattester.research.provenance import digest
        from grid.research_handoff import accept_handoff
        record={
            "api_version":{"major":1,"minor":1},"producer":"strattester",
            "producer_identity":"synthetic-fixture-owner",
            "source_revision":"a"*40,"producer_epoch":str(uuid.uuid4()),
            "run_id":str(uuid.uuid4()),"mode":"HISTORICAL","execution_authority":False,
            "dataset":{"fingerprint":"b"*64,"start_ms":0,"end_ms":60000,
                       "source_identity":"synthetic-only","market_type":"linear",
                       "symbol":"BTCUSDT","timeframe":"1m",
                       "coverage":"COMPLETE","missing_data":[]},
            "strategy":{"id":"synthetic","version":"1","fingerprint":"c"*64,"parameters":{}},
            "model":{"kind":"synthetic","version":"1"},
            "execution_assumptions":{"execution":"synthetic","fees":0.0,"slippage":0.0},
            "metrics":{"fixture":True},"completed_at_ms":120000}
        record["completion_receipt"]=digest(record)
        denied=accept_handoff(record,frozenset())
        assert denied["status"]=="UNAVAILABLE" and denied["execution_authority"] is False
        pin=(record["producer_identity"],record["source_revision"],record["run_id"],record["completion_receipt"])
        accepted=accept_handoff(record,frozenset((pin,)))
        assert accepted["status"]=="ACCEPTED_HISTORICAL" and accepted["trading_authorized"] is False
        mutated=dict(record);mutated["metrics"]={"fixture":False}
        tampered=accept_handoff(mutated,frozenset((pin,)))
        assert tampered["status"]=="UNAVAILABLE" and tampered["reason"]=="RESEARCH_RECEIPT_CORRUPT"
    finally:
        sys.path.pop(0)
        sys.path.pop(0)
    print("SYNTHETIC_PINNED_SOURCE_HANDOFF_ROUNDTRIP_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected checkout root")
    main(sys.argv[1])
