"""Disposable loopback actual Terminan server, no production configuration."""
import os
from pathlib import Path
import shutil
import sys

source=Path(os.environ['FIVE_TERMINAN']).resolve()
evidence=Path(os.environ['FIVE_EVIDENCE']).resolve()
shutil.copyfile(evidence/'lifecycle-0.json',evidence/'current.json')
os.environ['TERMINAN_LIFECYCLE_SNAPSHOT']=str(evidence/'current.json')
os.environ['TERMINAN_HOST']='127.0.0.1'
os.environ['TERMINAN_PORT']='18765'
for key in ('TERMINAN_GRID_DSN','TERMINAN_STRATTESTER_DB','TERMINAN_RESULTS_DB'):
    os.environ.pop(key,None)
sys.path.insert(0,str(source))
from terminan.server import run
run()
