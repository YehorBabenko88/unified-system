"""Pure offline supervisor; intentionally no process-launch methods."""
from .contracts import validate_handoff, ContractError
from .module_catalog import MODULE_IDS

class Supervisor:
    def __init__(self, installed=()):
        self.installed = frozenset(installed)
        if not self.installed <= MODULE_IDS:
            raise ContractError("unknown module")
        self.state = "INSTALLED"
        self.receipt = None

    def preflight(self):
        self.state = "INFRA_READY"
        return self.snapshot()

    def accept_research(self, envelope, expected_dataset):
        if self.state != "INFRA_READY" or "terminan" not in self.installed:
            self.state = "BLOCKED"
            raise ContractError("research producer unavailable or preflight missing")
        try:
            self.receipt = validate_handoff(envelope, expected_dataset)
        except ContractError:
            self.state = "BLOCKED"
            raise
        self.state = "HANDOFF_VERIFIED"
        return self.snapshot()

    def observe(self):
        if self.state != "HANDOFF_VERIFIED":
            self.state = "BLOCKED"
            raise ContractError("unverified handoff")
        self.state = "OBSERVING" if {"market_data", "terminan"} <= self.installed else "DEGRADED"
        return self.snapshot()

    def snapshot(self):
        return {"state":self.state, "modules":{name:("AVAILABLE" if name in self.installed else "UNAVAILABLE") for name in sorted(MODULE_IDS)}, "receipt":self.receipt, "trading_authorized":False, "physical_acceptance":"NOT_RUN"}
