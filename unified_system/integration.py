"""Pure offline three-module integration demo; never contacts live sources."""
from .contracts import ContractError, seal
from .coordinator import Coordinator
from .report import build_report

def synthetic_pipeline(journal_path, *, modules=("strattester","grid","terminan")):
    coordinator=Coordinator(journal_path,modules)
    coordinator.initialize()
    coordinator.preflight()
    dataset="a"*64
    envelope={"schema_version":1,"producer":"strattester","run_id":"offline-demo-001","dataset_fingerprint":dataset,"status":"SEALED","capabilities":["historical_research"],"payload":{"fixture":"historical_only"}}
    envelope["sha256"]=seal(envelope)
    coordinator.accept(envelope,dataset)
    state=coordinator.observe()
    def snapshot(name):
        return {"source":name,"status":"READY","timestamp_ms":1700000000000,"items":[{"fixture":True}],"synthetic":True}
    report=build_report(strattester=snapshot("strattester") if "strattester" in modules else None,grid=snapshot("grid") if "grid" in modules else None)
    return {"lifecycle":state,"dashboard":report,"terminan_connected":False,"mode":"OFFLINE_SYNTHETIC_ONLY"}
