"""Diagnostic-only probe for LAN mTLS DISCONNECTED failures (MASTER #111, C3).

Runs the unchanged LAN Mux qualification suites (same discovery order as
.github/workflows/lan-mux-isolated.yml) with test-process wrappers that only
RECORD: which side closes a Connection, with which reason and which handled
exception (type, code, raise site, cause chain), Mux aborts, SQLite budget
transaction latency, per-fragment send timing and remaining deadlines.

Wrappers call each original exactly once with unchanged arguments. No deadline,
timeout, TLS setting, certificate, budget or verification is modified. This is
not a product or gate component; it is never imported by product code.

Usage: python tools/diagnostics/lan_mtls_probe.py --iterations N --out FILE
       [--modules test_lan_transport,test_network_budget,test_lan_mux_channel]
       [--pattern-suite full]   (full = unittest discover over tests/)
"""
import argparse
import collections
import json
import os
import pathlib
import platform
import sys
import threading
import time
import traceback
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))

from unified_system import lan_transport as lan  # noqa: E402
from unified_system import lan_mux_channel as mux  # noqa: E402
from unified_system import network_budget as budget  # noqa: E402

_T0 = [time.monotonic()]
_EVENTS = collections.deque(maxlen=4000)
_LOCK = threading.Lock()
_TX = collections.defaultdict(list)


def _now():
    return round((time.monotonic() - _T0[0]) * 1000, 1)


def _record(kind, **fields):
    fields.update(kind=kind, t_ms=_now(), thread=threading.current_thread().name)
    with _LOCK:
        _EVENTS.append(fields)


def _exc_chain(exc):
    out = []
    seen = set()
    while exc is not None and id(exc) not in seen and len(out) < 5:
        seen.add(id(exc))
        tb = traceback.extract_tb(exc.__traceback__) if exc.__traceback__ else []
        sites = [f'{pathlib.Path(f.filename).name}:{f.lineno}:{f.name}' for f in tb[-4:]]
        out.append(dict(type=type(exc).__name__, text=str(exc)[:200], sites=sites))
        exc = exc.__cause__ or exc.__context__
    return out


def _side(connection):
    try:
        return f'{connection.owner.node_id}->{connection.peer_id}'
    except Exception:  # pragma: no cover - diagnostic only
        return 'UNKNOWN'


def install():
    close = lan.Connection.close
    abort = mux.LanMuxChannel._abort
    transaction = budget._Store.transaction
    send_fragment = lan.Connection.send_mux_fragment
    mux_send = mux.LanMuxChannel.send
    write_frame = lan._write_frame

    def observed_close(self, reason='CLOSED'):
        # Original first: recording must not delay the product's own cleanup.
        was_open = not self.closed
        result = close(self, reason)
        if was_open:
            exc = sys.exc_info()[1]
            _record('CONNECTION_CLOSE', side=_side(self), reason=str(reason)[:200],
                    age_ms=round((time.monotonic() - self.created_at) * 1000, 1),
                    since_last_rx_ms=round((time.monotonic() - self.last_rx) * 1000, 1),
                    handled=_exc_chain(exc) if exc is not None else None,
                    caller=[f'{pathlib.Path(f.filename).name}:{f.lineno}:{f.name}' for f in traceback.extract_stack()[-5:-1]])
        return result

    def observed_abort(self, reason):
        was_open = not self.closed
        result = abort(self, reason)
        if was_open:
            exc = sys.exc_info()[1]
            _record('MUX_ABORT', side=_side(self.connection), reason=str(reason)[:200],
                    handled=_exc_chain(exc) if exc is not None else None)
        return result

    import contextlib

    @contextlib.contextmanager
    def observed_transaction(store):
        start = time.monotonic()
        try:
            with transaction(store) as con:
                yield con
        finally:
            elapsed = (time.monotonic() - start) * 1000
            with _LOCK:
                _TX[pathlib.Path(str(store.path)).name].append(elapsed)
            if elapsed > 250:
                _record('SLOW_BUDGET_TX', store=pathlib.Path(str(store.path)).name, ms=round(elapsed, 1))

    def observed_send_fragment(self, payload, *, deadline=None, cancel=None):
        start = time.monotonic()
        try:
            return send_fragment(self, payload, deadline=deadline, cancel=cancel)
        except BaseException as exc:
            _record('FRAGMENT_SEND_ERROR', side=_side(self), error=_exc_chain(exc),
                    remaining_ms=None if deadline is None else round((deadline - time.monotonic()) * 1000, 1))
            raise
        finally:
            _record('FRAGMENT_SENT', side=_side(self), n=len(payload), ms=round((time.monotonic() - start) * 1000, 1),
                    remaining_ms=None if deadline is None else round((deadline - time.monotonic()) * 1000, 1))

    def observed_mux_send(self, kind, payload, *, deadline=None, cancel=None):
        start = time.monotonic()
        _record('MUX_SEND_START', side=_side(self.connection), kind_=kind, size=len(payload) if type(payload) is bytes else -1,
                budget_ms=None if deadline is None else round((deadline - start) * 1000, 1))
        try:
            result = mux_send(self, kind, payload, deadline=deadline, cancel=cancel)
            _record('MUX_SEND_DONE', side=_side(self.connection), ms=round((time.monotonic() - start) * 1000, 1))
            return result
        except BaseException as exc:
            _record('MUX_SEND_ERROR', side=_side(self.connection), ms=round((time.monotonic() - start) * 1000, 1),
                    error=_exc_chain(exc))
            raise

    def observed_write_frame(sock, lock, budget_, peer, kind, stream, traffic_class, payload, value, deadline, cancel=None, message_id=None):
        start = time.monotonic()
        try:
            return write_frame(sock, lock, budget_, peer, kind, stream, traffic_class, payload, value, deadline, cancel, message_id)
        except BaseException as exc:
            _record('WRITE_FRAME_ERROR', peer=peer, frame=kind, ms=round((time.monotonic() - start) * 1000, 1),
                    remaining_ms=round((deadline - time.monotonic()) * 1000, 1), error=_exc_chain(exc))
            raise
        finally:
            elapsed = (time.monotonic() - start) * 1000
            if elapsed > 250:
                _record('SLOW_WRITE_FRAME', peer=peer, frame=kind, n=len(payload), ms=round(elapsed, 1),
                        remaining_ms=round((deadline - time.monotonic()) * 1000, 1))

    lan.Connection.close = observed_close
    mux.LanMuxChannel._abort = observed_abort
    budget._Store.transaction = observed_transaction
    lan.Connection.send_mux_fragment = observed_send_fragment
    mux.LanMuxChannel.send = observed_mux_send
    lan._write_frame = observed_write_frame


