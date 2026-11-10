"""SOURCE-ONLY review1 controls: helper is deliberately NOT implemented yet.

Do not import/compile/run this module under the initial source lease. Later
authorized controls must import the actual tests/preparation_child_observer.py.
These inert objects cannot launch, read a pipe, kill, wait or prove native state.
"""
import hashlib
import json
import unittest

from preparation_child_observer import PreparationChildObserver


class Tripwire:
    def __init__(self, calls):
        self.calls = calls

    def forbidden(self, *args, **kwargs):
        self.calls.append('FORBIDDEN_IO_OR_WAIT')
        raise AssertionError('observer performed forbidden operation')

    read = readline = readinto = write = flush = close = fileno = forbidden
    communicate = kill = terminate = wait = join = forbidden


class InertThread(Tripwire):
    def __init__(self, calls, name, value):
        super().__init__(calls)
        self.name, self.value = name, value

    def is_alive(self):
        self.calls.append(self.name)
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


class InertChild(Tripwire):
    def __init__(self, poll=None, stdout=b'', stderr=b''):
        self.calls = []
        super().__init__(self.calls)
        self.pid = 101
        self.returncode = None
        self.poll_value = poll
        self.stdout_thread = InertThread(self.calls, 'stdout_thread', True)
        self.stderr_thread = InertThread(self.calls, 'stderr_thread', False)
        self._stdout_buff = [stdout]
        self._stderr_buff = [stderr]

    def poll(self):
        self.calls.append('poll')
        if isinstance(self.poll_value, Exception):
            raise self.poll_value
        self.returncode = self.poll_value
        return self.poll_value

    @property
    def stdin(self):
        return self.forbidden()

    @property
    def stdout(self):
        return self.forbidden()

    @property
    def stderr(self):
        return self.forbidden()


