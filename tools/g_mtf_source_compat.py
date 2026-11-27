"""G source-only B->D MTF compatibility probe; never activates Grid or Terminan.

External source files are inputs, not Python modules. This checker deliberately
cannot attest installed packages, producer provenance, native I/O or release.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path


class ContractUnverified(ValueError):
    pass


def _function(tree, name):
    matches = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    if len(matches) != 1:
        raise ContractUnverified('MISSING_UNIQUE_FUNCTION:' + name)
    return matches[0]


def _producer_keys(tree):
    fn = _function(tree, 'project_qualified_rollup')
    matches = [n for n in ast.walk(fn) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'result' for t in n.targets)]
    if len(matches) != 1 or not isinstance(matches[0].value, ast.Dict):
        raise ContractUnverified('PRODUCER_RESULT_NOT_LITERAL')
    keys = [ast.literal_eval(k) for k in matches[0].value.keys]
    if any(type(k) is not str for k in keys) or len(set(keys)) != len(keys):
        raise ContractUnverified('PRODUCER_KEYS_AMBIGUOUS')
    # Grid's final deterministic hash is appended by return dict(result, ...).
    returns = [n for n in ast.walk(fn) if isinstance(n, ast.Return)
               and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
               and n.value.func.id == 'dict']
    if len(returns) != 1 or len(returns[0].value.args) != 1 or not isinstance(returns[0].value.args[0], ast.Name) or returns[0].value.args[0].id != 'result':
        raise ContractUnverified('PRODUCER_RETURN_UNVERIFIED')
    additions = [kw.arg for kw in returns[0].value.keywords]
    if additions != ['dataset_fingerprint'] or 'dataset_fingerprint' in keys:
        raise ContractUnverified('PRODUCER_DIGEST_ROSTER_UNVERIFIED')
    return frozenset(keys + additions)


def _consumer_keys(tree):
    matches = [n for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == '_TOP' for t in n.targets)]
    if len(matches) != 1:
        raise ContractUnverified('CONSUMER_ROSTER_MISSING')
    expr = matches[0].value
    if not isinstance(expr, ast.Call) or not isinstance(expr.func, ast.Name) or expr.func.id != 'frozenset' or len(expr.args) != 1:
        raise ContractUnverified('CONSUMER_ROSTER_DYNAMIC')
    keys = ast.literal_eval(expr.args[0])
    if type(keys) is not set or not all(type(k) is str for k in keys):
        raise ContractUnverified('CONSUMER_ROSTER_AMBIGUOUS')
    return frozenset(keys)


def _has_quality_literal(tree):
    fn = _function(tree, 'validate_qualified_rollup')
    for n in ast.walk(fn):
        if not isinstance(n, ast.Tuple) or len(n.elts) != 2:
            continue
        try:
            if ast.literal_eval(n) == ('source_declared_quality', ['GOOD']):
                return True
        except (ValueError, TypeError, SyntaxError, MemoryError):
            pass
    # Also admit an explicit equality check outside the field/literal loop.
    for n in ast.walk(fn):
        if (isinstance(n, ast.Compare) and len(n.ops) == 1
                and isinstance(n.ops[0], ast.Eq)
                and len(n.comparators) == 1
                and isinstance(n.left, ast.Subscript)
                and isinstance(n.left.value, ast.Name)
                and n.left.value.id == 'envelope'
                and isinstance(n.left.slice, ast.Constant)
                and n.left.slice.value == 'source_declared_quality'):
            try:
                if ast.literal_eval(n.comparators[0]) == ['GOOD']:
                    return True
            except (ValueError, TypeError, SyntaxError):
                pass
    return False


def _has_lossy_recomputation(tree):
    fn = _function(tree, 'validate_qualified_rollup')
    for n in ast.walk(fn):
        if (isinstance(n, ast.Compare) and len(n.ops) == 1
                and isinstance(n.ops[0], ast.Eq)
                and isinstance(n.left, ast.Name) and n.left.id == 'delta_binary64'
                and any(isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name)
                        and v.value.id == 'row' and isinstance(v.slice, ast.Constant)
                        and v.slice.value == 'delta' for v in n.comparators)):
            return True
    return False


def _numeric_source_unverified(grid_tree, terminal_tree):
    """Admit source-only scrutiny, never infer Decimal parity from float names."""
    producer = _function(grid_tree, 'project_qualified_rollup')
    consumer = _function(terminal_tree, 'validate_qualified_rollup')
    text_producer = ast.dump(producer, include_attributes=False)
    text_consumer = ast.dump(consumer, include_attributes=False)
    # Original Math is single numeric owner. Wire numeric sources MUST be
    # lossless decimal strings, not two binary64 DTO totals with epsilon.
    if ('volume_total' in text_producer and
            'buy_volume_decimal' not in text_producer):
        return 'LOSSLESS_SOURCE_DECIMAL_FIELDS_ABSENT'
    if 'volume_total' in text_producer and 'delta == volume_delta' in ast.unparse(producer):
        return 'LOSSY_FLOAT_RECONSTRUCTION_VETO'
    if ('volume_decimal' not in text_consumer or
            'executed_volume_delta' not in text_consumer or
            'exact_sum' not in text_consumer):
        return 'CANONICAL_MATH_DECIMAL_CONSUMER_UNVERIFIED'
    return None


def check_pair(grid_source: str, terminan_source: str):
    reasons = []
    try:
        grid = ast.parse(grid_source)
        terminal = ast.parse(terminan_source)
        provided = _producer_keys(grid)
        accepted = _consumer_keys(terminal)
        if provided != accepted:
            reasons.append('DTO_KEYS_MISMATCH:' + json.dumps({
                'missing_in_consumer': sorted(provided - accepted),
                'unknown_to_producer': sorted(accepted - provided)}, sort_keys=True))
        if 'source_declared_quality' in provided and not _has_quality_literal(terminal):
            reasons.append('SOURCE_QUALITY_LITERAL_NOT_ENFORCED')
        if _has_lossy_recomputation(terminal):
            reasons.append('LOSSY_DELTA_BINARY64_RECOMPUTATION')
        numeric = _numeric_source_unverified(grid, terminal)
        if numeric is not None:
            reasons.append(numeric)
    except (SyntaxError, ContractUnverified, ValueError, TypeError) as exc:
        reasons.append('UNVERIFIED_SOURCE:' + type(exc).__name__)
    return {'status': 'BLOCKED' if reasons else 'SOURCE_CONTRACT_MATCH_ONLY',
            'reasons': reasons, 'native': 'NOT_RUN', 'release_authorized': False,
            'deletion_authorized': False}


def _read_pinned(path, expected_sha1):
    p = Path(path)
    info = p.lstat()
    if (not p.is_file() or p.is_symlink() or info.st_nlink != 1
            or info.st_size <= 0 or info.st_size > 1048576):
        raise ContractUnverified('SOURCE_FILE_NOT_REGULAR_BOUNDED')
    raw = p.read_bytes()
    if hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() != expected_sha1:
        raise ContractUnverified('SOURCE_GIT_BLOB_SHA_MISMATCH')
    return raw.decode('utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('grid', 'terminan'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-blob-sha1', required=True)
    args = parser.parse_args(argv)
    try:
        result = check_pair(_read_pinned(args.grid, args.grid_blob_sha1),
                            _read_pinned(args.terminan, args.terminan_blob_sha1))
    except (OSError, UnicodeError, ContractUnverified) as exc:
        result = {'status': 'BLOCKED', 'reasons': [type(exc).__name__],
                  'native': 'NOT_RUN', 'release_authorized': False,
                  'deletion_authorized': False}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'SOURCE_CONTRACT_MATCH_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
