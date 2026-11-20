"""Closed phase diagnostics for the hosted crash-before-commit child."""
import json
from pathlib import Path
PHASES=('ENTRY','IMPORT_BEGIN','IMPORT_END','JOURNAL_OPEN','PREPARE_BEGIN','CRASH_HOOK','RETURNED_WITHOUT_CRASH')
CRASH_CODE = r'''
import json, os, sys
from pathlib import Path
phase_path=Path(sys.argv[4])
def phase(value):
    with phase_path.open('a',encoding='ascii') as stream:
        stream.write(value+'\n');stream.flush()
phase('ENTRY')
sys.path.insert(0,sys.argv[1])
phase('IMPORT_BEGIN')
from scheduler_components.durable import PreparationJournal
from scheduler_components.placement import Candidate, Resources, Policy
phase('IMPORT_END')
store=PreparationJournal(sys.argv[2])
phase('JOURNAL_OPEN')
scope=json.loads(sys.argv[3])
def crash(*args):
    phase('CRASH_HOOK')
    os._exit(23)
store._event=crash
node=Candidate('node-a','process-a','process-a',90,'bench-v1',Resources(100,100,100,100,100),Resources(0,0,0,0,0))
phase('PREPARE_BEGIN')
store.prepare(scope,[node],100,Policy(10,800000,1,1),quorum_available=True,schedule_active=True)
phase('RETURNED_WITHOUT_CRASH')
'''
def build_command(executable, root, database, scope, phases, cache):
    return [str(executable),'-I','-S','-B','-X','pycache_prefix='+str(cache),'-c',CRASH_CODE,str(root),str(database),json.dumps(scope),str(phases)]
def phase_summary(path):
    path=Path(path)
    if not path.exists():return 'ENTRY_NOT_OBSERVED'
    if path.is_symlink() or not path.is_file():return 'INVALID_PHASE_RECORD'
    with path.open('rb') as stream:raw=stream.read(513)
    if len(raw)>512:return 'INVALID_PHASE_RECORD'
    try:values=raw.decode('ascii').splitlines()
    except UnicodeError:return 'INVALID_PHASE_RECORD'
    if not values or any(value not in PHASES for value in values) or len(values)>len(PHASES):return 'INVALID_PHASE_RECORD'
    return ','.join(values)
