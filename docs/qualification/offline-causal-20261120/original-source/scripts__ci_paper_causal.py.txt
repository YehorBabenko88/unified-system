"""Mandatory, source-pinned SYNTHETIC paper composition; never live acceptance.

Run with Python -I -S -B. Inputs are explicit committed source checkouts plus
hash-locked pytest test-only dependencies in a separate directory. No network
provider, credentials or real order API is used by this composition.
"""
import argparse
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import unittest

TEST_DEPENDENCIES = dict(pytest='8.3.5', iniconfig='2.1.0', packaging='24.2', pluggy='1.5.0', colorama='0.4.6')

EXPECTED_IDS = tuple('test_lab_paper_pipeline.' + value for value in (
    'GuardTests.test_numeric_funding_representation_is_exact_without_rounding_milliseconds',
    'GuardTests.test_missing_kernel_source_admission_precedes_all_factories_and_files',
    'ComposedTests.test_ten_actual_strategy_risk_later_quotes_native_ledger_and_writer',
    'ComposedTests.test_unknown_funding_and_legacy_context_never_create_paper_fill',
    'ComposedTests.test_funding_survives_actual_processing_delay_without_relabelling_selection',
    'ComposedTests.test_fractional_hour_and_integral_float_funding_values_keep_exact_units',
    'ComposedTests.test_risk_processing_cannot_refresh_expired_strategy_window',
    'ComposedTests.test_reconnect_retains_uncertain_collateral_and_never_reuses_old_book',
    'ComposedTests.test_publication_failure_stops_without_retry_or_new_source_io',
    'ComposedTests.test_tiny_hold_budget_rejects_ten_minute_plan_before_audit_creation',
    'ComposedTests.test_first_new_quote_before_latency_is_not_relabelled_as_a_fill',
    'ComposedTests.test_revocation_stops_before_another_source_read_and_preserves_cash_reservation',
    'ComposedTests.test_elapsed_window_stops_reads_without_claiming_qualification',
    'ComposedTests.test_provider_failure_holds_cursor_then_normal_poll_uses_real_later_asof',
    'ComposedTests.test_foreign_native_ledger_trade_stops_before_writer_callback',
    'ComposedTests.test_actual_native_result_reaches_existing_writer_and_pinned_term_reader',
))


class GateRejected(Exception):
    """Public bounded rejection code only; no exception data enters evidence."""


def need(value, code):
    if not value:
        raise GateRejected(code)


def require_inventory(ids):
    need(len(ids) == len(EXPECTED_IDS) and set(ids) == set(EXPECTED_IDS), 'CASE_INVENTORY_REJECTED')


