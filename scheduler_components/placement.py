"""Pure advisory placement. CPU uses one explicitly matched benchmark scale.

RAM/scratch are bytes; disk/network are bytes/second. Scratch is worker-local
working space, not Storage replica capacity. No lease or reservation is issued.
"""
from dataclasses import dataclass, fields
from fractions import Fraction

@dataclass(frozen=True)
class Resources:
    cpu: int
    ram: int
    scratch: int
    disk_bps: int
    network_bps: int

@dataclass(frozen=True)
class Candidate:
    node_id: str
    incarnation: str
    observation_incarnation: str
    observed_ms: int
    benchmark_id: str
    capacity: Resources
    reserved: Resources
    pressure_ppm: int = 0
    healthy: bool = True
    mode: str = 'ACTIVE'
    worker_role: bool = True
    data: frozenset = frozenset()

@dataclass(frozen=True)
class Policy:
    max_age_ms: int
    max_pressure_ppm: int
    utilization_weight: int
    locality_weight: int

@dataclass(frozen=True)
class Decision:
    candidate: str | None
    rejections: tuple

def place(request, benchmark_id, data, candidates, now_ms, policy):
    """Rank eligible snapshots deterministically; caller must later obtain authority.

    Every configured threshold/weight is required. Freshness assumes exact caller
    time for this isolated component; authoritative commit-time validation remains
    gated. Available = capacity - already reserved in each independent dimension.
    """
    dimensions = tuple(f.name for f in fields(Resources))

    def resource_values(value):
        if not isinstance(value, Resources):
            raise ValueError('typed resource vector required')
        result = tuple(getattr(value, key) for key in dimensions)
        if any(type(v) is not int or v < 0 for v in result):
            raise ValueError('resources must be nonnegative integers')
        return result

    requested = resource_values(request)
    if not any(requested) or type(now_ms) is not int or now_ms < 0:
        raise ValueError('nonempty request and nonnegative integer time required')
    if not isinstance(policy, Policy):
        raise ValueError('typed policy required')
    if (any(type(v) is not int for v in (policy.max_age_ms, policy.max_pressure_ppm,
                                        policy.utilization_weight, policy.locality_weight))
            or policy.max_age_ms <= 0 or not 0 <= policy.max_pressure_ppm <= 1000000
            or policy.utilization_weight < 0 or policy.locality_weight < 0
            or policy.utilization_weight + policy.locality_weight == 0):
        raise ValueError('invalid policy')
    if not isinstance(benchmark_id, str) or not benchmark_id or not isinstance(data, frozenset):
        raise ValueError('explicit benchmark and immutable data identity set required')
    ranked, rejected, identities = [], [], set()
    for node in candidates:
        if not isinstance(node, Candidate):
            raise ValueError('typed candidate required')
        if (any(not isinstance(v, str) or not v for v in (node.node_id, node.incarnation,
                node.observation_incarnation, node.benchmark_id)) or node.node_id in identities):
            raise ValueError('unique candidate identity required')
        identities.add(node.node_id)
        capacity, reserved = resource_values(node.capacity), resource_values(node.reserved)
        if (type(node.observed_ms) is not int or node.observed_ms < 0
                or type(node.pressure_ppm) is not int or not 0 <= node.pressure_ppm <= 1000000
                or type(node.healthy) is not bool or type(node.worker_role) is not bool
                or node.mode not in {'ACTIVE', 'STANDBY', 'DRAINING', 'MAINTENANCE'}
                or not isinstance(node.data, frozenset)):
            raise ValueError('malformed candidate observation')
        reason = None
        if node.incarnation != node.observation_incarnation:
            reason = 'INCARNATION_MISMATCH'
        elif node.observed_ms > now_ms:
            reason = 'CAPACITY_FUTURE'
        elif now_ms - node.observed_ms > policy.max_age_ms:
            reason = 'CAPACITY_STALE'
        elif not node.healthy:
            reason = 'UNHEALTHY'
        elif not node.worker_role:
            reason = 'NO_WORKER_ROLE'
        elif node.mode != 'ACTIVE':
            reason = 'NODE_' + node.mode
        elif node.pressure_ppm > policy.max_pressure_ppm:
            reason = 'MEMORY_PRESSURE'
        elif node.benchmark_id != benchmark_id:
            reason = 'BENCHMARK_MISMATCH'
        available = tuple(c - r for c, r in zip(capacity, reserved))
        if reason is None:
            for key, need, free in zip(dimensions, requested, available):
                if need > free:
                    reason = 'INSUFFICIENT_' + key.upper()
                    break
        if reason is not None:
            rejected.append((node.node_id, reason))
            continue
        utilization = sum((Fraction(need, free) for need, free in zip(requested, available) if need), Fraction())
        locality = Fraction(len(data & node.data), len(data)) if data else Fraction()
        score = policy.utilization_weight * utilization - policy.locality_weight * locality
        ranked.append((score, node.node_id))
    return Decision(min(ranked)[1] if ranked else None, tuple(sorted(rejected)))
