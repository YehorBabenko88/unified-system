"""Hosted modeled operator contracts with existing Root source/origin custody."""
import argparse
import json
import os
from pathlib import Path
import sys


def run(expected_head, dependencies, basetemp, junit):
    root = Path(__file__).resolve().parents[1]
    if not sys.flags.isolated or not sys.dont_write_bytecode or sys.pycache_prefix is None:
        raise ValueError('ISOLATED_NO_BYTECODE_CACHE_REQUIRED')
    for output in (Path(basetemp).resolve(), Path(junit).resolve(), Path(sys.pycache_prefix).resolve()):
        if output == root or root in output.parents:
            raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_CHECKOUT')
    sys.path.insert(0, str(root))
    os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
    from integration.source_guard import SourceFence
    import integration.source_guard as guard
    fence = SourceFence(root, expected_head, isolated_cache=sys.pycache_prefix)
    fence.check()
    fence.module(guard)
    fence.file(__file__, python=True)
    # Qualify the Root evidence module before adding third-party dependency paths.
    from scripts.operator_contract_ci import validate_junit
    import scripts.operator_contract_ci as evidence
    fence.module(evidence)
    sys.path.insert(1, str(Path(dependencies).resolve()))
    # The source lock is pinned separately by operator_contract_ci before setup.
    import pytest
    result = pytest.main([
        str(root / 'tests/test_operator_control_plane.py'),
        str(root / 'tests/test_operator_command_composition.py'),
        str(root / 'tests/test_lifecycle.py'),
        str(root / 'tests/test_consul_command_store.py'),
        '--rootdir=' + str(root), '-o', 'xfail_strict=true', '--noconftest',
        '-p', 'no:cacheprovider', '-q', '--basetemp=' + str(basetemp),
        '--junitxml=' + str(junit)])
    # No unrelated cached app/test module may supply the apparent passing code.
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if module is not None and (
                name == 'unified_system' or name.startswith('unified_system.')
                or name == 'tests' or name.startswith('tests.')
                or name == 'integration.source_guard'):
            origins[name] = fence.module(module)
    fence.finish()
    if int(result) == 0:
        fence.module(evidence)
        validate_junit(junit)
        fence.finish()
    return int(result), origins


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('expected-head', 'dependencies', 'basetemp', 'junit', 'origins'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    output = Path(args.origins).resolve()
    source = Path(__file__).resolve().parents[1]
    if output == source or source in output.parents:
        raise ValueError('EVIDENCE_MUST_BE_OUTSIDE_CHECKOUT')
    status, origins = run(args.expected_head, args.dependencies, args.basetemp, args.junit)
    output.write_text(json.dumps({'module_origins': origins, 'scope': 'SYNTHETIC_AUTH_MODELED_CONSUL'}, indent=2))
    raise SystemExit(status)
