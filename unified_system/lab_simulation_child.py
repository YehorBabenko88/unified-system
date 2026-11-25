"""LAB_SIMULATION child entry (Workstream C). Run as a file: python -I -B <this> .

Reads exactly one capability line from stdin, re-verifies the admitted
component identity *before* importing any application module, then runs the
module's canonical ``main`` with a live ``startup_admission``. The rest of
stdin is the supervisor's lifeline: when it closes, admission is revoked and
the process exits. Any refusal prints one fixed line and exits 78.
"""
import sys

ENTRIES = {'market_data': ('market_data.cli', ['serve']), 'terminan': ('terminan.server', None)}


def main():
    try:
        if not (sys.flags.isolated and sys.flags.dont_write_bytecode):
            raise ValueError('flags')
        import json
        import os
        from pathlib import Path
        line = sys.stdin.buffer.readline(65537)
        if not line.endswith(b'\n') or len(line) > 65536:
            raise ValueError('capability')
        capability = json.loads(line)
        own_package = Path(__file__).absolute().parent
        sources = capability['sources']
        if (Path(sources['unified_system']['root']) != own_package
                or Path(sources['unified_system']['import_root']) != own_package.parent):
            raise ValueError('own root')
        # Verify our own package bytes before importing any of it.
        import hashlib
        files = {}
        for directory, dirs, names in os.walk(own_package):
            dirs.sort()
            if '__pycache__' in dirs:
                raise ValueError('bytecode')
            for name in names:
                path = Path(directory) / name
                if path.is_symlink() or name.endswith(('.pyc', '.pyo')):
                    raise ValueError('file')
                files[path.relative_to(own_package).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        body = (json.dumps(files, sort_keys=True, separators=(',', ':')) + '\n').encode()
        if hashlib.sha256(body).hexdigest() != sources['unified_system']['tree_sha256']:
            raise ValueError('own identity')
        sys.path[:0] = [str(own_package.parent)]
        from unified_system.lab_simulation_admission import LabGrant, need
        grant = LabGrant(capability, watch_stream=sys.stdin.buffer)
        module_id = capability['module_id']
        need(os.environ.get('UNIFIED_MODULE_ID') == module_id
             and os.environ.get('UNIFIED_INSTANCE_TOKEN') == capability['instance_token']
             and os.environ.get('UNIFIED_RELEASE_ID') == capability['release_id']
             and os.environ.get('UNIFIED_TRADING_AUTHORIZED') == 'false')
        roots = [sources[m]['import_root'] for m in ('market_data', 'math', 'terminan') if m in sources]
        sys.path[1:1] = roots + list(capability.get('dependency_roots', []))
        entry, fixed = ENTRIES[module_id]
        argv = fixed if fixed is not None else ['--host', '127.0.0.1', '--port', str(capability['port'])]

        def lifeline():
            # Revocation is final: stop serving promptly once the supervisor is gone.
            import time
            while not grant.revoked:
                time.sleep(0.2)
            os._exit(0)
        import threading
        threading.Thread(target=lifeline, daemon=True).start()
        grant.require_current()
        module = __import__(entry, fromlist=['main'])
        return module.main(argv, startup_admission=grant) or 0
    except SystemExit:
        raise
    except BaseException:
        print('BLOCKED_LAB_CHILD', flush=True)
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
