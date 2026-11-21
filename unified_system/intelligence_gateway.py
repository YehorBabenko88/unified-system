"""Offline Gateway contract preparation, never a client identity or executor.

This module performs no IO, imports no engines and accepts no backend callback.
An authenticated MCP/API composition has NOT been implemented or admitted.
"""
import copy
import hashlib
import json
import math
import re
from datetime import datetime


class GatewayInvalid(ValueError):
    """Closed public validation failure, without reflected request contents."""


class GatewayBlocked(RuntimeError):
    """Native client/tool admission is unavailable."""


_GROUPS = (
    ('OBSERVATION', 'get_cluster_status list_nodes get_node_health list_instruments get_dataset_manifest get_data_coverage query_market_data query_orderbook_history list_strategies get_strategy_results get_experiment get_paper_positions get_paper_trades get_statistics get_scientific_evidence get_ci_status get_release_status'),
    ('RESEARCH', 'create_research_plan submit_backtest submit_replay submit_statistical_analysis submit_paper_experiment get_job_status get_job_artifacts cancel_owned_job'),
    ('VISUALIZATION', 'create_visualization publish_research_artifact get_visualization compare_experiments'),
    ('DEVELOPMENT', 'get_component_capabilities get_integration_blockers create_diagnostic_bundle propose_change get_change_validation'),
)


def catalog():
    """Public proposed logical tools; not registered MCP tools or active routes."""
    return dict(schema='unified.gateway.catalog.v1', profile='OFFLINE_CONTRACT_PREPARATION',
                runtime_available=False, authentication_available=False,
                tools=[dict(name='unified.'+name, level=level, runtime='BLOCKED')
                       for level, names in _GROUPS for name in names.split()])


def runtime_call(_name, _arguments):
    """Unconditional closure: no credential, role, text or flag can enable IO."""
    raise GatewayBlocked('GATEWAY_CLIENT_ADMISSION_UNAVAILABLE')


def _require(condition):
    if not condition:
        raise GatewayInvalid('INVALID_GATEWAY_CONTRACT')


def _closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys.split()))


def _match(value, pattern):
    _require(type(value) is str and re.fullmatch(pattern, value) is not None)


def _integer(value, minimum, maximum):
    _require(type(value) is int and minimum <= value <= maximum)


def _shape(value, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    _require(depth <= 12 and count[0] <= 2048)
    if type(value) is dict:
        _require(len(value) <= 48)
        for key, child in value.items():
            _require(type(key) is str)
            _shape(key, depth+1, count)
            _shape(child, depth+1, count)
    elif type(value) is list:
        _require(len(value) <= 128)
        for child in value:
            _shape(child, depth+1, count)
    elif type(value) is str:
        _require(len(value) <= 4096 and all(ord(c) >= 32 and not 0xd800 <= ord(c) <= 0xdfff for c in value))
    else:
        _require(value is None or type(value) in (bool, int, float))
        if type(value) is float:
            _require(math.isfinite(value))
        if type(value) is int:
            _require(abs(value) <= 9007199254740991)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def decode(raw):
    """Bounded strict JSON ingress for local preparation, no payload logging."""
    _require(type(raw) is bytes and 0 < len(raw) <= 32768)
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                           parse_constant=lambda _: _require(False))
        _shape(value)
        return value
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        raise GatewayInvalid('INVALID_GATEWAY_CONTRACT') from None


def _canonical(value):
    _shape(value)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('ascii')
    except (ValueError, OverflowError, RecursionError):
        raise GatewayInvalid('INVALID_GATEWAY_CONTRACT') from None
    _require(len(raw) <= 32768)
    return raw


