"""Opt-in REAL backend contract targets. No backend/model replacement is supplied.

Default discovery schedules zero native cases and reports NOT_RUN. Explicit
--run-native-contracts runs the cases and fails at the absent actual dependency.
This deliberate dependency RED is NOT a reproduced native safety regression.
"""
from dataclasses import dataclass
import json
import os
import sys
import unittest
import uuid


class ActualBackendUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ScenarioObservation:
    """Private TEST observations, not a wire API, native proof or permission.

    A future actual owner fixture must derive these from verified native records
    and preserve raw source/endpoint/receipt/transaction evidence. A caller-made
    instance or passing these assertions cannot admit any worker or backend.
    """
    assignment_status: str
    publication_status: str
    supersession_status: str
    assignment_effects: int
    publication_effects: int
    debit_effects: int
    checkpoint_effects: int
    assignment_revision_before: str
    assignment_revision_after: str
    original_request_id: str
    observed_request_id: str
    historical_receipt_before: bytes | None
    historical_receipt_after: bytes | None
    native_linearization_order: tuple[str, ...]


async def open_actual_owner_fixture():
    """Intentionally unbound until exact A2/A4 supported endpoint/schema ACK.

    Not a permissive provider stub. No environment plugin, fake issuer, Consul
    process launch, office namespace, KV write, boolean capability or old model.
    Future private fixture ABI is test-only: await run_scenario(name), await close().
    It will need actual owner implementation and joint review before invocation.
    """
    raise ActualBackendUnavailable(
        'A2 actual Assignment producer NONE; A4 actual reservation/publication '
        'backend NONE; supported endpoint/schema ACK absent. Native contract '
        'assertions NOT_RUN; do not substitute model18/UNWIRED/Mux/lease metadata.'
    )


def positive_revision(value):
    if (type(value) is not str or not value.isascii() or not value.isdecimal()
            or value.startswith('0') or not 0 < int(value) <= 9223372036854775807):
        raise AssertionError('actual monotonic revision must be positive canonical u63 string')
    return int(value)


