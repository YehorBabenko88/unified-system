"""Bounded ordered offline event cursor; no persistence or networking."""
from .contracts import ContractError

class EventCursor:
    def __init__(self):
        self.epoch = None
        self.sequence = None

    def ingest(self, event):
        if not isinstance(event, dict) or set(event) != {"epoch", "sequence", "payload"}:
            raise ContractError("invalid event")
        epoch, seq = event["epoch"], event["sequence"]
        if type(epoch) is not str or not 1 <= len(epoch) <= 128 or not epoch.isascii() or not all(c.isalnum() or c in "-_." for c in epoch):
            raise ContractError("invalid epoch")
        if type(seq) is not int or not 0 <= seq <= 2**63 - 1:
            raise ContractError("invalid sequence")
        if not isinstance(event["payload"], dict):
            raise ContractError("invalid payload")
        if self.epoch is None:
            self.epoch, self.sequence = epoch, seq
            return "SNAPSHOT_REQUIRED"
        if epoch != self.epoch:
            self.epoch, self.sequence = epoch, seq
            return "SNAPSHOT_REQUIRED"
        if seq <= self.sequence:
            return "DUPLICATE_OR_OLD"
        if seq != self.sequence + 1:
            self.sequence = seq
            return "GAP_SNAPSHOT_REQUIRED"
        self.sequence = seq
        return "APPLIED"
