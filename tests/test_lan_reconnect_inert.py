"""Pure reconnect-policy regression tests; no sockets, services or PKI."""
import threading
import time
import unittest
from unified_system.lan_transport import LanTransport, ReconnectPolicy, TransportError


class ReconnectLifecycleTests(unittest.TestCase):
    @staticmethod
    def fake_transport(outcomes):
        transport = object.__new__(LanTransport)
        transport.retry_counts = {}
        transport.connections = {}
        seen = []
        def connect(peer, *, deadline=None, cancel=None):
            seen.append(peer)
            value = outcomes.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        transport.connect = connect
        return transport, seen

    def test_disconnected_then_success_resets_backoff(self):
        marker = object()
        transport, seen = self.fake_transport([TransportError("DISCONNECTED"), marker])
        outcome = transport.connect_with_retry("LS5", deadline=time.monotonic()+3,
                                                policy=ReconnectPolicy(seed=2))
        self.assertIs(outcome, marker)
        self.assertEqual(seen, ["LS5", "LS5"])
        self.assertNotIn("LS5", transport.retry_counts)

    def test_first_success_resets_old_failure_count(self):
        marker = object()
        transport, seen = self.fake_transport([marker])
        transport.retry_counts["LS5"] = 8
        self.assertIs(transport.connect_with_retry("LS5", deadline=time.monotonic()+1), marker)
        self.assertEqual(seen, ["LS5"])
        self.assertEqual(transport.retry_counts, {})

    def test_cancel_before_connect(self):
        transport, seen = self.fake_transport([object()])
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaisesRegex(TransportError, "CANCELLED"):
            transport.connect_with_retry("LS5", deadline=time.monotonic()+1, cancel=cancelled)
        self.assertEqual(seen, [])

    def test_cancel_after_network_failure(self):
        cancelled = threading.Event()
        transport, seen = self.fake_transport([])
        def broken(peer, *, deadline=None, cancel=None):
            seen.append(peer)
            cancelled.set()
            raise TransportError("DISCONNECTED")
        transport.connect = broken
        with self.assertRaisesRegex(TransportError, "CANCELLED"):
            transport.connect_with_retry("LS5", deadline=time.monotonic()+1, cancel=cancelled)
        self.assertEqual(seen, ["LS5"])
        self.assertEqual(transport.retry_counts, {})

    def test_expired_cancelled_request_reports_cancelled(self):
        transport, seen = self.fake_transport([])
        cancelled = threading.Event()
        cancelled.set()
        with self.assertRaisesRegex(TransportError, "CANCELLED"):
            transport.connect_with_retry("LS5", deadline=time.monotonic()-1, cancel=cancelled)
        self.assertEqual(seen, [])

    def test_invalid_deadline_rejected_before_network(self):
        transport, seen = self.fake_transport([object()])
        for deadline in (float("nan"), float("inf"), None, "invalid"):
            with self.subTest(deadline=deadline):
                with self.assertRaisesRegex(TransportError, "DEADLINE"):
                    transport.connect_with_retry("LS5", deadline=deadline)
        self.assertEqual(seen, [])

    def test_authentication_error_never_retried(self):
        transport, seen = self.fake_transport([TransportError("AUTH_REJECTED"), object()])
        with self.assertRaisesRegex(TransportError, "AUTH_REJECTED"):
            transport.connect_with_retry("LS5", deadline=time.monotonic()+1)
        self.assertEqual(seen, ["LS5"])


    def test_bounded_long_reconnect_sequence_clears_history(self):
        class ImmediatePolicy:
            def __init__(self): self.attempts = []
            def retryable(self, code): return code == "DISCONNECTED"
            def delay(self, attempt):
                self.attempts.append(attempt)
                return 0
        marker = object()
        outcomes = [TransportError("DISCONNECTED") for _ in range(64)] + [marker]
        transport, seen = self.fake_transport(outcomes)
        policy = ImmediatePolicy()
        self.assertIs(transport.connect_with_retry("LS5", deadline=time.monotonic()+2,
                                                  policy=policy), marker)
        self.assertEqual(len(seen), 65)
        self.assertEqual(policy.attempts, list(range(64)))
        self.assertEqual(transport.retry_counts, {})

    def test_cancel_during_repeated_retry_backoff(self):
        cancel = threading.Event()
        class CancelAfterThird:
            def __init__(self): self.attempts = []
            def retryable(self, code): return code == "DISCONNECTED"
            def delay(self, attempt):
                self.attempts.append(attempt)
                if attempt == 2: cancel.set()
                return 0
        transport, seen = self.fake_transport(
            [TransportError("DISCONNECTED") for _ in range(5)])
        policy = CancelAfterThird()
        with self.assertRaisesRegex(TransportError, "CANCELLED"):
            transport.connect_with_retry("LS5", deadline=time.monotonic()+2,
                                         policy=policy, cancel=cancel)
        self.assertEqual(len(seen), 3)
        self.assertEqual(policy.attempts, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
