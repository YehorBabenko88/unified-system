"""Six stdlib DATA models; NOT actual broker/native reproduction or permission.

No project imports or fixture execution. Identity fields are deliberately small
projections, not native schemas, TLS/issuer custody or a Consul implementation.
Store snapshots and local validity flags are supplied DATA, never live probes.
"""
from dataclasses import dataclass, replace
import unittest


_KEYS = ('generation', 'profile:F', 'principal:A', 'policy:P', 'principal-session:S')


@dataclass(frozen=True)
class _Record:
    key: str
    index: int
    value: tuple
    session: str = ''


@dataclass(frozen=True)
class _ContextData:
    issuer: object
    connection: object
    generation: str = 'G0'
    local_live: bool = True
    peer_matches: bool = True
    expiry_current: bool = True
    clock_certain: bool = True


@dataclass(frozen=True)
class _ViewData:
    rows: tuple
    available: bool = True
    known_leader: bool = True
    acl_filtered: bool = False


@dataclass(frozen=True)
class _CaptureData:
    rows: tuple
    issuer: object
    connection: object
    original: bytes = b'model-original'
    scope: str = 'READ_RESEARCH'


def _stable_rows():
    return (
        _Record('generation', 10, (('generation', 'G0'),)),
        _Record('profile:F', 11, (('profile', 'F'), ('actor', 'A'), ('service', 'V'))),
        _Record('principal:A', 12, (('actor', 'A'), ('service', 'V'), ('policy', 'P'),
                                   ('quota', 'Q'), ('profile', 'F'), ('state', 'ACTIVE'))),
        _Record('policy:P', 13, (('actor', 'A'), ('profile', 'F'), ('policy', 'P'),
                                ('revision', '1'), ('state', 'ACTIVE'), ('scope', 'READ_RESEARCH'))),
        _Record('principal-session:S', 14, (('actor', 'A'), ('service', 'V'), ('policy', 'P'),
                                           ('quota', 'Q'), ('profile', 'F'), ('session', 'S')), 'S'),
    )


def _timeline():
    initial = _stable_rows()
    generation_changed = (replace(initial[0], index=20, value=(('generation', 'G1'),)),) + initial[1:]
    revoked = list(generation_changed)
    revoked[2] = replace(initial[2], index=21, value=initial[2].value[:-1] + (('state', 'REVOKED'),))
    policy_changed = list(revoked)
    policy_changed[3] = replace(initial[3], index=22, value=tuple(
        (key, '2' if key == 'revision' else value) for key, value in initial[3].value))
    return initial, generation_changed, tuple(revoked), tuple(policy_changed)


def _model_sequential_capture(states, cuts, context):
    # Each supplied cut is an independently consistent historical read.
    rows = tuple(states[cut][position] for position, cut in enumerate(cuts))
    return _capture_projection(rows, context, context)


def _model_atomic_capture(view, context, *, after=None):
    if not _closed_view(view):
        return None
    return _capture_projection(view.rows, context, context if after is None else after)


def _model_reobserve(view, captured):
    # Projection of _observe's exact key/index/raw/session comparisons.
    return (_closed_view(view) and type(captured) is _CaptureData
            and view.rows == captured.rows)


def _model_open_session_fence(view, preliminary):
    # Four preliminary identity check-index operations; stable leader assumed.
    return (_closed_view(view) and type(preliminary) is tuple and len(preliminary) == 4
            and all(type(old) is _Record and (old.key, old.index) == (current.key, current.index)
                    for old, current in zip(preliminary, view.rows[:4])))


def _model_local_require(captured, context, *, issuer, original, scope):
    # No store argument or native re-read: deliberately a historical boundary.
    return (type(captured) is _CaptureData and _local_live(context)
            and context.issuer is issuer and captured.issuer is issuer
            and captured.connection is context.connection
            and type(original) is bytes and 0 < len(original) <= 16384
            and original == captured.original
            and type(scope) is str and scope == captured.scope == 'READ_RESEARCH')


def _local_live(context):
    return (type(context) is _ContextData and all(flag is True for flag in
            (context.local_live, context.peer_matches, context.expiry_current, context.clock_certain)))


