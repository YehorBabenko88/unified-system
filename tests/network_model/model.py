"""MODEL_ONLY discrete-event test helper; never an application budget authority.

No sockets, subprocesses, OS/network configuration or production imports.
Synthetic time/identity/quotas are deliberately not Bybit/runtime admission.
"""
from dataclasses import dataclass
import hashlib
import heapq
import json
import random


def uint(value, minimum=0):
    if type(value) is not int or not minimum <= value <= 10**12:
        raise ValueError('invalid bounded model integer')
    return value


class Bucket:
    def __init__(self, rate, burst, *, empty=False, now=0):
        self.rate, self.burst = uint(rate, 1), uint(burst, 1)
        self.last = uint(now)
        self.credit = 0 if empty else self.burst * 1000

    def available(self, now):
        uint(now)
        if now < self.last:
            raise ValueError('backward virtual clock')
        self.credit = min(self.burst * 1000, self.credit + (now - self.last) * self.rate)
        self.last = now
        return self.credit // 1000

    def take(self, now, size):
        uint(size, 1)
        if self.available(now) < size:
            return False
        self.credit -= size * 1000
        return True


@dataclass(frozen=True)
class Packet:
    packet_id: str
    node: str
    traffic_class: str
    size: int
    instrument: str


class _Node:
    def __init__(self):
        self.ceiling = 1000
        self.bucket = Bucket(1000, 1000)
        self.classes = {c: Bucket(r, r) for c, r in (('control', 200), ('live', 500), ('bulk', 300))}
        self.queue = []
        self.queued_bytes = 0
        self.active = True
        self.recovery_at = None
        self.recovery_start = None


