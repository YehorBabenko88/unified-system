"""Pinned source-owned A->B->C synthetic integration; no real market data."""
import pathlib
import sys
import uuid

def main(root):
    root=pathlib.Path(root).resolve()
    sys.path.insert(0,str(root/"strattester"))
    sys.path.insert(0,str(root/"grid"))
    sys.path.insert(0,str(root/"Terminan"))
    try:
        from strattester.research.provenance import digest
        from grid.research_handoff import accept_handoff
        from terminan.consumer import present_source
        record={
            "api_version":{"major":1,"minor":1},"producer":"strattester",
            "producer_identity":"synthetic-chain","source_revision":"a"*40,
            "producer_epoch":str(uuid.uuid4()),"run_id":str(uuid.uuid4()),
            "mode":"HISTORICAL","execution_authority":False,
            "dataset":{"fingerprint":"b"*64,"start_ms":0,"end_ms":60000,
                       "source_identity":"synthetic","market_type":"linear",
                       "symbol":"BTCUSDT","timeframe":"1m","coverage":"COMPLETE","missing_data":[]},
            "strategy":{"id":"synthetic","version":"1","fingerprint":"c"*64,"parameters":{}},
            "model":{"kind":"synthetic","version":"1"},
            "execution_assumptions":{"execution":"synthetic","fees":0.0,"slippage":0.0},
            "metrics":{"synthetic":True},"completed_at_ms":120000}
        record["completion_receipt"]=digest(record)
        pin=(record["producer_identity"],record["source_revision"],record["run_id"],record["completion_receipt"])
        assert accept_handoff(record,())["status"]=="UNAVAILABLE"
        admitted=accept_handoff(record,(pin,))
        assert admitted["status"]=="ACCEPTED_HISTORICAL"
        assert admitted["trading_authorized"] is False
        # Terminan presents the research as historical, not live execution.
        presented=present_source({"version":1,"authority":"HISTORICAL_ONLY",
                                  "state":"HISTORICAL","coverage":{"verified":False}})
        assert presented["state"]=="HISTORICAL"
        assert presented["coverage_verified"] is False
        # No source authenticity, physical admission or order authority is inferred.
        assert presented["runtime_identity"]=="UNVERIFIED"
    finally:
        for _ in range(3):sys.path.pop(0)
    print("PINNED_A_B_C_SYNTHETIC_CHAIN_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected checkout root")
    main(sys.argv[1])