def _percentile(values, q):
    if not values:
        return None
    values = sorted(values)
    return round(values[min(len(values) - 1, int(q * len(values)))], 1)


class ProbeResult(unittest.TextTestResult):
    records = []

    def startTest(self, test):
        with _LOCK:
            _EVENTS.clear()
            _TX.clear()
        _T0[0] = time.monotonic()
        self._start = time.monotonic()
        super().startTest(test)

    def _finish(self, test, outcome, err=None):
        tx = {name: dict(n=len(v), p50=_percentile(v, .5), p95=_percentile(v, .95), max=_percentile(v, 1.0))
              for name, v in _TX.items()}
        row = dict(id=test.id(), outcome=outcome, ms=round((time.monotonic() - self._start) * 1000, 1), budget_tx=tx)
        if err is not None:
            row['error'] = _exc_chain(err[1])
            with _LOCK:
                row['events'] = list(_EVENTS)
        ProbeResult.records.append(row)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._finish(test, 'ok')

    def addError(self, test, err):
        super().addError(test, err)
        self._finish(test, 'error', err)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._finish(test, 'fail', err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._finish(test, 'skip')


def build_suite(mode):
    loader = unittest.TestLoader()
    if mode == 'full':
        return loader.discover(str(ROOT / 'tests'))
    patterns = ['test_lan_transport.py', 'test_network_budget.py', 'test_lan_mux_channel.py']
    if mode == 'lan+coverage':
        patterns.append('test_lan_mtls_coverage.py')
    return unittest.TestSuite(loader.discover(str(ROOT / 'tests'), pattern=p) for p in patterns)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iterations', type=int, default=1)
    parser.add_argument('--out', required=True)
    parser.add_argument('--suite', default='lan', choices=('lan', 'lan+coverage', 'full'))
    parser.add_argument('--label', default='')
    args = parser.parse_args()
    install()
    summary = dict(label=args.label, python=sys.version, platform=platform.platform(), suite=args.suite, iterations=[])
    for i in range(args.iterations):
        ProbeResult.records = []
        start = time.monotonic()
        runner = unittest.TextTestRunner(verbosity=1, resultclass=ProbeResult, stream=sys.stderr)
        result = runner.run(build_suite(args.suite))
        bad = [r for r in ProbeResult.records if r['outcome'] in ('error', 'fail')]
        lan_rows = [r for r in ProbeResult.records if 'test_lan' in r['id'] or 'test_network_budget' in r['id']]
        summary['iterations'].append(dict(
            index=i, ran=result.testsRun, errors=len(result.errors), failures=len(result.failures),
            seconds=round(time.monotonic() - start, 2), failed=bad,
            lan_timings={r['id']: dict(ms=r['ms'], budget_tx=r['budget_tx']) for r in lan_rows if r['ms'] > 1000}))
        pathlib.Path(args.out).write_text(json.dumps(summary, indent=1, default=str), encoding='utf-8')
        print(f'PROBE iteration={i} ran={result.testsRun} errors={len(result.errors)} failures={len(result.failures)}', flush=True)
        for row in bad:
            print('PROBE_FAILED', row['id'], json.dumps(row.get('error'))[:500], flush=True)
            for event in row.get('events', []):
                if event['kind'] in ('CONNECTION_CLOSE', 'MUX_ABORT', 'MUX_SEND_ERROR', 'WRITE_FRAME_ERROR', 'FRAGMENT_SEND_ERROR', 'MUX_SEND_START', 'MUX_SEND_DONE'):
                    print('  PROBE_EVENT', json.dumps(event, default=str)[:1500], flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
