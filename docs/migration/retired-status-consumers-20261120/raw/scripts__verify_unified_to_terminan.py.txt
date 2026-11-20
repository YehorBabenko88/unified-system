"""Actual Terminan presentation of conservative Unified synthetic provenance."""
import pathlib
import sys
from unified_system.provenance_v11 import inspect_grid_snapshot,qualify_historical

def main(root):
    root=pathlib.Path(root).resolve()
    sys.path.insert(0,str(root))
    try:
        from terminan.consumer import present_source
        grid=inspect_grid_snapshot({"api_version":{"major":1,"minor":1},
             "producer":"bybit-cluster-grid","status":"PARTIAL",
             "reason":"EXCHANGE_COMPLETENESS_UNATTESTED"})
        assert grid["status"]=="PARTIAL"
        view={"version":1,"authority":"AGGREGATED_HISTORY_NOT_L2",
              "state":grid["status"],"coverage":{"verified":False}}
        rendered=present_source(view)
        assert rendered["state"]=="GAP" and rendered["provenance"]=="AGGREGATED_HISTORY_NOT_L2"
        denied=qualify_historical({})
        assert denied["status"]=="UNAVAILABLE"
        unavailable=present_source({"version":1,"authority":"HISTORICAL_ONLY",
             "state":"UNAVAILABLE","coverage":{"verified":False}})
        assert unavailable["state"]=="UNAVAILABLE"
    finally:
        sys.path.pop(0)
    print("UNIFIED_TO_TERMINAN_SYNTHETIC_STATUS_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected Terminan checkout")
    main(sys.argv[1])
