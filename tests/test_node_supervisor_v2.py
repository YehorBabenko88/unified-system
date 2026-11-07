import tempfile
import unittest
from pathlib import Path
from unified_system.node_supervisor_v2 import NodeSupervisorV2
from unified_system.node_task_journal import NodeTaskJournal, OPERATIONS, NodeJournalError
from test_node_task_journal import operation

class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.journal=NodeTaskJournal(Path(self.tmp.name)/'node.db')
        self.supervisor=NodeSupervisorV2(self.journal,node_id='node1',node_incarnation='inc1',cluster_id='cluster1')

    def test_readonly_durable_completion_and_duplicate(self):
        self.supervisor.submit(operation())
        result=self.supervisor.run_readonly('task1')
        self.assertEqual(result['state'],'COMPLETED')
        self.assertEqual(result['receipt']['authority'],'UNKNOWN')
        self.assertEqual(self.supervisor.run_readonly('task1'),result)
        self.assertEqual(NodeTaskJournal(self.journal.path).reconcile()[0]['state'],'COMPLETED')

    def test_all_other_operations_fail_closed(self):
        for index,kind in enumerate(OPERATIONS-{'REPORT_STATUS','CHECK_HEALTH'}):
            task='task'+str(index)
            self.supervisor.submit(operation(task_id=task,idempotency_key=task,operation_type=kind))
            result=self.supervisor.run_readonly(task)
            self.assertEqual(result['state'],'BLOCKED')
            self.assertFalse(result['receipt']['effects_authorized'])

    def test_identity_mismatch_and_no_proof_injection(self):
        with self.assertRaises(NodeJournalError): self.supervisor.submit(operation(node_id='other'))
        self.supervisor.submit(operation())
        with self.assertRaises(TypeError): self.supervisor.run_readonly('task1',authority=True)

    def test_persisted_authorized_is_not_admission(self):
        self.supervisor.submit(operation(operation_type='PREPARE_INSTALL'))
        for state in ('VERIFIED','AUTHORIZED'): self.journal.transition('task1',state)
        result=self.supervisor.run_readonly('task1')
        self.assertEqual(result['state'],'BLOCKED')
        self.assertFalse(result['receipt']['effects_authorized'])

    def test_interrupted_read_is_not_blindly_replayed(self):
        self.supervisor.submit(operation())
        for state in ('VERIFIED','AUTHORIZED','PREPARED','RUNNING'): self.journal.transition('task1',state)
        self.supervisor.reconcile()
        self.assertEqual(self.supervisor.run_readonly('task1')['state'],'UNKNOWN_OUTCOME')
