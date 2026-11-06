"""Bounded API predicate model; NOT Consul, Raft, a lease server or acceptance.

No network, persistence engine, election or quorum algorithm. The model executes
only the documented check-session/check-index/CAS semantics over supplied state.
Wall time and physical media are external variables, as they are to KV predicates.
"""
import copy
import json
from pathlib import Path


def initial():
    return {'leader': {'index': 7, 'session': 's1', 'value': 'owner1'},
            'grant': {'index': 8, 'value': {'revision': 1, 'expires_at_ms': 10000}},
            'head': {'index': 9, 'value': 'old'},
            'eligibility': {'index': 10, 'value': 'VERIFIED'},
            'hold': {'index': 11, 'value': 'PINNED'},
            'budget': {'index': 12, 'value': {'remaining': 100}}}


def txn(state, checks, writes):
    """Atomic supplied predicates only; no hidden clock or physical-media check."""
    for kind, key, expected in checks:
        actual = state.get(key)
        if kind == 'check-session':
            if actual is None or actual.get('session') != expected:
                return False
        elif kind == 'check-index':
            if (actual['index'] if actual else 0) != expected:
                return False
        else:
            raise ValueError('model supports only documented supplied predicates')
    revision = max(row['index'] for row in state.values()) + 1
    for key, value in writes.items():
        state[key] = {'index': revision, 'value': copy.deepcopy(value)}
    return True


def publication_checks(state, include_eligibility=True):
    keys = ['grant', 'head', 'hold', 'budget']
    if include_eligibility:
        keys.append('eligibility')
    return [('check-session', 'leader', 's1'), ('check-index', 'leader', 7)] + [
        ('check-index', key, state[key]['index']) for key in keys]


cases = []
for label, delay in [('T01_CLIENT_PAUSE_AFTER_VALIDATION', 'client paused'),
                     ('T02_REQUEST_QUEUED_AFTER_SEND', 'network/server queue')]:
    state = initial()
    checks = publication_checks(state)
    checked_ms, admission_ms, raft_commit_ms, apply_ms, deadline_ms = 9000, 10001, 10002, 10003, 10000
    assert checked_ms < deadline_ms < admission_ms <= raft_commit_ms <= apply_ms
    committed = txn(state, checks, {'head': 'new', 'receipt': 'COMMITTED'})
    assert committed  # Session/invalidation and all KV indices still match.
    cases.append(dict(id=label, kind='COUNTEREXAMPLE', committed=committed,
        precheck_ms=checked_ms, supplied_raft_admission_ms=admission_ms,
        supplied_majority_commit_ms=raft_commit_ms, native_txn_apply_ms=apply_ms, deadline_ms=deadline_ms,
        schedule_qualification='SUPPLIED_EVENT_ORDER_NOT_RAFT_SIMULATION',
        schedule=delay+' before Raft admission', violation='STRICT_COMMIT_TIME_EXPIRY',
        reason='native predicate set has no apply-time wall-clock comparison'))

state = initial()
checks = publication_checks(state)
state['leader']['session'] = None  # Invalidation is actually ordered first.
before = copy.deepcopy(state)
assert not txn(state, checks, {'head': 'new'}) and state == before
cases.append(dict(id='T03_ORDERED_INVALIDATION_FIRST', kind='PREDICATE_CONTROL',
    result='REJECTED_ATOMICALLY', limitation='only proves invalidation order, not exact wall-clock expiry'))

state_a, state_b = initial(), initial()
for state in (state_a, state_b):
    assert txn(state, publication_checks(state), {'head': 'new', 'receipt': {'supplied_time_ms': 9000}})
assert state_a == state_b
cases.append(dict(id='T04_COMMIT_TIME_NOT_IDENTIFIABLE', kind='INDISTINGUISHABLE_HISTORIES',
    supplied_majority_commit_ms=[9890, 10000], native_apply_ms=[9900, 10001], response_observed_ms=11000,
    same_kv_receipt_and_index=True, reason='API data and response-time metadata do not supply actual FSM apply time'))

