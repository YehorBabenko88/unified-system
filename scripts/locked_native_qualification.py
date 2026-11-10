"""Unconditional native prerequisite failure. No supported native enable path."""
import argparse
import json
import hashlib
import os
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--expected-tests', required=True, type=int, choices=(21, 22))
    args = parser.parse_args(argv)
    status = dict(schema='unified.native-prerequisite.v1', state='BLOCKED',
                  reason='NATIVE_QUALIFICATION_PREREQUISITES_LOCKED', result='NOT_RUN',
                  expected_tests=args.expected_tests, collected_tests=0, executed_tests=0,
                  skipped_tests=0, fixture_imported=False, historical_exec=False,
                  native_download_attempted=False, native_processes_started=0,
                  enable_path_supported=False, production='NO_GO',
                  helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  declared_expected_head=os.environ.get('EXPECTED_HEAD'),
                  identity_scope='Declared event input and raw helper identity; not authenticated admission')
    raw = (json.dumps(status, sort_keys=True) + '\n').encode('ascii')
    assert len(raw) <= 4096
    try:
        target = Path(args.output).absolute()
        # Workflow passes a fresh explicitly owned runner-temp child directory.
        # Never overwrite/adopt a preexisting output path.
        for parent in target.parents:
            info = parent.lstat()
            if parent.is_symlink() or getattr(info, 'st_reparse_tag', 0) or getattr(info, 'st_file_attributes', 0) & 1024:
                raise ValueError('LINK_OUTPUT')
        target.mkdir(exist_ok=False)
        with (target / 'status.json').open('xb') as stream:
            stream.write(raw)
    except Exception:
        print('NATIVE_PREREQUISITE_ARTIFACT_WRITE_FAILED', file=sys.stderr)
    sys.stdout.write(raw.decode('ascii'))
    sys.stderr.write('NATIVE_QUALIFICATION_PREREQUISITES_LOCKED\n')
    return 78


if __name__ == '__main__':
    raise SystemExit(main())
