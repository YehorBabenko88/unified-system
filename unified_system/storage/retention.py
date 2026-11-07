"""Pure conservative candidate planner. It cannot authorize or execute any mutation."""
from dataclasses import dataclass

from .contracts import digest, identifier, require
from .segments import ByteCheck


@dataclass(frozen=True)
class ReplicaClaim:
    replica_id: str
    node_id: str
    volume_id: str
    byte_check: ByteCheck | None
    available: bool

    def __post_init__(self):
        for value in (self.replica_id, self.node_id, self.volume_id):
            identifier(value)
        require(type(self.available) is bool)
        require(self.byte_check is None or type(self.byte_check) is ByteCheck)
        if self.byte_check is not None:
            require(self.byte_check.authority_verified is False)


@dataclass(frozen=True)
class RetentionFacts:
    object_sha256: str
    target_replica_id: str
    replicas: tuple[ReplicaClaim, ...]
    min_survivors: int
    age_eligible: bool
    closure_complete: bool
    research_pins: tuple[str, ...]
    dependency_pins: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    active_upload: bool

    def __post_init__(self):
        digest(self.object_sha256)
        identifier(self.target_replica_id)
        require(type(self.min_survivors) is int and 1 <= self.min_survivors <= 32)
        require(type(self.replicas) is tuple and len(self.replicas) <= 32)
        require(all(type(replica) is ReplicaClaim for replica in self.replicas))
        require(len({replica.replica_id for replica in self.replicas}) == len(self.replicas), "DUPLICATE_REPLICA_ID")
        for flag in (self.age_eligible, self.closure_complete, self.active_upload):
            require(type(flag) is bool)
        for pins in (self.research_pins, self.dependency_pins, self.unresolved_gaps):
            require(type(pins) is tuple and len(pins) <= 32)
            for pin in pins:
                identifier(pin)


@dataclass(frozen=True)
class RetentionPlan:
    decision: str
    target_replica_id: str
    byte_matched_survivor_claims: int
    reasons: tuple[str, ...]

    @property
    def executable(self):
        return False


def plan_retention(facts: RetentionFacts) -> RetentionPlan:
    """Plan against untrusted supplied facts only; never calls an executor or authority."""
    require(type(facts) is RetentionFacts)
    reasons = []
    for blocked, reason in ((not facts.age_eligible, "RETENTION_NOT_ELAPSED"),
                            (not facts.closure_complete, "CLOSURE_UNKNOWN"),
                            (bool(facts.research_pins), "ACTIVE_RESEARCH_PIN"),
                            (bool(facts.dependency_pins), "DEPENDENCY_PIN"),
                            (bool(facts.unresolved_gaps), "UNRESOLVED_GAPS"),
                            (facts.active_upload, "ACTIVE_UPLOAD")):
        if blocked:
            reasons.append(reason)
    if not any(replica.replica_id == facts.target_replica_id for replica in facts.replicas):
        reasons.append("TARGET_UNKNOWN")
    # Same node OR same volume cannot supply two independent candidate copies.
    nodes, volumes = set(), set()
    matches = 0
    for replica in facts.replicas:
        evidence = replica.byte_check
        if (replica.replica_id == facts.target_replica_id or not replica.available or evidence is None
                or evidence.sha256 != facts.object_sha256 or replica.node_id in nodes or replica.volume_id in volumes):
            continue
        nodes.add(replica.node_id)
        volumes.add(replica.volume_id)
        matches += 1
    if matches < facts.min_survivors:
        reasons.append("LAST_COPY_OR_POLICY_PROTECTED")
    decision = "KEEP" if reasons else "QUARANTINE_CANDIDATE"
    # Even an attractive candidate is NOT Verified Delete or a quarantine permission.
    reasons.append("ACTUAL_AUTHORITY_PROOF_UNAVAILABLE")
    return RetentionPlan(decision, facts.target_replica_id, matches, tuple(reasons))