state = initial()
checks = publication_checks(state, include_eligibility=False)
state['eligibility'] = {'index': 13, 'value': 'REVOKED'}
assert txn(state, checks, {'head': 'new'})
cases.append(dict(id='C01_UNCOUPLED_REVOCATION', kind='COUNTEREXAMPLE',
    result='PUBLISH_ACCEPTED_WITH_REVOKED_EVIDENCE', reason='hold/index did not change and evidence key was not checked'))

state = initial()
checks = publication_checks(state)
state['eligibility'] = {'index': 13, 'value': 'REVOKED'}
before = copy.deepcopy(state)
assert not txn(state, checks, {'head': 'new'}) and state == before
cases.append(dict(id='C02_CHECK_EVERY_DEPENDENCY_INDEX', kind='PREDICATE_CONTROL', result='REJECTED_ATOMICALLY'))

state = initial()
checks = publication_checks(state, include_eligibility=False)
state['eligibility'] = {'index': 13, 'value': 'REVOKED'}
state['hold'] = {'index': 13, 'value': 'INVALIDATED'}  # Same ordered invalidation protocol.
assert not txn(state, checks, {'head': 'new'})
cases.append(dict(id='C03_COUPLED_HOLD_INVALIDATION', kind='PREDICATE_CONTROL', result='REJECTED_ATOMICALLY'))

state = initial()
first, second = publication_checks(state), publication_checks(state)
assert txn(state, first, {'head': 'new1', 'budget': {'remaining': 40}, 'receipt': 'one-debit'})
before = copy.deepcopy(state)
assert not txn(state, second, {'head': 'new2', 'budget': {'remaining': 40}, 'receipt': 'second-debit'})
assert state == before
cases.append(dict(id='C04_CONCURRENT_ALLOCATION_DEBIT', kind='PREDICATE_CONTROL', result='ONE_CAS_WINNER_NO_PARTIAL_SECOND_DEBIT'))

records_healthy, records_corrupt = initial(), initial()
assert records_healthy == records_corrupt
physical_bytes_valid = [True, False]  # Unreported corruption has no KV transition.
accepted = [txn(s, publication_checks(s), {'head': 'new'}) for s in (records_healthy, records_corrupt)]
assert accepted == [True, True] and physical_bytes_valid == [True, False]
cases.append(dict(id='C05_UNREPORTED_MEDIA_CORRUPTION', kind='INDISTINGUISHABLE_HISTORIES',
    same_authority_records=True, physical_bytes_valid=physical_bytes_valid, accepted=accepted,
    reason='KV CAS can order observed eligibility; it cannot synchronously sense external media corruption'))

dispatch = dict(charged=True, incarnation='old', observed_current=True, socket_contained=False)
dispatch['observed_current'] = False  # Replacement after durable consume.
old_sender_can_write = dispatch['charged'] and not dispatch['socket_contained']
assert old_sender_can_write
cases.append(dict(id='D01_PAUSED_DISPATCHER', kind='COUNTEREXAMPLE',
    durable_charge=True, superseded_before_socket_write=True, old_socket_can_write=True,
    reason='external provider/socket does not validate Consul fence; freezing successors does not stop old sender'))

report = dict(schema='unified.authority.bounded-api-counterexamples.v1',
    result='BOUNDED_COUNTEREXAMPLES_CONFIRMED', cases=cases,
    qualification='DETERMINISTIC_API_PREDICATE_MODEL_ONLY_NOT_REAL_CONSUL_OR_HA_ACCEPTANCE',
    implemented_clock_or_containment=False, runtime_go=False, physical='NOT_RUN')
path = Path(__file__).with_name('bounded-counterexamples.json')
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'result': report['result'], 'cases': len(cases), 'qualification': report['qualification']}))
