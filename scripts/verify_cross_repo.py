"""Disposable source-code contract smoke; no live network services or databases."""
import importlib.util
import json
import pathlib
import sys

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,str(path))
    if spec is None or spec.loader is None:raise RuntimeError("source module unavailable")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def wsgi(app,path):
    capture={}
    def start(status,headers):
        capture["status"]=int(status.split()[0])
    data=b"".join(app({"REQUEST_METHOD":"GET","PATH_INFO":path,"QUERY_STRING":""},start))
    return capture["status"],json.loads(data)

def main(root):
    root=pathlib.Path(root).resolve()
    strat=load("strat_readonly_contract",root/"strattester"/"strattester"/"readonly_api.py")
    grid=load("grid_readonly_contract",root/"grid"/"grid"/"terminan_gateway.py")
    from unified_system.status_api import ReadOnlySupervisorApp
    status,s=wsgi(strat.ReadOnlyResultsApp(),"/internal/v1/health")
    assert status==503 and s["status"]=="UNAVAILABLE" and s["producer"]=="strattester"
    g=grid.qualified_snapshot("/internal/v1/capabilities","BTCUSDT",1)
    assert g["producer"]=="bybit-cluster-grid" and g["status"]=="UNAVAILABLE"
    status,u=wsgi(ReadOnlySupervisorApp(),"/internal/v1/health")
    assert status==503 and u["status"]=="UNAVAILABLE" and u["trading_authorized"] is False
    from unified_system.compatibility import validate_response
    validate_response("strattester","health",503,s)
    validate_response("grid","health",503,g)
    validate_response("supervisor","health",503,u)
    print(json.dumps({"contract":"source-code-smoke-v1","strattester":"UNAVAILABLE","grid":"UNAVAILABLE",
                      "supervisor":"UNAVAILABLE","production_ready":False},sort_keys=True))

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: verify_cross_repo.py CHECKOUT_ROOT")
    main(sys.argv[1])
