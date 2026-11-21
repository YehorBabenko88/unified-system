"""Actual pinned Unified WSGI -> pinned Terminan dashboard over disposable HTTP."""
import pathlib
import sys
import threading
from unittest.mock import patch
from wsgiref.simple_server import make_server,WSGIRequestHandler
from unified_system.status_api import ReadOnlySupervisorApp

class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass

def main(root):
    root=pathlib.Path(root).resolve()
    sys.path.insert(0,str(root))
    try:
        from terminan.consumer import dashboard
        server=make_server("127.0.0.1",0,ReadOnlySupervisorApp(lambda:{"state":"BLOCKED"}),handler_class=Quiet)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with patch.dict("os.environ",{"TERMINAN_SUPERVISOR_CONTRACT_PORT":str(server.server_port)}):
                with patch("terminan.consumer.all_sources",return_value={"sources":{}}):
                    result=dashboard("BTCUSDT")
            assert result["supervisor"]["state"]=="BLOCKED",result["supervisor"]
            assert result["supervisor"]["provenance"]=="UNVERIFIED"
            assert result["trading_authorized"] is False
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)
            assert not thread.is_alive()
    finally:
        sys.path.pop(0)
    print("ACTUAL_UNIFIED_TO_TERMINAN_LOOPBACK_PASS")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("expected Terminan checkout")
    main(sys.argv[1])