class ActualAssignmentBackendContracts(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fixture = await open_actual_owner_fixture()
        self.addAsyncCleanup(self.fixture.close)

    async def scenario(self, name):
        observed = await self.fixture.run_scenario(name)
        self.assertIs(type(observed), ScenarioObservation)
        for value in (observed.original_request_id, observed.observed_request_id):
            self.assertIs(type(value), str)
            parsed = uuid.UUID(value)
            self.assertEqual(str(parsed), value)
            self.assertEqual(parsed.version, 4)
        for count in (observed.assignment_effects, observed.publication_effects, observed.debit_effects, observed.checkpoint_effects):
            self.assertIs(type(count), int)
            self.assertGreaterEqual(count, 0)
            self.assertLessEqual(count, 1)
        for status, effects in ((observed.assignment_status, observed.assignment_effects),
                                (observed.publication_status, observed.publication_effects)):
            self.assertIn(status, ('COMMITTED', 'REJECTED', 'UNKNOWN', 'UNAVAILABLE'))
            if status in ('COMMITTED', 'REJECTED'):
                self.assertEqual(effects, int(status == 'COMMITTED'))
            # UNKNOWN/UNAVAILABLE alone cannot terminate an earlier uncertain
            # original command; scenario-specific native evidence is required.
        self.assertEqual(observed.original_request_id, observed.observed_request_id,
                         'uncertainty/conflict must not rekey the original intent')
        if name in ('SUPERSESSION_THEN_OLD_PUBLICATION',
                    'PUBLICATION_THEN_SUPERSESSION',
                    'CONCURRENT_SUPERSESSION_PUBLICATION'):
            # Initial assignment is fixture preparation, not a tested effect.
            # Here the sole tested assignment mutation is this supersession.
            self.assertIn(observed.supersession_status, ('COMMITTED', 'REJECTED'))
            self.assertEqual(observed.assignment_status, observed.supersession_status)
            self.assertEqual(observed.assignment_effects,
                             int(observed.supersession_status == 'COMMITTED'))
            if observed.supersession_status == 'REJECTED':
                self.assertEqual(observed.assignment_revision_before,
                                 observed.assignment_revision_after)
        if observed.supersession_status == 'COMMITTED':
            self.assertGreater(positive_revision(observed.assignment_revision_after), positive_revision(observed.assignment_revision_before))
        return observed

    async def test_stale_generation_cannot_create_assignment_or_publication(self):
        r = await self.scenario('STALE_GENERATION')
        self.assertEqual(r.assignment_status, 'REJECTED')
        self.assertEqual(r.publication_status, 'REJECTED')
        self.assertEqual((r.assignment_effects, r.publication_effects, r.debit_effects, r.checkpoint_effects), (0,0,0,0))
        self.assertEqual(r.assignment_revision_before, r.assignment_revision_after)

    async def test_native_no_quorum_preserves_original_intent_without_mutation(self):
        # Only A2-owned isolated voters may be stopped by the eventual fixture;
        # no office stop, network partition, guessed boolean or topology rewrite.
        r = await self.scenario('ACTUAL_TEST_STAND_NO_QUORUM')
        self.assertIn(r.assignment_status, ('UNAVAILABLE','UNKNOWN'))
        self.assertIn(r.publication_status, ('UNAVAILABLE','UNKNOWN'))
        self.assertNotEqual(r.supersession_status, 'COMMITTED')
        self.assertEqual((r.assignment_effects, r.publication_effects, r.debit_effects, r.checkpoint_effects), (0,0,0,0))
        self.assertEqual(r.assignment_revision_before, r.assignment_revision_after)

    async def test_supersession_first_rejects_old_worker_publication(self):
        r = await self.scenario('SUPERSESSION_THEN_OLD_PUBLICATION')
        self.assertEqual(r.supersession_status, 'COMMITTED')
        self.assertEqual(r.publication_status, 'REJECTED')
        self.assertGreater(positive_revision(r.assignment_revision_after), positive_revision(r.assignment_revision_before))
        self.assertEqual((r.publication_effects, r.debit_effects, r.checkpoint_effects), (0,0,0))
        self.assertEqual(r.native_linearization_order, ('SUPERSESSION',))

    async def test_publication_first_survives_as_one_immutable_historical_commit(self):
        r = await self.scenario('PUBLICATION_THEN_SUPERSESSION')
        self.assertEqual((r.publication_status, r.supersession_status), ('COMMITTED','COMMITTED'))
        self.assertEqual((r.publication_effects, r.debit_effects, r.checkpoint_effects), (1,1,1))
        self.assertIs(type(r.historical_receipt_before), bytes)
        self.assertTrue(r.historical_receipt_before)
        self.assertEqual(r.historical_receipt_before, r.historical_receipt_after)
        self.assertEqual(r.native_linearization_order, ('PUBLICATION','SUPERSESSION'))

    async def test_concurrent_supersession_publication_has_one_native_order(self):
        r = await self.scenario('CONCURRENT_SUPERSESSION_PUBLICATION')
        self.assertIn(r.publication_status, ('COMMITTED','REJECTED'))
        self.assertIn(r.supersession_status, ('COMMITTED','REJECTED'))
        self.assertTrue('COMMITTED' in (r.publication_status, r.supersession_status))
        committed = int(r.publication_status == 'COMMITTED')
        self.assertEqual((r.publication_effects, r.debit_effects, r.checkpoint_effects), (committed,committed,committed))
        if committed:
            self.assertIs(type(r.historical_receipt_before), bytes)
            self.assertTrue(r.historical_receipt_before)
            self.assertEqual(r.historical_receipt_before, r.historical_receipt_after)
        expected = tuple(op for op in r.native_linearization_order if op in ('PUBLICATION','SUPERSESSION'))
        self.assertEqual(r.native_linearization_order, expected)
        self.assertEqual(len(expected), len(set(expected)))
        if r.publication_status == r.supersession_status == 'COMMITTED':
            self.assertEqual(expected, ('PUBLICATION','SUPERSESSION'))
        elif committed:
            self.assertEqual(expected, ('PUBLICATION',))
        else:
            self.assertEqual(expected, ('SUPERSESSION',))


def load_tests(loader, standard_tests, pattern):
    if os.environ.get('AGENT5_RUN_NATIVE_ASSIGNMENT_CONTRACTS') != '1':
        print(json.dumps(dict(status='NOT_RUN_ACTUAL_BINDING_UNAVAILABLE', scheduled_native_cases=0,
                              native_acceptance=False, reason='explicit native contract selection and actual owner ACK required')), file=sys.stderr)
        return unittest.TestSuite()
    return loader.loadTestsFromTestCase(ActualAssignmentBackendContracts)


if __name__ == '__main__':
    if '--run-native-contracts' not in sys.argv:
        print(json.dumps(dict(status='UNAVAILABLE', native_acceptance=False,
                              next_action='exact A2/A4 supported contracts; --run-native-contracts exposes dependency RED')))
        raise SystemExit(2)
    sys.argv.remove('--run-native-contracts')
    os.environ['AGENT5_RUN_NATIVE_ASSIGNMENT_CONTRACTS'] = '1'
    unittest.main()
