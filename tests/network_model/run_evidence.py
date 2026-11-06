"""Print bounded synthetic evidence to stdout; no network or product imports."""
import argparse
from collections import Counter
import json
import math

from model import Packet, Simulator


def scenario(seed=41):
    s = Simulator(seed=seed, latency_ms=30, jitter_ms=10, loss_every=7)
    for tick in range(0, 3001, 10):
        if tick == 500:
            s.fail_node('LS5')
        if tick == 1000:
            s.restart_node('LS5', tick)
        if tick >= 1000:
            s.recover('LS5', tick)
        if tick <= 2000 and tick % 100 == 0:
            for node in s.nodes:
                for instrument in range(10):
                    cls = 'control' if instrument == 0 else ('live' if instrument % 2 else 'bulk')
                    s.enqueue(Packet(f'{tick}:{node}:{instrument}', node, cls, 100, f'I{instrument}'))
        s.step(tick)
    latencies = sorted(x['delivered_at_ms'] - x['at_ms'] for x in s.delivered)
    quantile = lambda fraction: latencies[max(0, math.ceil(len(latencies) * fraction) - 1)] if latencies else None
    return {
        'qualification': 'MODEL_ONLY_NOT_RUNTIME_NBM_BYBIT_OR_PHYSICAL_PROOF',
        'seed': seed, 'virtual_duration_ms': 3000, 'nodes': 6, 'synthetic_instruments': 10,
        'attempts': len(s.attempts), 'delivered': len(s.delivered), 'lost': len(s.lost),
        'pending_delivery': len(s.pending), 'explicit_backpressure_rejections': s.rejected,
        'remaining_queued_packets': sum(len(n.queue) for n in s.nodes.values()),
        'peak_queue_bytes_per_node': s.peak_queue_bytes,
        'attempted_bytes_per_node': dict(Counter({n: sum(a['size'] for a in s.attempts if a['node'] == n) for n in s.nodes})),
        'attempts_by_class': dict(Counter(a['traffic_class'] for a in s.attempts)),
        'synthetic_delivery_latency_ms': {'samples': len(latencies), 'p50': quantile(.50), 'p95': quantile(.95), 'p99': quantile(.99)},
        'ls5_loss_ms': 500, 'ls5_restart_ms': 1000, 'restored_rate_ceiling': s.nodes['LS5'].bucket.rate,
        'network_reset_actions': 0, 'provider_requests': 0, 'sockets_opened': 0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='UNBOUND_LOCAL_MODEL')
    args = parser.parse_args()
    print(json.dumps(dict(scenario(), source_commit=args.source), sort_keys=True, indent=2))
