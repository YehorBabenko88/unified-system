"""Disposable deterministic local receipt supervisor; all native effects unavailable."""
from .node_task_journal import NodeTaskJournal, need, identifier

class NodeSupervisorV2:
    def __init__(self,journal,*,node_id,node_incarnation,cluster_id):
        need(type(journal) is NodeTaskJournal)
        for value in (node_id,node_incarnation,cluster_id): identifier(value)
        self.journal=journal
        self.identity=dict(node_id=node_id,node_incarnation=node_incarnation,cluster_id=cluster_id)

    def submit(self,intent):
        need(type(intent) is dict and all(intent.get(key)==value for key,value in self.identity.items()))
        return self.journal.create(intent)

    def inspect(self,task_id):
        return self.journal.get(task_id)

    def reconcile(self):
        return self.journal.reconcile()

    def run_readonly(self,task_id):
        record=self.journal.get(task_id)
        need(all(record['intent'][key]==value for key,value in self.identity.items()))
        receipt=dict(code='LOCAL_RECEIPTS_ONLY',authority='UNKNOWN',source='UNKNOWN',freshness='UNKNOWN',effects_authorized=False,journal_integrity='PASS',physical_acceptance='NOT_RUN')
        # No authority argument, callback, executor, serialized fence or service call.
        if record['state'] in ('COMPLETED','BLOCKED','FAILED','INTERRUPTED','RECOVERY_REQUIRED','ROLLBACK_REQUIRED','CANCELLED','UNKNOWN_OUTCOME'):
            return record
        if record['intent']['operation_type'] not in ('REPORT_STATUS','CHECK_HEALTH'):
            receipt['code']='PLAN_ONLY_NATIVE_AUTHORITY_UNAVAILABLE'
            return self.journal.transition(task_id,'BLOCKED',receipt)
        if record['state']!='CREATED':
            return self.journal.transition(task_id,'BLOCKED',dict(receipt,code='RECONCILIATION_REQUIRED'))
        if any(item['expected']!='PASS' for item in record['intent']['preconditions']+record['intent']['expected_postconditions']):
            return self.journal.transition(task_id,'BLOCKED',dict(receipt,code='CONDITION_UNPROVEN'))
        # AUTHORIZED is a recorded lifecycle label only. No effect admission follows.
        for state in ('VERIFIED','AUTHORIZED','PREPARED','RUNNING','VERIFYING','COMPLETED'):
            record=self.journal.transition(task_id,state,receipt)
        return record