def git(root, *args):
    result = subprocess.run(['git', '--no-replace-objects', '-C', str(root), *args],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    need(result.returncode == 0 and len(result.stdout) <= 16 * 1024 * 1024, 'SOURCE_GIT_REJECTED')
    return result.stdout


def source_snapshot(root, repository, expected):
    root = Path(root).resolve(strict=True)
    need(re.fullmatch('[a-f0-9]{40}', expected) is not None, 'SOURCE_PIN_REJECTED')
    need(Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() == root,
         'SOURCE_ROOT_REJECTED')
    origin = git(root, 'remote', 'get-url', 'origin').decode().strip()
    need(origin in (f'https://github.com/YehorBabenko88/{repository}',
                    f'https://github.com/YehorBabenko88/{repository}.git',
                    f'git@github.com:YehorBabenko88/{repository}.git'), 'SOURCE_ORIGIN_REJECTED')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    need(head == expected, 'SOURCE_HEAD_REJECTED')
    need(not git(root, 'status', '--porcelain=v1', '--untracked-files=all'), 'SOURCE_DIRTY_REJECTED')
    entries = git(root, 'ls-files', '-z').split(b'\0')
    digest = hashlib.sha256(); count = 0
    for encoded in sorted(filter(None, entries)):
        relative = encoded.decode('utf-8', 'strict'); path = root / relative
        need(path.resolve(strict=True).is_relative_to(root), 'SOURCE_PATH_REJECTED')
        need(stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink(), 'SOURCE_KIND_REJECTED')
        raw = path.read_bytes()
        digest.update(len(encoded).to_bytes(8, 'big')); digest.update(encoded)
        digest.update(len(raw).to_bytes(8, 'big')); digest.update(hashlib.sha256(raw).digest()); count += 1
    return dict(head=head, tree=git(root, 'rev-parse', 'HEAD^{tree}').decode().strip(),
                origin=origin, tracked_count=count, tracked_raw_sha256=digest.hexdigest())


def require_external_output(output, roots):
    output = Path(output).resolve()
    need(all(not output.is_relative_to(Path(root).resolve()) for root in roots), 'OUTPUT_INSIDE_SOURCE_REJECTED')


def require_unchanged(before, after):
    need(before == after, 'SOURCE_CHANGED_DURING_TESTS')


def dependencies_snapshot(root):
    root = Path(root).resolve(strict=True)
    versions = {}
    for distribution in importlib.metadata.distributions(path=[str(root)]):
        name = distribution.metadata['Name']
        need(name in TEST_DEPENDENCIES and name not in versions, 'TEST_DEPENDENCY_INVENTORY_REJECTED')
        versions[name] = distribution.version
    need(versions == TEST_DEPENDENCIES, 'TEST_DEPENDENCY_VERSION_REJECTED')
    digest = hashlib.sha256(); count = 0
    for path in sorted(root.rglob('*')):
        need(not path.is_symlink(), 'TEST_DEPENDENCY_LINK_REJECTED')
        if path.is_dir():
            continue
        need(stat.S_ISREG(path.lstat().st_mode) and path.suffix not in ('.pth', '.pyc'),
             'TEST_DEPENDENCY_PRELOAD_REJECTED')
        relative = path.relative_to(root).as_posix().encode(); raw = path.read_bytes()
        digest.update(len(relative).to_bytes(8, 'big')); digest.update(relative)
        digest.update(len(raw).to_bytes(8, 'big')); digest.update(hashlib.sha256(raw).digest()); count += 1
    return dict(versions=versions, file_count=count, raw_sha256=digest.hexdigest())


class CausalResult(unittest.TestResult):
    def __init__(self):
        super().__init__(); self.started = []; self.finished = []

    def startTest(self, test):
        self.started.append(test.id()); super().startTest(test)

    def stopTest(self, test):
        self.finished.append(test.id()); super().stopTest(test)


def require_success(result, expected):
    need(result.wasSuccessful() and not result.skipped and not result.expectedFailures
         and not result.unexpectedSuccesses and result.testsRun == len(expected)
         and len(result.started) == len(expected) and set(result.started) == set(expected)
         and len(result.finished) == len(expected) and set(result.finished) == set(expected),
         'MANDATORY_CASE_NOT_PASSED')


def case_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from case_ids(item)
        else:
            yield item.id()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('unified', 'grid', 'stratt', 'terminan'):
        parser.add_argument('--' + name + '-root', type=Path, required=True)
        parser.add_argument('--' + name + '-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test-deps-root', type=Path, required=True)
    args = parser.parse_args(argv)
    roots = {name: getattr(args, name + '_root').resolve(strict=True)
             for name in ('unified', 'grid', 'stratt', 'terminan')}
    require_external_output(args.output, roots.values())
    require_external_output(args.test_deps_root, roots.values())
    need(not args.output.resolve().is_relative_to(args.test_deps_root.resolve()), 'OUTPUT_INSIDE_TEST_DEPS_REJECTED')
    need(not args.output.exists(), 'FRESH_OUTPUT_REQUIRED')
    report = dict(schema='unified.causal-paper-ci.v1', status='FAIL', evidence_class='SYNTHETIC',
                  physical_acceptance='NOT_EVALUATED', live_market_data='NOT_RUN',
                  duration_600s='NOT_RUN', real_orders='PROHIBITED',
                  modeled=['market frames', 'clock', 'kernel admission callback'],
                  actual=['Grid observation validation', 'BookTapeResearch strategy',
                          'Strattester paper account and native PaperLedger',
                          'Unified SnapshotWriter', 'Terminan pinned snapshot reader'],
                  expected_ids=list(EXPECTED_IDS))
    result = None
    try:
        need(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode, 'ISOLATED_STDLIB_PYTHON_REQUIRED')
        need(roots['unified'] == Path(__file__).resolve().parents[1], 'GATE_SOURCE_ROOT_REJECTED')
        repositories = dict(unified='unified-system', grid='bybit-cluster-grid', stratt='strattester', terminan='Terminan')
        before = {name: source_snapshot(root, repositories[name], getattr(args, name + '_head'))
                  for name, root in roots.items()}
        report['sources_before'] = before
        dependencies = dependencies_snapshot(args.test_deps_root)
        report['test_dependencies_before'] = dependencies
        sys.path.append(str(args.test_deps_root.resolve(strict=True)))
        artifact = roots['terminan'] / 'terminan/lab_view.py'
        pin = hashlib.sha256(artifact.read_bytes()).hexdigest()
        report['terminan_reader_raw_sha256'] = pin
        report['terminan_reader_git_blob'] = git(roots['terminan'], 'rev-parse', 'HEAD:terminan/lab_view.py').decode().strip()
        os.environ.update(PAPER_TEST_GRID_ROOT=str(roots['grid']), PAPER_TEST_STRATT_ROOT=str(roots['stratt']),
                          PAPER_TEST_TERMINAN_ROOT=str(roots['terminan']), PAPER_TEST_TERMINAN_LAB_SHA256=pin)
        sys.path.insert(0, str(roots['unified']))
        path = roots['unified'] / 'tests/test_lab_paper_pipeline.py'
        spec = importlib.util.spec_from_file_location('test_lab_paper_pipeline', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        require_inventory(list(case_ids(suite)))
        result = CausalResult(); suite.run(result)
        report['tests'] = dict(run=result.testsRun, started=result.started, finished=result.finished,
                               skipped=len(result.skipped), failures=len(result.failures), errors=len(result.errors),
                               expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses))
        after = {name: source_snapshot(root, repositories[name], getattr(args, name + '_head'))
                 for name, root in roots.items()}
        report['sources_after'] = after
        require_unchanged(before, after)
        report['test_dependencies_after'] = dependencies_snapshot(args.test_deps_root)
        need(dependencies == report['test_dependencies_after'], 'TEST_DEPENDENCIES_CHANGED_DURING_TESTS')
        require_success(result, EXPECTED_IDS)
        report['status'] = 'PASS_SYNTHETIC_CAUSAL_COMPOSITION_ONLY'
    except GateRejected as error:
        report['reason'] = str(error)
    except Exception:
        report['reason'] = 'UNEXPECTED_GATE_FAILURE'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True); stream.write('\n')
    print(report['status'], report.get('reason', ''))
    return 0 if report['status'] == 'PASS_SYNTHETIC_CAUSAL_COMPOSITION_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
