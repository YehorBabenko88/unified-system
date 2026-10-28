"""Pinned actual Grid research-handoff negative acceptance; no producer or DB."""
import importlib.util
import pathlib
import sys

def main(root):
    root=pathlib.Path(root).resolve()
    # Import real source-owned Grid handoff implementation without changing it.
    sys.path.insert(0,str(root/"grid"))
    try:
        from grid.research_handoff import accept_handoff
        result=accept_handoff({},frozenset())
        assert result["status"]=="UNAVAILABLE" and result["execution_authority"] is False
        spoof={"api_version":{"major":1,"minor":1},"producer":"strattester",
               "run_id":"00000000-0000-4000-8000-000000000001",
               "mode":"HISTORICAL","execution_authority":False,
               "producer_identity":"spoof","source_revision":"a"*40,
               "completion_receipt":"b"*64}
        result=accept_handoff(spoof,frozenset())
        assert result["status"]=="UNAVAILABLE" and result["reason"]=="SOURCE_IDENTITY_UNATTESTED"
        assert result.get("trading_authorized") is not True
    finally:
        sys.path.pop(0)
    print("PINNED_GRID_HANDOFF_NEGATIVE_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected checkout root")
    main(sys.argv[1])
