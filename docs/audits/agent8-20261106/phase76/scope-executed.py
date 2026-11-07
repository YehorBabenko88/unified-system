import sys,pathlib,tempfile,hashlib,json
sys.path[:0]=[str(pathlib.Path.cwd()),str(pathlib.Path.cwd()/'tests')]
from test_node_task_journal import operation
from unified_system.node_task_journal import NodeTaskJournal,NodeJournalError
from unified_system.node_supervisor_v2 import NodeSupervisorV2
with tempfile.TemporaryDirectory() as d:
 path=pathlib.Path(d)/'pc1.db';j=NodeTaskJournal(path,cluster_id='cluster1',node_id='PC1',node_incarnation='inc1');j.create(operation(node_id='PC1'));before=path.read_bytes()
 for scope in [dict(cluster_id='cluster1',node_id='LS5',node_incarnation='inc1'),dict(cluster_id='other',node_id='PC1',node_incarnation='inc1'),dict(cluster_id='cluster1',node_id='PC1',node_incarnation='other')]:
  try:NodeSupervisorV2(j,**scope);raise AssertionError('foreign supervisor accepted')
  except NodeJournalError:pass
  try:NodeTaskJournal(path,**scope);raise AssertionError('foreign journal accepted')
  except NodeJournalError:pass
 assert path.read_bytes()==before and j.get('task1')['state']=='CREATED'
 print(json.dumps(dict(foreign_node_cluster_incarnation_constructor_refusals=6,original_PC1_task='CREATED',file_bytes_unchanged=True,sha256=hashlib.sha256(before).hexdigest(),scope='OWN_SYNTHETIC_LOCAL_JOURNAL_ONLY'),indent=2))