class PreparationChildObserverControls(unittest.TestCase):
    def bound_child(self, child):
        observer = PreparationChildObserver()
        token = observer.begin_constructor(at_ns=10)
        observer.end_constructor(token, child, at_ns=20)
        observer.begin_communicate(token, at_ns=30)
        return observer, token

    def exported(self, observer):
        raw = observer.export_json()
        self.assertIs(type(raw), bytes)
        self.assertLessEqual(len(raw), 16384)
        result = json.loads(raw)
        self.assertEqual(set(result), {'schema', 'events', 'retained_children',
                                      'dropped_events', 'incomplete'})
        self.assertEqual(result['schema'], 'preparation.child-observer.v1-review1')
        return result

    def test_fixed_limits_and_constructor_registration_are_observation_only(self):
        self.assertEqual((PreparationChildObserver.MAX_CHILDREN,
                          PreparationChildObserver.MAX_EVENTS,
                          PreparationChildObserver.HASH_PREFIX_BYTES,
                          PreparationChildObserver.MAX_EXPORT_BYTES), (1, 8, 256, 16384))
        child = InertChild()
        observer = PreparationChildObserver()
        token = observer.begin_constructor(at_ns=10)
        observer.end_constructor(token, child, at_ns=20)
        self.assertEqual(child.calls, [])
        result = self.exported(observer)
        self.assertEqual([e['kind'] for e in result['events']],
                         ['CONSTRUCTOR_BEGIN', 'CONSTRUCTOR_END'])
        self.assertEqual(result['events'][1]['elapsed_ns'], 10)
        self.assertEqual(result['retained_children'], 1)

    def test_timeout_samples_poll_then_threads_without_pipe_or_cleanup_calls(self):
        child = InertChild(poll=None, stdout=b'abc', stderr=b'error')
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        event = self.exported(observer)['events'][-1]
        self.assertEqual(child.calls, ['poll', 'stdout_thread', 'stderr_thread'])
        self.assertEqual(event['kind'], 'COMMUNICATE_TIMEOUT')
        self.assertEqual(event['elapsed_ns'], 20)
        self.assertEqual(event['poll'], {'state': 'RUNNING', 'returncode': None})
        self.assertEqual(event['stdout_thread'], 'ALIVE')
        self.assertEqual(event['stderr_thread'], 'STOPPED')
        self.assertEqual(event['stdout_buffer']['bytes'], 3)

    def test_exit23_with_live_stdout_reader_is_recorded_not_reinterpreted(self):
        child = InertChild(poll=23)
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        event = self.exported(observer)['events'][-1]
        self.assertEqual(event['poll'], {'state': 'EXITED', 'returncode': 23})
        self.assertEqual(child.returncode, 23)
        self.assertEqual(event['stdout_thread'], 'ALIVE')
        self.assertNotIn('root_cause', event)
        self.assertNotIn('cleanup_confirmed', event)
        self.assertNotIn('authority', event)

    def test_buffer_hash_is_only_bounded_prefix_not_full_output(self):
        payload = b'private-output-' + b'x' * 1024
        child = InertChild(stdout=payload)
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        buffer = self.exported(observer)['events'][-1]['stdout_buffer']
        self.assertEqual(buffer, dict(state='PRESENT', chunks=1, bytes=len(payload),
                         prefix_bytes=256,
                         prefix_sha256=hashlib.sha256(payload[:256]).hexdigest()))
        self.assertNotIn(payload, observer.export_json())
        self.assertNotIn(b'private-output-', observer.export_json())
        self.assertNotEqual(buffer['prefix_sha256'], hashlib.sha256(payload).hexdigest())

    def test_missing_or_empty_cpython_buffers_and_threads_are_explicit(self):
        child = InertChild()
        del child._stdout_buff
        del child.stdout_thread
        child._stderr_buff = []
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        event = self.exported(observer)['events'][-1]
        self.assertEqual(event['stdout_thread'], 'ABSENT')
        self.assertEqual(event['stdout_buffer']['state'], 'ABSENT')
        self.assertEqual(event['stderr_buffer'],
                         dict(state='EMPTY', chunks=0, bytes=0,
                              prefix_bytes=0, prefix_sha256=None))
        self.assertEqual(child.calls, ['poll', 'stderr_thread'])

    def test_unsupported_buffers_are_not_coerced_hashed_or_iterated(self):
        class NoConversion:
            def __len__(self):
                raise AssertionError('unexpected len')
            def __bytes__(self):
                raise AssertionError('unexpected conversion')
            def __iter__(self):
                raise AssertionError('unexpected iteration')
        child = InertChild()
        child._stdout_buff = NoConversion()
        child._stderr_buff = [NoConversion()]
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        result = self.exported(observer)
        event = result['events'][-1]
        self.assertEqual(event['stdout_buffer']['state'], 'UNSUPPORTED')
        self.assertEqual(event['stderr_buffer']['state'], 'UNSUPPORTED')
        self.assertTrue(result['incomplete'])
        self.assertNotIn('FORBIDDEN_IO_OR_WAIT', child.calls)

    def test_poll_or_thread_error_is_unknown_without_exception_text(self):
        child = InertChild(poll=OSError('sensitive exception text'))
        child.stdout_thread.value = RuntimeError('another secret')
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        result = self.exported(observer)
        event = result['events'][-1]
        self.assertEqual(event['poll'], {'state': 'ERROR', 'returncode': None})
        self.assertEqual(event['stdout_thread'], 'ERROR')
        self.assertTrue(result['incomplete'])
        self.assertNotIn(b'sensitive', observer.export_json())
        self.assertNotIn(b'secret', observer.export_json())

    def test_event_budget_exhaustion_does_not_sample_child_again(self):
        child = InertChild()
        observer, token = self.bound_child(child)
        for _ in range(5):
            observer.communicate_timeout(token, at_ns=50)
        self.assertEqual(len(self.exported(observer)['events']), 8)
        calls = list(child.calls)
        observer.communicate_timeout(token, at_ns=50)
        result = self.exported(observer)
        self.assertEqual(child.calls, calls)
        self.assertEqual(len(result['events']), 8)
        self.assertEqual(result['dropped_events'], 1)
        self.assertTrue(result['incomplete'])

    def test_second_constructor_is_declined_without_observing_another_child(self):
        child = InertChild()
        observer, token = self.bound_child(child)
        other = InertChild()
        self.assertIsNone(observer.begin_constructor(at_ns=40))
        observer.end_constructor(None, other, at_ns=45)
        self.assertEqual(other.calls, [])
        self.assertEqual(self.exported(observer)['retained_children'], 1)
        self.assertTrue(self.exported(observer)['incomplete'])

    def test_export_is_a_detached_bounded_copy_with_no_child_effects(self):
        child = InertChild()
        observer, token = self.bound_child(child)
        before = list(child.calls)
        raw = observer.export_json()
        decoded = json.loads(raw)
        decoded['events'].clear()
        self.assertEqual(observer.export_json(), raw)
        self.assertEqual(child.calls, before)

    def test_invalid_timing_or_unknown_token_never_polls_or_mutates_history(self):
        child = InertChild()
        observer, token = self.bound_child(child)
        before = observer.export_json()
        for bad in (True, -1, 2**63, 29):
            with self.subTest(at_ns=bad), self.assertRaises(ValueError):
                observer.communicate_timeout(token, at_ns=bad)
        self.assertEqual(observer.export_json(), before)
        self.assertEqual(child.calls, [])
        with self.assertRaises(ValueError):
            observer.communicate_timeout(999, at_ns=50)
        self.assertEqual(observer.export_json(), before)
        self.assertEqual(child.calls, [])

    def test_failed_constructor_and_two_observed_communicate_calls_do_not_do_cleanup(self):
        failed = PreparationChildObserver()
        token = failed.begin_constructor(at_ns=10)
        failed.constructor_failed(token, at_ns=20)
        result = self.exported(failed)
        self.assertEqual(result['retained_children'], 0)
        self.assertEqual(result['events'][-1]['kind'], 'CONSTRUCTOR_ERROR')
        child = InertChild()
        observer, token = self.bound_child(child)
        observer.communicate_timeout(token, at_ns=50)
        # Standard subprocess.run may itself communicate after its own kill.
        # This records a caller-entered second call; the observer never calls it.
        observer.begin_communicate(token, at_ns=60)
        observer.end_communicate(token, at_ns=70)
        self.assertEqual(self.exported(observer)['events'][-1]['elapsed_ns'], 10)
        self.assertNotIn('FORBIDDEN_IO_OR_WAIT', child.calls)