def _closed_view(view):
    if (type(view) is not _ViewData or view.available is not True
            or view.known_leader is not True or view.acl_filtered is not False
            or type(view.rows) is not tuple or len(view.rows) != 5):
        return False
    for key, row in zip(_KEYS, view.rows):
        if (type(row) is not _Record or row.key != key or type(row.index) is not int
                or not 0 < row.index < 2**63 or type(row.session) is not str
                or type(row.value) is not tuple or not 1 <= len(row.value) <= 6):
            return False
        names = set()
        for pair in row.value:
            if (type(pair) is not tuple or len(pair) != 2
                    or any(type(item) is not str for item in pair) or pair[0] in names):
                return False
            names.add(pair[0])
    return True


def _capture_projection(rows, before, after):
    if not _closed_view(_ViewData(rows)) or not _local_live(before):
        return None
    generation, profile, principal, policy, lock = (dict(row.value) for row in rows)
    if (generation != {'generation': before.generation}
            or profile != {'profile': 'F', 'actor': 'A', 'service': 'V'}
            or principal != {'actor': 'A', 'service': 'V', 'policy': 'P', 'quota': 'Q',
                             'profile': 'F', 'state': 'ACTIVE'}
            or set(policy) != {'actor', 'profile', 'policy', 'revision', 'state', 'scope'}
            or any(policy[key] != value for key, value in
                   (('actor', 'A'), ('profile', 'F'), ('policy', 'P'),
                    ('state', 'ACTIVE'), ('scope', 'READ_RESEARCH')))
            or not policy['revision'].isascii() or not policy['revision'].isdecimal()
            or not 1 <= len(policy['revision']) <= 19 or policy['revision'].startswith('0')
            or not 0 < int(policy['revision']) < 2**63
            or lock != {'actor': 'A', 'service': 'V', 'policy': 'P', 'quota': 'Q',
                        'profile': 'F', 'session': 'S'} or rows[-1].session != 'S'):
        return None
    captured = _CaptureData(rows, before.issuer, before.connection)
    if not _model_local_require(captured, after, issuer=before.issuer,
                                original=b'model-original', scope='READ_RESEARCH'):
        return None
    return captured


