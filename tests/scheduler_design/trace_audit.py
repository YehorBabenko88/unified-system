"""Offline trace auditor and policy fixtures, never an authority or publisher.

Input facts MUST describe the atomic linearization snapshot, not an RPC precheck.
Passing an invented trace proves nothing about the actual source of those facts.
No tokens, networking, consensus, database writes or storage effects occur here.
"""
from datetime import timedelta
from zoneinfo import ZoneInfo


def audit(events):
    """Return violations in a supplied single-scope, ordered fixture history.

For rejected requests effect=False means *no* durable effects, not an error
response with unobserved partial writes. Fixture captures must establish this.
"""
    violations = []
    high_revision = 0
    high_epoch = 0
    committed_checkpoint = 1
    segments = set()
    for e in events:
        op = e['op']
        if op == 'restart':
            continue  # durable observed history is deliberately not reset
        if op == 'resume':
            if not e['verified']:
                violations.append('UNVERIFIED_CHECKPOINT')
            if e['checkpoint'] != committed_checkpoint:
                violations.append('UNCOMMITTED_CHECKPOINT')
            continue
        if op not in {'grant', 'supersede', 'renew', 'cancel', 'publish'}:
            raise ValueError('unknown fixture operation')
        if not e['effect']:
            continue
        if not e['quorum']:
            violations.append('NO_QUORUM')
        if e['generation'] != e['current_generation']:
            violations.append('GENERATION_MISMATCH')
        # A trace may start with an already active assignment, not its grant.
        high_revision = max(high_revision, e['current_revision'])
        high_epoch = max(high_epoch, e['current_epoch'])
        if op in {'grant', 'supersede'}:
            revision = e['assignment_revision']
            if revision <= max(high_revision, e['current_revision']):
                violations.append('REVISION_REUSED')
            if e['epoch'] <= high_epoch:
                violations.append('EPOCH_REUSED')
            high_revision = max(high_revision, revision)
            high_epoch = max(high_epoch, e['epoch'])
            continue
        if e['assignment_revision'] != e['current_revision']:
            violations.append('STALE_ASSIGNMENT')
        if e['epoch'] != e['current_epoch']:
            violations.append('STALE_EPOCH')
        if e['incarnation'] != e['current_incarnation']:
            violations.append('INCARNATION_MISMATCH')
        if e['grant_revision'] != e['current_grant_revision']:
            violations.append('STALE_GRANT')
        if op == 'cancel':
            continue
        if e['state'] not in {'ACTIVE', 'DRAINING'}:
            violations.append('TERMINAL_ASSIGNMENT')
        if e['time'] >= e['lease_expiry']:
            violations.append('LEASE_EXPIRED')
        if e['time'] >= e['reservation_expiry']:
            violations.append('RESERVATION_EXPIRED')
        if e['budget_revision'] != e['current_budget_revision']:
            violations.append('STORAGE_BUDGET_CHANGED')
        if op != 'publish':
            continue
        if e['state'] == 'DRAINING':
            if e['batch_id'] not in e['permitted_batches']:
                violations.append('BATCH_NOT_PERMITTED')
            if e['bytes'] > e['drain_remaining']:
                violations.append('DRAIN_EXHAUSTED')
        if e['bytes'] < 0 or e['bytes'] > e['remaining_bytes']:
            violations.append('RESERVATION_EXHAUSTED')
        if e['segment'] in segments:
            violations.append('DUPLICATE_EFFECT')
        segments.add(e['segment'])
        if e['checkpoint'] != committed_checkpoint or e['next_checkpoint'] <= e['checkpoint']:
            violations.append('CHECKPOINT_CONFLICT')
        committed_checkpoint = e['next_checkpoint']
    return violations


def active_at(instant, start_minute, end_minute, weekdays):
    """Half-open Berlin window; weekday belongs to the starting day.

Equal endpoints are rejected (ambiguous zero hours versus all day).
ZoneInfoNotFoundError is intentionally fail-closed when tzdata is absent.
"""
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('an aware instant is required')
    if (type(start_minute) is not int or type(end_minute) is not int
            or not 0 <= start_minute < 1440 or not 0 <= end_minute < 1440
            or start_minute == end_minute or any(type(d) is not int or d not in range(7) for d in weekdays)):
        raise ValueError('invalid schedule')
    local = instant.astimezone(ZoneInfo('Europe/Berlin'))
    minute = local.hour * 60 + local.minute
    if start_minute < end_minute:
        return local.weekday() in weekdays and start_minute <= minute < end_minute
    if minute >= start_minute:
        return local.weekday() in weekdays
    return minute < end_minute and (local - timedelta(days=1)).weekday() in weekdays


def admission(now_ms, observed_ms, max_age_ms, capacity, reserved, requested, healthy=True):
    """Pure one-dimension candidate check; does not reserve or grant anything.

Caller repeats for each typed resource dimension; max_age is TEST_ONLY input.
This fixture assumes exact observation time; production requires approved skew.
"""
    values = (now_ms, observed_ms, max_age_ms, capacity, reserved, requested)
    if any(type(v) is not int or v < 0 for v in values) or max_age_ms == 0 or requested == 0:
        raise ValueError('invalid resource observation/request')
    if observed_ms > now_ms:
        return 'CAPACITY_FUTURE'
    if now_ms - observed_ms > max_age_ms:
        return 'CAPACITY_STALE'
    if not healthy:
        return 'UNHEALTHY'
    if reserved > capacity or requested > capacity - reserved:
        return 'QUEUED_RESOURCES'
    return 'ADMIT_CANDIDATE'