def _time(value):
    _match(value, r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z')
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise GatewayInvalid('INVALID_GATEWAY_CONTRACT') from None


def prepare_query(value):
    """Validate a request; returns no market rows, registry claim or page token.

    Offset is bounded planning metadata, not a production pagination protocol.
    Dataset, instrument, units and source capability require owner verification.
    """
    _canonical(value)
    _closed(value, 'schema exchange category symbol instrument_version dataset_id manifest_sha256 data_kind start_utc end_utc limit offset aggregation quality units')
    _require(value['schema'] == 'unified.gateway.query.v1' and value['exchange'] == 'BYBIT')
    _require(value['category'] in ('spot', 'linear', 'inverse', 'option'))
    _match(value['symbol'], r'[A-Z0-9][A-Z0-9_-]{0,63}')
    _match(value['instrument_version'], r'[1-9][0-9]{0,18}')
    _require(int(value['instrument_version']) <= 9223372036854775807)
    _match(value['dataset_id'], r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}')
    _match(value['manifest_sha256'], r'[0-9a-f]{64}')
    _require(value['data_kind'] in ('CANDLES', 'PUBLIC_TRADES', 'ORDERBOOK_SNAPSHOTS', 'ORDERBOOK_DELTAS', 'FUNDING', 'DERIVED_FEATURES'))
    _require(_time(value['start_utc']) < _time(value['end_utc']))
    _integer(value['limit'], 1, 1000)
    _integer(value['offset'], 0, 100000)
    _require(value['aggregation'] in ('NONE', '1m', '5m', '1h', '1d'))
    _require(value['quality'] == 'REQUIRE_VERIFIED' and value['units'] == 'SOURCE_DECLARED')
    return dict(schema='unified.gateway.query-preparation.v1', status='NOT_EXECUTED',
                query_sha256=hashlib.sha256(_canonical(value)).hexdigest(), query=copy.deepcopy(value),
                data=[], next_page=None, coverage='UNKNOWN', gaps='UNKNOWN', integrity='UNVERIFIED',
                dataset_identity='UNVERIFIED_REFERENCE', instrument_identity='UNVERIFIED_REFERENCE',
                time_semantics='UTC_RANGE_ONLY_EVENT_KNOWLEDGE_TIME_UNVERIFIED', units='UNVERIFIED',
                source_content_digests=[], effects_authorized=False,
                limitations=['CLIENT_ADMISSION_UNAVAILABLE', 'STORAGE_REGISTRY_BINDING_UNAVAILABLE',
                             'SOURCE_CAPABILITY_NOT_VERIFIED', 'NO_MARKET_DATA_RETURNED'])


def prepare_research_plan(value):
    """Content-addressed plan only. No job creation, ledger, registry or engine."""
    _canonical(value)
    _closed(value, 'schema hypothesis strategy_sha query fidelity execution_model periods costs numerical seed budget')
    _require(value['schema'] == 'unified.gateway.research-plan.v1')
    _require(type(value['hypothesis']) is str and 1 <= len(value['hypothesis']) <= 2048)
    _match(value['strategy_sha'], r'[0-9a-f]{40}')
    q = prepare_query(value['query'])['query']
    _require(value['execution_model'] == 'PAPER_ONLY')
    expected = {'CANDLES':'CANDLE_ONLY', 'PUBLIC_TRADES':'TRADE_REPLAY',
                'ORDERBOOK_SNAPSHOTS':'BOOK_SNAPSHOT_ONLY', 'ORDERBOOK_DELTAS':'BOOK_REPLAY'}
    _require(q['data_kind'] in expected and value['fidelity'] == expected[q['data_kind']])
    _closed(value['periods'], 'train validation test')
    previous = _time(q['start_utc'])
    for key in ('train', 'validation', 'test'):
        period = value['periods'][key]
        _require(type(period) is list and len(period) == 2)
        start, end = map(_time, period)
        _require(previous <= start < end <= _time(q['end_utc']))
        previous = end
    _closed(value['costs'], 'fee_bps slippage_bps funding')
    for key in ('fee_bps', 'slippage_bps'):
        # String decimal, no binary64 arithmetic or silent cost subtraction.
        _match(value['costs'][key], r'(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,8})?')
    _require(value['costs']['funding'] == 'SOURCE_SIGNED_SEPARATE')
    _closed(value['numerical'], 'engine configuration_sha256')
    _require(value['numerical']['engine'] == 'Math')
    _match(value['numerical']['configuration_sha256'], r'[0-9a-f]{64}')
    _integer(value['seed'], 0, 2147483647)
    _closed(value['budget'], 'cpu_seconds memory_mib max_output_bytes')
    for key, high in (('cpu_seconds', 3600), ('memory_mib', 8192), ('max_output_bytes', 1048576)):
        _integer(value['budget'][key], 1, high)
    return dict(schema='unified.gateway.research-preparation.v1', status='NOT_SUBMITTED',
                plan_sha256=hashlib.sha256(_canonical(value)).hexdigest(), plan=copy.deepcopy(value),
                job_id=None, experiment_id=None, effects_authorized=False, scientifically_validated=False,
                limitations=['HYPOTHESIS_IS_UNTRUSTED_TEXT', 'DATASET_AND_SOURCE_NOT_ADMITTED',
                             'CLIENT_QUOTA_FENCING_UNAVAILABLE', 'NO_ENGINE_EXECUTED',
                             'PERIOD_ORDER_CHECK_IS_NOT_LEAKAGE_PROOF', 'NO_PAPER_ACTIVATION'])
