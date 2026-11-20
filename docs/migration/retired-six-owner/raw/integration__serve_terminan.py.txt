"""Disposable loopback actual Terminan server, no production configuration."""
import os
from pathlib import Path
import shutil
import sys
import socket

source=Path(os.environ['FIVE_TERMINAN']).resolve()
evidence=Path(os.environ['FIVE_EVIDENCE']).resolve()
shutil.copyfile(evidence/'lifecycle-0.json',evidence/'current.json')
os.environ['TERMINAN_LIFECYCLE_SNAPSHOT']=str(evidence/'current.json')
os.environ['TERMINAN_HOST']='127.0.0.1'
os.environ['TERMINAN_PORT']='18765'
for key in ('TERMINAN_GRID_DSN','TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB'):
    os.environ.pop(key,None)
sys.path.insert(0,str(source))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from terminan.server import Handler, ThreadingHTTPServer
from integration.source_guard import SourceFence
import terminan.server
fence=SourceFence(source,isolated_cache=sys.pycache_prefix);fence.check();fence.module(terminan.server)

class FaultTransport(Handler):
    """Test-only transport seam; normal requests use the actual source handler."""
    def handle_one_request(self):
        if (evidence/'disconnect.flag').exists():
            self.close_connection=True
            try:self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            return
        return super().handle_one_request()

server=ThreadingHTTPServer(('127.0.0.1',18765),FaultTransport)
try:server.serve_forever()
finally:server.server_close()
