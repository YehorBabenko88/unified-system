"""Foreground Observer; no service installation, network polling or repair CLI."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import signal
import threading
from threading import Thread as _ObserverThread

from .dashboard import CSS, ObserverApp, render
from .model import ObserverError, decode, need
from .notifications import MockNotificationTransport
from .runtime import ObserverEngine, sources_from_config
from .store import ObserverStore, ordinary


def _make_loopback_server(*args, **kwargs):
    from wsgiref.simple_server import make_server
    return make_server(*args, **kwargs)


def main(argv=None):
    class SafeParser(argparse.ArgumentParser):
        def error(self, message): raise ObserverError('OBSERVER_ARGUMENTS_REJECTED')
    parser = SafeParser(description='Unified Observer (read-only, foreground)')
    parser.add_argument('--config', required=True)
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--export-dashboard', action='store_true')
    parser.add_argument('--mock-notifications', action='store_true')
    parser.add_argument('--serve-loopback', action='store_true', help='Requires separate local listener admission')
    parser.add_argument('--port', type=int, default=8769)
    args = parser.parse_args(argv)
    need(not args.once or not args.serve_loopback, 'ONCE_NO_LISTENER')
    need(1024 <= args.port <= 65535, 'LOOPBACK_PORT_BOUND')
    config = Path(args.config); need(config.is_absolute(), 'ABSOLUTE_CONFIG_REQUIRED')
    ordinary(config, False); need(config.stat().st_size <= 65536, 'CONFIG_BYTE_BOUND')
    with config.open('rb') as stream: raw = stream.read(65537)
    need(len(raw) <= 65536, 'CONFIG_BYTE_BOUND')
    sources = sources_from_config(decode(raw))
    store = ObserverStore(Path(args.state_dir)); server = None; thread = None
    engine = ObserverEngine(store, sources, transport=MockNotificationTransport() if args.mock_notifications else None)
    try:
        if args.export_dashboard:
            engine.poll_once(datetime.now(timezone.utc))
            content = render(store.snapshot(datetime.now(timezone.utc))).replace(
                b'<link rel="stylesheet" href="/app.css">', b'<style>' + CSS + b'</style>')
            target = store.directory / 'dashboard.html'
            if target.exists(): ordinary(target, False)
            need(len(content) <= 1048576, 'DASHBOARD_BOUND')
            with target.open('wb') as stream: stream.write(content)
        if args.once:
            if not args.export_dashboard: engine.poll_once(datetime.now(timezone.utc))
            print(json.dumps({'status':'OFFLINE_OBSERVATION_COMPLETE', 'read_only':True,
                'sources':len(sources), 'notification_transport':'MOCK' if args.mock_notifications else 'DISABLED',
                'physical_admission':False, 'automatic_repair':False}))
            return 0
        if args.serve_loopback:
            from wsgiref.simple_server import WSGIRequestHandler
            class QuietHandler(WSGIRequestHandler):
                def log_message(self, *args): pass
                def handle(self):
                    self.connection.settimeout(3)
                    super().handle()
            server = _make_loopback_server('127.0.0.1', args.port,
                ObserverApp(lambda:store.snapshot(datetime.now(timezone.utc))), handler_class=QuietHandler)
            thread = _ObserverThread(target=server.serve_forever, kwargs={'poll_interval':0.2}, daemon=True)
            thread.start()
        def stop(*_): engine.stop()
        signal.signal(signal.SIGINT, stop)
        if hasattr(signal, 'SIGTERM'): signal.signal(signal.SIGTERM, stop)
        engine.run_forever()
        return 0
    finally:
        engine.stop()
        if server is not None:
            if thread is not None and thread.is_alive(): server.shutdown()
            server.server_close()
        if thread is not None:
            if thread.is_alive(): thread.join(5)
            need(not thread.is_alive(), 'OWN_SERVER_RETIREMENT_UNKNOWN')
        store.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit('OBSERVER_NOT_QUALIFIED_NO_REPAIR') from None
