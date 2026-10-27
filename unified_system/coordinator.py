"""Offline lifecycle coordinator with explicit journal transitions."""
from .contracts import ContractError, validate_handoff
from .journal import Journal
from .supervisor import Supervisor

class Coordinator:
    def __init__(self, path, installed):
        self.journal=Journal(path)
        self.supervisor=Supervisor(installed)

    def initialize(self):
        self.journal.initialize()
        records=self.journal.read()
        if not records:
            self.journal.append("INSTALLED")
        elif records[-1]["state"] != "INSTALLED":
            # Recovery is read-only; do not silently resume operations.
            self.supervisor.state="BLOCKED"
        return self.snapshot()

    def preflight(self):
        if self.supervisor.state != "INSTALLED":
            raise ContractError("explicit recovery required")
        self.supervisor.preflight()
        self.journal.append("INFRA_READY")
        return self.snapshot()

    def accept(self, envelope, expected_dataset):
        if self.supervisor.state != "INFRA_READY":
            raise ContractError("invalid lifecycle")
        try:
            receipt=validate_handoff(envelope,expected_dataset)
        except ContractError:
            self.supervisor.state="BLOCKED"
            self.journal.append("BLOCKED")
            raise
        self.journal.append("HANDOFF_VERIFIED",receipt)
        self.supervisor.receipt=receipt
        self.supervisor.state="HANDOFF_VERIFIED"
        return self.snapshot()

    def observe(self):
        if self.supervisor.state != "HANDOFF_VERIFIED":
            raise ContractError("handoff not verified")
        state="OBSERVING" if {"grid","terminan"} <= self.supervisor.installed else "DEGRADED"
        self.journal.append(state,self.supervisor.receipt)
        self.supervisor.state=state
        return self.snapshot()

    def snapshot(self):
        result=self.supervisor.snapshot()
        result["journal_records"]=len(self.journal.read())
        result["recovery"]="MANUAL_REVIEW_REQUIRED" if result["state"]=="BLOCKED" else "NONE"
        return result
