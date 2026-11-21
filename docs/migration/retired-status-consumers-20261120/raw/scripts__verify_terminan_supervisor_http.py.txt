"""Pinned Terminan consumer contract against disposable Unified HTTP source.

Terminan PR22 currently exposes source_contract only for Grid/Strattester.
This script proves that the source-owned consumer rejects the Supervisor's
different producer identity rather than falsely declaring it qualified.
"""
import pathlib
import sys
import threading
from wsgiref.simple_server import make_server, WSGIRequestHandler
from unified_system.status_api import ReadOnlySupervisorApp

class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass

def main(root):
    root=pathlib.Path(root).resolve()
    sys.path.insert(0,str(root))
    try:
        from terminan import consumer
        app=ReadOnlySupervisorApp(lambda:{"state":"BLOCKED"})
        server=make_server("127.0.0.1",0,app,handler_class=Quiet)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            import os
            old=os.environ.get("TERMINAN_GRID_CONTRACT_PORT")
            os.environ["TERMINAN_GRID_CONTRACT_PORT"]=str(server.server_port)
            try:
                response=consumer.source_contract("grid")
                assert response["state"]=="UNAVAILABLE"
                assert response["reason"]=="SOURCE_CONTRACT_INVALID_OR_UNAVAILABLE"
            finally:
                if old is None:os.environ.pop("TERMINAN_GRID_CONTRACT_PORT",None)
                else:os.environ["TERMINAN_GRID_CONTRACT_PORT"]=old
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
            assert not thread.is_alive()
    finally:
        sys.path.pop(0)
    print("PINNED_TERMINAN_REJECTS_WRONG_PRODUCER_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected checkout")
    main(sys.argv[1])