class ResearchIdentityCaptureAtomicityModelTests(unittest.TestCase):
    def setUp(self):
        self.issuer = object()
        self.context = _ContextData(self.issuer, object())

    def test_model_stable_capture_accepts_unequal_per_key_indexes(self):
        # Break caught: rejecting unequal indexes or losing stable positive DATA.
        rows = _stable_rows()
        sequential = _model_sequential_capture((rows,), (0, 0, 0, 0, 0), self.context)
        atomic = _model_atomic_capture(_ViewData(rows), self.context)
        self.assertIsInstance(sequential, _CaptureData)
        self.assertIsInstance(atomic, _CaptureData)
        self.assertEqual(tuple(row.index for row in atomic.rows), (10, 11, 12, 13, 14))
        self.assertEqual(atomic.rows, rows)
        self.assertEqual(sequential.rows, rows)

    def test_model_interleaving_accepts_never_coexisting_sequential_capture_only(self):
        # Break caught: presenting records selected at different cuts as one view.
        states = _timeline()
        sequential = _model_sequential_capture(states, (0, 0, 0, 3, 3), self.context)
        self.assertIsInstance(sequential, _CaptureData)
        self.assertEqual(tuple(row.index for row in sequential.rows), (10, 11, 12, 22, 14))
        self.assertNotIn(sequential.rows, states)
        before = _model_atomic_capture(_ViewData(states[0]), self.context)
        self.assertIsInstance(before, _CaptureData)
        self.assertEqual(tuple(row.index for row in before.rows), (10, 11, 12, 13, 14))
        for cut in (1, 2, 3):
            with self.subTest(cut=cut):
                self.assertIsNone(_model_atomic_capture(_ViewData(states[cut]), self.context))
        self.assertEqual(dict(sequential.rows[2].value)['state'], 'ACTIVE')
        self.assertEqual(dict(sequential.rows[3].value)['revision'], '2')

    def test_model_existing_reobserve_and_open_session_reject_mixed_capture(self):
        # Break caught: dropping exact reobservation or a preliminary index fence.
        initial, _, _, current = _timeline()
        mixed_rows = initial[:3] + (current[3], current[4])
        mixed = _CaptureData(mixed_rows, self.issuer, self.context.connection)
        self.assertFalse(_model_reobserve(_ViewData(current), mixed))
        self.assertFalse(_model_open_session_fence(_ViewData(current), mixed_rows[:4]))
        stable = _CaptureData(initial, self.issuer, self.context.connection)
        self.assertTrue(_model_reobserve(_ViewData(initial), stable))
        self.assertTrue(_model_open_session_fence(_ViewData(initial), initial[:4]))
        for position in range(4):
            changed = list(initial)
            changed[position] = replace(changed[position], index=30 + position)
            with self.subTest(fenced_key=position):
                self.assertFalse(_model_open_session_fence(_ViewData(tuple(changed)), initial[:4]))
        for field, value in (('index', 31), ('value', (('different', 'DATA'),)), ('session', 'OTHER')):
            changed = initial[:-1] + (replace(initial[-1], **{field: value}),)
            with self.subTest(reobserve_field=field):
                self.assertFalse(_model_reobserve(_ViewData(changed), stable))

    def test_model_session_invalidation_before_and_after_snapshot_bounds_history(self):
        # Break caught: accepting a released lock, or inventing native freshness.
        rows = _stable_rows()
        released = rows[:-1] + (replace(rows[-1], index=40, session=''),)
        self.assertIsNone(_model_atomic_capture(_ViewData(released), self.context))
        historical = _model_atomic_capture(_ViewData(rows), self.context)
        self.assertIsInstance(historical, _CaptureData)
        self.assertTrue(_model_local_require(historical, self.context, issuer=self.issuer,
                                            original=b'model-original', scope='READ_RESEARCH'))
        self.assertFalse(_model_reobserve(_ViewData(released), historical))
        # Local require has no store argument: a later external change is invisible.
        self.assertTrue(_model_local_require(historical, self.context, issuer=self.issuer,
                                            original=b'model-original', scope='READ_RESEARCH'))

    def test_model_snapshot_rejects_unavailable_or_malformed_inventory(self):
        # Break caught: accepting incomplete, filtered, aliased or malformed views.
        rows = _stable_rows()
        bad = (
            _ViewData(rows, available=False), _ViewData(rows, known_leader=False),
            _ViewData(rows, acl_filtered=True), _ViewData(rows[:-1]),
            _ViewData(rows + (rows[0],)), _ViewData((rows[1], rows[0]) + rows[2:]),
            _ViewData(rows[:1] + (rows[0],) + rows[2:]),
            _ViewData(rows[:3] + (replace(rows[3], key='policy:OTHER'),) + rows[4:]),
            _ViewData((replace(rows[0], index=True),) + rows[1:]),
            _ViewData((replace(rows[0], index=0),) + rows[1:]),
            _ViewData(rows[:2] + (replace(rows[2], value=rows[2].value + (('state', 'ACTIVE'),)),) + rows[3:]),
        )
        for number, view in enumerate(bad):
            with self.subTest(invalid_view=number):
                self.assertIsNone(_model_atomic_capture(view, self.context))
        self.assertIsInstance(_model_atomic_capture(_ViewData(rows), self.context), _CaptureData)

    def test_model_local_binding_and_invalidation_checks_remain_required(self):
        # Break caught: accepting wrong fixed issuer/original/scope or post-await loss.
        rows = _stable_rows()
        captured = _CaptureData(rows, self.issuer, self.context.connection)
        self.assertFalse(_model_local_require(captured, self.context, issuer=object(),
                                             original=b'model-original', scope='READ_RESEARCH'))
        for original, scope in ((b'changed', 'READ_RESEARCH'), (b'model-original', 'SUBMIT_RESEARCH'),
                                (b'', 'READ_RESEARCH'), (b'x' * 16385, 'READ_RESEARCH')):
            with self.subTest(original_length=len(original), scope=scope):
                self.assertFalse(_model_local_require(captured, self.context, issuer=self.issuer,
                                                     original=original, scope=scope))
        for field in ('local_live', 'peer_matches', 'expiry_current', 'clock_certain'):
            invalid = replace(self.context, **{field: False})
            with self.subTest(local_loss=field):
                self.assertIsNone(_model_atomic_capture(_ViewData(rows), invalid))
                self.assertIsNone(_model_atomic_capture(_ViewData(rows), self.context, after=invalid))
                self.assertFalse(_model_local_require(captured, invalid, issuer=self.issuer,
                                                     original=b'model-original', scope='READ_RESEARCH'))
        self.assertTrue(_model_local_require(captured, self.context, issuer=self.issuer,
                                            original=b'model-original', scope='READ_RESEARCH'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
