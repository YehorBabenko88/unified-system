"""Inert worker-close provenance tests: no TLS, subprocesses, sockets or nodes."""
from collections import deque
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch
from unified_system.lan_transport import Connection, TransportError


class CloseAttributionTests(unittest.TestCase):
    def test_reader_failure_is_classified_without_raw_error_details(self):
        for channel, expected in (("control", "READER_CONTROL"), ("data", "READER_DATA")):
            with self.subTest(channel=channel):
                calls = []
                fake = SimpleNamespace(closed=False,
                    channels={channel: object()},
                    owner=SimpleNamespace(budget=object()),
                    peer_id="private-node", closed_event=threading.Event(),
                    close=lambda reason, *, source: calls.append((reason, source)))
                with patch("unified_system.lan_transport._read_frame",
                           side_effect=TransportError("CREDIT_BOUNDS")):
                    Connection._reader(fake, channel)
                self.assertEqual(calls, [("CREDIT_BOUNDS", expected)])

    def test_heartbeat_error_is_classified(self):
        calls = []
        fake = SimpleNamespace(
            closed_event=SimpleNamespace(wait=lambda _: False),
            _emit=lambda *a, **k: (_ for _ in ()).throw(TransportError("DEADLINE")),
            close=lambda reason, *, source: calls.append((reason, source)))
        Connection._heartbeat(fake)
        self.assertEqual(calls, [("DEADLINE", "HEARTBEAT")])

    def test_sender_error_is_classified(self):
        calls = []
        class FailingLock:
            def __enter__(self): raise TransportError("OVERLOADED")
            def __exit__(self, *args): return False
        fake = SimpleNamespace(cv=FailingLock(),
            close=lambda reason, *, source: calls.append((reason, source)))
        Connection._sender(fake, True)
        self.assertEqual(calls, [("OVERLOADED", "SENDER")])

    def test_close_keeps_first_cause_and_is_idempotent(self):
        released = []
        class FakeSocket:
            def __init__(self): self.closed = 0
            def shutdown(self, *_): return None
            def close(self): self.closed += 1
        sockets = [FakeSocket(), FakeSocket()]
        fake = SimpleNamespace(
            cv=threading.Condition(), closed=False, error=None,
            close_source="NONE", closed_event=threading.Event(),
            outgoing=deque(), incoming=deque(), queued_bytes=0,
            owner=SimpleNamespace(memory=SimpleNamespace(release=released.append)),
            reserved=0, control_held=0,
            channels={"control": sockets[0], "data": sockets[1]})
        Connection.close(fake, "CREDIT_BOUNDS", source="READER_DATA")
        Connection.close(fake, "OVERRIDE_NOT_ALLOWED", source="SENDER")
        self.assertTrue(fake.closed_event.is_set())
        self.assertEqual(fake.error, "CREDIT_BOUNDS")
        self.assertEqual(fake.close_source, "READER_DATA")
        self.assertEqual([s.closed for s in sockets], [1, 1])
        self.assertEqual(released, [0])

    def test_unexpected_close_origin_maps_to_other(self):
        class FakeSocket:
            def shutdown(self, *_): pass
            def close(self): pass
        fake = SimpleNamespace(
            cv=threading.Condition(), closed=False, error=None,
            close_source="NONE", closed_event=threading.Event(),
            outgoing=deque(), incoming=deque(), queued_bytes=0,
            owner=SimpleNamespace(memory=SimpleNamespace(release=lambda _: None)),
            reserved=0, control_held=0,
            channels={"control": FakeSocket(), "data": FakeSocket()})
        Connection.close(fake, "CLOSED", source="SECRET_HOST_PAYLOAD")
        self.assertEqual(fake.close_source, "OTHER")


if __name__ == "__main__":
    unittest.main()
