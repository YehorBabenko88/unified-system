"""Measure the NodeBudget per-transaction cost on this runner (diagnostic only).

1. The real NodeBudget.try_take (unchanged product code) in a fresh temp store.
2. The same SQLite transaction shape with alternative journal modes, in a
   separate scratch database, to quantify where the time goes. Nothing here
   changes product settings; the alternatives are measurements, not proposals
   that have been applied.
"""
import pathlib
import sqlite3
import statistics
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from unified_system.network_budget import BandwidthPolicy, NodeBudget, NODES  # noqa: E402

N = 200


def stats(name, samples):
    samples = sorted(samples)
    print(f'{name:40s} n={len(samples)} p50={statistics.median(samples):7.2f}ms '
          f'p95={samples[int(.95 * len(samples)) - 1]:7.2f}ms max={samples[-1]:7.2f}ms total={sum(samples):8.1f}ms')


def product():
    policy = BandwidthPolicy({n: {'rate': 64000000, 'burst': 8000000} for n in NODES}, cluster_rate=384000000,
                             cluster_burst=48000000, classes={'control': 80, 'live': 10, 'bulk': 10})
    with tempfile.TemporaryDirectory(prefix='c3-budget-latency-') as directory:
        budget = NodeBudget.isolated(pathlib.Path(directory) / 'PC1.sqlite', 'PC1', policy)
        samples = []
        for _ in range(N):
            start = time.perf_counter()
            budget.try_take('tx', 'LS5', 'control', 1)
            samples.append((time.perf_counter() - start) * 1000)
        stats('NodeBudget.try_take (product)', samples)


def shape(journal, synchronous):
    with tempfile.TemporaryDirectory(prefix='c3-sqlite-shape-') as directory:
        path = pathlib.Path(directory) / 'x.sqlite'
        con = sqlite3.connect(path, isolation_level=None)
        con.execute('PRAGMA journal_mode=' + journal)
        con.execute('CREATE TABLE b (name TEXT PRIMARY KEY, credit INTEGER)')
        con.execute("INSERT INTO b VALUES('k',0)")
        con.close()
        samples = []
        for i in range(N):
            start = time.perf_counter()
            con = sqlite3.connect(path, timeout=2, isolation_level=None)
            con.execute('PRAGMA synchronous=' + synchronous)
            con.execute('BEGIN IMMEDIATE')
            con.execute("UPDATE b SET credit=? WHERE name='k'", (i,))
            con.execute('COMMIT')
            con.close()
            samples.append((time.perf_counter() - start) * 1000)
        stats(f'shape journal={journal} sync={synchronous}', samples)


if __name__ == '__main__':
    print('sqlite', sqlite3.sqlite_version, 'python', sys.version.split()[0], 'platform', sys.platform)
    product()
    for journal, synchronous in (('DELETE', 'FULL'), ('TRUNCATE', 'FULL'), ('PERSIST', 'FULL'), ('WAL', 'FULL'), ('WAL', 'NORMAL')):
        shape(journal, synchronous)