class Simulator:
    """Fixed six-node synthetic byte ceilings; one scheduling visit/node/step."""
    def __init__(self, *, seed=0, latency_ms=0, jitter_ms=0, loss_every=0,
                 max_queue_bytes=3000, max_queue_packets=30):
        self.nodes = {n: _Node() for n in ('LS5', 'PC1', 'PC2', 'PC3', 'PC4', 'LS7')}
        self.cluster = Bucket(6000, 6000)
        self.max_queue_bytes = uint(max_queue_bytes, 1)
        self.max_queue_packets = uint(max_queue_packets, 1)
        self.latency_ms, self.jitter_ms, self.loss_every = map(uint, (latency_ms, jitter_ms, loss_every))
        self.random = random.Random(seed)
        self.now = 0
        self.attempts, self.delivered, self.lost = [], [], []
        self.rejected = 0
        self.pending = []
        self.accepted_ids = set()
        self.peak_queue_bytes = {n: 0 for n in self.nodes}

    def enqueue(self, packet):
        if not isinstance(packet, Packet) or packet.node not in self.nodes:
            raise ValueError('invalid model packet')
        uint(packet.size, 1)
        node = self.nodes[packet.node]
        if packet.traffic_class not in node.classes or not packet.packet_id or not packet.instrument:
            raise ValueError('invalid class/identity')
        if (not node.active or packet.packet_id in self.accepted_ids
                or len(node.queue) >= self.max_queue_packets
                or node.queued_bytes + packet.size > self.max_queue_bytes):
            self.rejected += 1
            return False
        self.accepted_ids.add(packet.packet_id)
        node.queue.append(packet)
        node.queued_bytes += packet.size
        self.peak_queue_bytes[packet.node] = max(self.peak_queue_bytes[packet.node], node.queued_bytes)
        return True

    def _deliver(self):
        while self.pending and self.pending[0][0] <= self.now:
            due, _, attempt = heapq.heappop(self.pending)
            self.delivered.append(dict(attempt, delivered_at_ms=due))

    def step(self, now):
        uint(now)
        if now < self.now:
            raise ValueError('backward virtual clock')
        self.now = now
        self._deliver()
        for node_id, node in self.nodes.items():
            if not node.active:
                continue
            # Class hard caps reserve capacity; a saturated class cannot steal it.
            chosen = None
            for traffic_class in ('control', 'live', 'bulk'):
                packet = next((p for p in node.queue if p.traffic_class == traffic_class), None)
                if packet is None:
                    continue
                buckets = (node.bucket, node.classes[traffic_class], self.cluster)
                if all(b.available(now) >= packet.size for b in buckets):
                    chosen = packet, buckets
                    break
            if chosen is None:
                continue
            packet, buckets = chosen
            # All eligibility checks precede every debit, with no asynchronous effects.
            for b in buckets:
                if not b.take(now, packet.size):
                    raise AssertionError('model atomic debit failed')
            node.queue.remove(packet)
            node.queued_bytes -= packet.size
            attempt = dict(packet_id=packet.packet_id, node=node_id, traffic_class=packet.traffic_class,
                           size=packet.size, instrument=packet.instrument, at_ms=now)
            self.attempts.append(attempt)
            if self.loss_every and len(self.attempts) % self.loss_every == 0:
                self.lost.append(attempt)
            else:
                due = now + self.latency_ms + self.random.randint(0, self.jitter_ms)
                heapq.heappush(self.pending, (due, len(self.attempts), attempt))
        self._deliver()

    def fail_node(self, node_id):
        self.nodes[node_id].active = False

    def restart_node(self, node_id, now):
        uint(now)
        if now < self.now:
            raise ValueError('backward restart')
        node = self.nodes[node_id]
        # Queued producer-owned packets are retained; no automatic retransmission.
        node.active = True
        node.bucket = Bucket(100, node.ceiling, empty=True, now=now)
        node.classes = {c: Bucket(r // 10, r, empty=True, now=now)
                        for c, r in (('control', 200), ('live', 500), ('bulk', 300))}
        node.recovery_start = node.recovery_at = now

    def recover(self, node_id, now):
        node = self.nodes[node_id]
        uint(now)
        if node.recovery_at is None or now < node.recovery_at:
            raise ValueError('invalid recovery time')
        # Accrue at OLD rate first; late recovery cannot retroactively mint credit.
        for bucket in (node.bucket, *node.classes.values()):
            bucket.available(now)
        stage = min(10, 1 + (now - node.recovery_start) // 100)
        node.bucket.rate = node.ceiling * stage // 10
        for c, ceiling in (('control', 200), ('live', 500), ('bulk', 300)):
            node.classes[c].rate = ceiling * stage // 10
        node.recovery_at = now


class QuotaLedger:
    """Shared NAT thought experiment, not Consul, provider policy or permission."""
    def __init__(self, *, limit=10, window_ms=1000):
        self.limit, self.window_ms = uint(limit, 1), uint(window_ms, 1)
        self.attempts = {}
        self.cooldowns = {}
        self.frozen = set()
        self.last_ms = 0
        self.generation = 1
        self.blocked = False
        # These are synthetic test conditions, never external quorum/identity assertions.
        self.quorum = True
        self.gate_open = True

    def _time(self, now):
        uint(now)
        if now < self.last_ms:
            self.blocked = True
        self.last_ms = max(self.last_ms, now)
        return not self.blocked

    def reserve(self, attempt_id, node, nat, now, cost=1):
        uint(cost, 1)
        if not self._time(now) or not self.quorum or not self.gate_open or nat != 'nat1':
            return 'DENIED'
        if attempt_id in self.attempts:
            prior = self.attempts[attempt_id]
            if (prior['node'], prior['nat'], prior['cost']) != (node, nat, cost):
                return 'DENIED'
            if prior['state'] == 'CANCELLED':
                return 'DENIED'
            return 'RESERVED'  # Historical acquisition response; never send permission.
        if nat in self.frozen or now < self.cooldowns.get(nat, 0):
            return 'DENIED'
        used = sum(a['cost'] for a in self.attempts.values()
                   if a['nat'] == nat and a['state'] != 'CANCELLED'
                   and (a['at_ms'] > now - self.window_ms or a['state'] != 'OBSERVED'))
        if used + cost > self.limit:
            return 'DENIED'
        self.attempts[attempt_id] = dict(node=node, nat=nat, cost=cost, at_ms=now, state='RESERVED')
        return 'RESERVED'

    def consume(self, attempt_id, now):
        if not self._time(now) or not self.quorum or not self.gate_open:
            return 'DENIED'
        a = self.attempts.get(attempt_id)
        if a is None:
            return 'DENIED'
        if a['state'] == 'UNKNOWN':
            return 'UNKNOWN'
        if a['state'] != 'RESERVED':
            return 'HISTORICAL'
        if a['nat'] in self.frozen or now < self.cooldowns.get(a['nat'], 0):
            return 'DENIED'
        a['state'] = 'CHARGED'
        return 'CHARGED'

    def mark_unknown(self, attempt_id):
        a = self.attempts[attempt_id]
        a['state'] = 'UNKNOWN'
        self.frozen.add(a['nat'])

    def cancel(self, attempt_id):
        a = self.attempts[attempt_id]
        if self.blocked or not self.quorum or not self.gate_open or a['state'] != 'RESERVED':
            return False
        a['state'] = 'CANCELLED'
        return True

    def cooldown(self, nat, until):
        uint(until)
        self.cooldowns[nat] = max(until, self.cooldowns.get(nat, 0))

    def failover(self):
        # Synthetic leadership counter is diagnostic, never a new quota namespace.
        self.generation += 1

    def save(self, path):
        body = dict(limit=self.limit, window_ms=self.window_ms, attempts=self.attempts,
                    cooldowns=self.cooldowns, frozen=sorted(self.frozen), last_ms=self.last_ms,
                    generation=self.generation, blocked=self.blocked, quorum=self.quorum,
                    gate_open=self.gate_open)
        raw = json.dumps(body, sort_keys=True, separators=(',', ':')).encode('ascii')
        envelope = dict(body=body, sha256=hashlib.sha256(raw).hexdigest())
        path.write_text(json.dumps(envelope, sort_keys=True), encoding='ascii')

    @classmethod
    def load(cls, path):
        try:
            if path.stat().st_size > 1048576:
                raise ValueError('oversized model state')
            e = json.loads(path.read_text(encoding='ascii'))
            if set(e) != {'body', 'sha256'}:
                raise ValueError('bad envelope')
            b = e['body']
            raw = json.dumps(b, sort_keys=True, separators=(',', ':')).encode('ascii')
            if hashlib.sha256(raw).hexdigest() != e['sha256']:
                raise ValueError('bad digest')
            if set(b) != {'limit','window_ms','attempts','cooldowns','frozen','last_ms','generation','blocked','quorum','gate_open'}:
                raise ValueError('bad body')
            obj = cls(limit=b['limit'], window_ms=b['window_ms'])
            for key in ('last_ms', 'generation'):
                uint(b[key])
            for key in ('blocked', 'quorum', 'gate_open'):
                if type(b[key]) is not bool:
                    raise ValueError('bad flag')
            if not isinstance(b['attempts'], dict) or len(b['attempts']) > 10000:
                raise ValueError('bad attempts')
            for a in b['attempts'].values():
                if set(a) != {'node','nat','cost','at_ms','state'} or a['nat'] != 'nat1':
                    raise ValueError('bad attempt')
                uint(a['cost'], 1); uint(a['at_ms'])
                if a['state'] not in ('RESERVED','CHARGED','UNKNOWN','OBSERVED','CANCELLED'):
                    raise ValueError('bad state')
            if type(b['cooldowns']) is not dict or type(b['frozen']) is not list:
                raise ValueError('bad scope container')
            if set(b['cooldowns']) - {'nat1'} or set(b['frozen']) - {'nat1'}:
                raise ValueError('unknown scope')
            for until in b['cooldowns'].values():
                uint(until)
            for key, value in b.items():
                setattr(obj, key, set(value) if key == 'frozen' else value)
            if any(a['state'] == 'UNKNOWN' and a['nat'] not in obj.frozen for a in obj.attempts.values()):
                raise ValueError('lost unknown freeze')
            return obj
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
            obj = cls()
            obj.blocked = True
            return obj
