"""Account for physical test records without treating claims as authentication.

This is the fleet acceptance ledger, not a test simulator or deployment agent.
An external verifier must bind the referenced evidence to the real machines,
release and run. Even a complete ledger cannot grant itself physical acceptance.
"""
import argparse
import json
import re
from pathlib import Path

SCENARIOS = (
    'initial_deployment', 'all_modules_concurrent', 'leader_failure',
    'two_node_failure', 'reboot_recovery', 'network_partition',
    'database_failover', 'verified_rolling_update', 'release_rollback',
    'module_hot_add', 'strategy_hot_add', 'online_migration',
    'disk_retention', 'no_duplicate_computation', 'terminan_real_state',
)
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z')
_SHA = re.compile(r'[a-f0-9]{40}\Z')
_DIGEST = re.compile(r'[a-f0-9]{64}\Z')
_FIELDS = {'node_id', 'scenario', 'release_sha', 'run_id', 'result',
           'environment', 'evidence_sha256'}


def _matches(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None


def assess(inventory, records, *, release_sha, run_id):
    """Return deterministic missing/failed cases; never authenticate input records."""
    if (not isinstance(inventory, list) or len(inventory) not in (5, 6)
            or any(not _matches(_ID, node) for node in inventory)
            or len({node.casefold() for node in inventory}) != len(inventory)):
        raise ValueError('explicit unique inventory of five or six nodes required')
    if not _matches(_SHA, release_sha) or not _matches(_ID, run_id):
        raise ValueError('exact release and acceptance run required')
    if not isinstance(records, list) or len(records) > len(inventory) * len(SCENARIOS):
        raise ValueError('bounded acceptance records required')
    cases = {}
    for record in records:
        if not isinstance(record, dict) or set(record) != _FIELDS:
            raise ValueError('invalid physical record fields')
        if (not _matches(_ID, record['node_id']) or record['node_id'] not in inventory
                or type(record['scenario']) is not str or record['scenario'] not in SCENARIOS
                or record['release_sha'] != release_sha or record['run_id'] != run_id
                or record['environment'] != 'PHYSICAL_WINDOWS'
                or type(record['result']) is not str or record['result'] not in ('PASS', 'FAIL')
                or not _matches(_DIGEST, record['evidence_sha256'])):
            raise ValueError('record identity, environment, result or evidence mismatch')
        key = (record['node_id'], record['scenario'])
        if key in cases:
            raise ValueError('duplicate acceptance case')
        cases[key] = record
    expected = [(node, scenario) for node in sorted(inventory) for scenario in SCENARIOS]
    missing = [dict(node_id=n, scenario=s) for n, s in expected if (n, s) not in cases]
    failed = [dict(node_id=n, scenario=s) for n, s in expected
              if (n, s) in cases and cases[n, s]['result'] == 'FAIL']
    status = 'NOT_RUN' if not cases else 'BLOCKED' if missing or failed else 'RECORDED_UNVERIFIED'
    return {
        'schema': 'unified.physical-acceptance-ledger.v1', 'status': status,
        'release_sha': release_sha, 'run_id': run_id, 'expected_nodes': sorted(inventory),
        'expected_cases': len(expected), 'recorded_cases': len(cases),
        'missing': missing, 'failed': failed,
        'evidence_authenticity': 'UNVERIFIED', 'physical_acceptance_confirmed': False,
        'deployment_authorized': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ledger', type=Path,
                        help='JSON with inventory, records, release_sha and run_id')
    args = parser.parse_args(argv)
    try:
        with args.ledger.open(encoding='utf-8') as stream:
            raw = stream.read(1048577)
        if len(raw) > 1048576:
            raise ValueError('ledger too large')
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('duplicate JSON field')
                result[key] = value
            return result
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
        if not isinstance(value, dict) or set(value) != {'inventory', 'records', 'release_sha', 'run_id'}:
            raise ValueError('invalid ledger fields')
        report = assess(**value)
    except (OSError, ValueError, TypeError, RecursionError):
        print(json.dumps({'status': 'INVALID', 'physical_acceptance_confirmed': False}))
        return 2
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    # A complete unverified ledger still is not a release/deployment gate PASS.
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
