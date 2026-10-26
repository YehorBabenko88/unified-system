"""Offline-only synthetic smoke demonstration."""
import argparse
import json
from .contracts import seal
from .supervisor import Supervisor

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", required=True)
    args=parser.parse_args()
    dataset="a"*64
    envelope={"schema_version":1,"producer":"strattester","run_id":"synthetic-001","dataset_fingerprint":dataset,"status":"SEALED","capabilities":["historical_research"],"payload":{"research_only":True}}
    envelope["sha256"]=seal(envelope)
    s=Supervisor(("strattester","grid","terminan"))
    s.preflight();s.accept_research(envelope,dataset)
    print(json.dumps(s.observe(),sort_keys=True,indent=2))

if __name__ == "__main__":
    main()
