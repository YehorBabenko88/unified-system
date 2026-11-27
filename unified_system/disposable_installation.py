"""Agent I: disposable inactive installation rehearsal, not a service installer.

This small orchestration adapter reuses the existing owned inactive capsule
transaction. It does not grant host authority or execute service, PostgreSQL,
network, Consul, launcher, migration or uninstall effects.

Every operation is closed and bound to a separately approved disposable
workspace. Unknown outcomes remain retained and unadopted. Never use this
module to claim a trusted release, physical acceptance or production GO.
"""
import copy
import tempfile
from pathlib import Path

from .installation_transaction import InstallationTransaction, source_plan


SCHEMA = "unified.disposable-installation.v1"
OPERATIONS = frozenset(("PREVIEW", "STAGE", "OBSERVE", "ROLLBACK", "UNINSTALL_PREVIEW", "DISPOSE_INACTIVE"))


def _need(ok):
    if not ok:
        raise ValueError("DISPOSABLE_INSTALLATION_REJECTED")


class DisposableInstallation:
    """Non-activating wrapper over the original journal-backed staging owner."""

    def __init__(self, plan):
        self._plan = copy.deepcopy(plan)
        # Enforce the existing closed plan schema on every construction.
        from .installation_transaction import validate_plan
        self._plan = validate_plan(self._plan)

    @classmethod
    def from_capsule(cls, *, capsule_root, install_root, state_root,
                     installation_id, node_id, operation_id, role,
                     manifest_sha256):
        return cls(source_plan(
            capsule_root=capsule_root, install_root=install_root,
            state_root=state_root, installation_id=installation_id,
            node_id=node_id, operation_id=operation_id, role=role,
            manifest_sha256=manifest_sha256))

    @property
    def plan(self):
        return copy.deepcopy(self._plan)

    def preview(self):
        """Read existing state only; no directory creation or service calls."""
        _need(not Path(self._plan["state_root"]).exists())
        _need(not Path(self._plan["install_root"]).exists())
        return {
            "schema": SCHEMA,
            "mode": "DISPOSABLE_INACTIVE_ONLY",
            "manifest_sha256": self._plan["manifest_sha256"],
            "installation_id": self._plan["installation_id"],
            "operation_id": self._plan["operation_id"],
            "owned_paths": [self._plan["install_root"], self._plan["state_root"]],
            "activation": "BLOCKED",
            "service_creation": False,
            "postgresql_effect": False,
            "consul_effect": False,
            "cleanup_effect": False,
            "execution_authority": False,
            "physical_acceptance": "NOT_RUN",
        }

    def _open(self):
        # Existing journal is authoritative for this local rehearsal; never
        # adopt a foreign installation or overwrite an unreceipted path.
        return InstallationTransaction.open(copy.deepcopy(self._plan))

    def stage(self, *, disposable_approval=False):
        """Stage only immutable code bytes in fresh, explicitly approved roots."""
        _need(disposable_approval is True)
        state = Path(self._plan["state_root"])
        install = Path(self._plan["install_root"])
        if state.exists():
            transaction = self._open()
        else:
            _need(not install.exists())
            transaction = InstallationTransaction.create(copy.deepcopy(self._plan))
        result = transaction.stage()
        _need(result["activation"] == "BLOCKED")
        _need(result["execution_authority"] is False)
        _need(result["physical_acceptance"] == "NOT_RUN")
        return result

    def observe(self):
        """Resume inspection never runs a child or retries an uncertain stage."""
        return self._open().snapshot()

    def rollback(self, *, disposable_approval=False):
        """Original logical rollback retains all bytes for manual examination."""
        _need(disposable_approval is True)
        result = self._open().rollback()
        _need(result["status"] == "ROLLED_BACK_RETAINED")
        _need(result["activation"] == "BLOCKED")
        return result

    def uninstall_preview(self):
        """No full uninstall for a non-serviced staged capsule.

        Removal belongs to the existing separately approved APP_ONLY
        Uninstaller and its service ownership receipts. An inactive
        InstallationTransaction is not a Windows service receipt.
        """
        result = self.observe()
        return {
            "schema": SCHEMA,
            "status": "DENIED_NO_OWNED_SERVICE_REMOVAL_RECEIPT",
            "transaction_receipt_sha256": result["transaction_receipt_sha256"],
            "stage_status": result["status"],
            "removes_code": False,
            "removes_state": False,
            "removes_postgresql": False,
            "execution_authority": False,
        }

    def dispose_inactive(self, *, disposable_approval=False, fail_after_members=None):
        """Test-workspace-only removal of verified inactive code, never state.

        Preserves the original installation ownership journal and application
        state; ambiguous disposal blocks retries pending manual inspection.
        """
        _need(disposable_approval is True)
        result = self._open().dispose_inactive(
            approved_disposable=True, fail_after_members=fail_after_members)
        _need(result["activation"] == "BLOCKED")
        _need(result["execution_authority"] is False)
        return result

    def execute(self, operation, *, disposable_approval=False):
        _need(type(operation) is str and operation in OPERATIONS)
        if operation == "PREVIEW":
            return self.preview()
        if operation == "STAGE":
            return self.stage(disposable_approval=disposable_approval)
        if operation == "OBSERVE":
            return self.observe()
        if operation == "ROLLBACK":
            return self.rollback(disposable_approval=disposable_approval)
        if operation == "DISPOSE_INACTIVE":
            return self.dispose_inactive(disposable_approval=disposable_approval)
        return self.uninstall_preview()
