"""ROUND25 transport/model regressions; MOCK Consul only, never native lease proof."""
import asyncio
import base64
from dataclasses import replace
import json
import unittest
import uuid

import httpx

from unified_system.consul_authority import (
    ConsulConfig, ConsulLease, ConsulSessionAuthority, CoordinationUnavailable,
)
from unified_system.grid_writer_fence_model import (
    WriterLeaseIdentity, ResourceFenceBlocked, claim_model, stop_model,
)


OBSERVED = "4a91bb79-c488-1086-0664-30ccbc028eda"


class OpaqueSessionTests(unittest.TestCase):
    def identity(self, session=OBSERVED, token=40):
        return WriterLeaseIdentity(
            "owner", "isolated/round25", session, token,
            str(uuid.uuid4()), str(uuid.uuid4()), "a" * 64, "b" * 64,
        )

    def test_exact_server_identity_preserved_across_fencing_model(self):
        first = self.identity()
        self.assertEqual(first.session_id, OBSERVED)
        self.assertIsInstance(uuid.UUID(first.session_id), uuid.UUID)
        active = claim_model(None, first, legacy_quiescent=True)
        stopped = stop_model(active, first)
        next_owner = self.identity(str(uuid.uuid4()), token=41)
        self.assertEqual(claim_model(stopped, next_owner, legacy_quiescent=True).identity,
                         next_owner)
        with self.assertRaises(ResourceFenceBlocked):
            claim_model(stopped, self.identity(token=40), legacy_quiescent=True)
        self.assertNotEqual(first.session_id, OBSERVED.upper())
        with self.assertRaises(ResourceFenceBlocked):
            self.identity(OBSERVED.upper())
        # Safe opaque transport does not imply SQL eligibility.
        with self.assertRaises(ResourceFenceBlocked):
            self.identity("OpaqueSession_2")

    def test_sql_session_canonical_uuid_shapes_and_transport_separation(self):
        from unified_system.grid_writer_fence_model import (
            _consul_session_id, _sql_consul_session_id,
        )
        # Server-issued opaque syntax can safely travel through Consul APIs,
        # but the protected PostgreSQL ABI only accepts canonical UUID text.
        for value in (OBSERVED, str(uuid.uuid4()),
                      str(uuid.uuid5(uuid.NAMESPACE_DNS, "consul.example")),
                      str(uuid.uuid1())):
            with self.subTest(value=value):
                self.assertTrue(_consul_session_id(value))
                self.assertTrue(_sql_consul_session_id(value))
                self.assertEqual(self.identity(value).session_id, value)
        for value in ("OpaqueSession_2", "foreign-session", OBSERVED.upper(),
                      "ffffffff-ffff-ffff-ffff-ffffffffffff",
                      "00000000-0000-0000-0000-000000000000"):
            with self.subTest(value=value):
                # For non-canonical or SQL-ineligible values fail closed.
                if value not in ("ffffffff-ffff-ffff-ffff-ffffffffffff",
                                 "00000000-0000-0000-0000-000000000000"):
                    self.assertTrue(_consul_session_id(value))
                if _sql_consul_session_id(value):
                    # Canonical all-f/all-zero text has valid PG uuid syntax;
                    # it is NOT authority without authentic lease checks.
                    self.assertEqual(self.identity(value).session_id, value)
                else:
                    with self.assertRaises(ResourceFenceBlocked):
                        self.identity(value)

    def test_uuid4_instance_node_stay_strict(self):
        original = self.identity()
        for field in ("instance_id", "node_incarnation_id"):
            for bad in (OBSERVED, str(uuid.uuid5(uuid.NAMESPACE_DNS, "example")),
                        "OpaqueSession_2"):
                with self.subTest(field=field, value=bad):
                    with self.assertRaises(ResourceFenceBlocked):
                        replace(original, **{field: bad})

    def test_consul_acquire_validate_renew_and_owner_loss_mock_only(self):
        async def scenario():
            state = {"session": OBSERVED, "held": False, "value": b"",
                     "modify": 41, "active": True, "kv_put": 0}
            key = "isolated/round25/leader"

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": state["session"]})
                if path.startswith("/v1/session/renew/"):
                    return httpx.Response(200, json=[{"ID": state["session"]}])
                if path.startswith("/v1/session/destroy/"):
                    state["active"] = False
                    state["held"] = False
                    return httpx.Response(200, json=True)
                if path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["kv_put"] += 1
                        won = (state["active"] and
                               req.url.params.get("acquire") == state["session"] and
                               not state["held"])
                        if won:
                            state["held"] = True
                            state["value"] = req.content
                        return httpx.Response(200, json=won)
                    assert "consistent" in req.url.params
                    return httpx.Response(200, json=[{
                        "Key": key, "Session": state["session"] if state["held"] else "",
                        "ModifyIndex": state["modify"],
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                return httpx.Response(404)

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25", isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertEqual(lease, ConsulLease("owner", OBSERVED, 41))
                self.assertEqual(state["kv_put"], 1)
                self.assertTrue(await authority.validate(lease))
                self.assertFalse(await authority.validate(
                    ConsulLease("owner", OBSERVED, 42)))
                self.assertTrue(await authority.renew(lease))
                original_value = state["value"]
                state["modify"] += 1
                self.assertFalse(await authority.validate(lease))
                state["modify"] -= 1
                state["value"] = json.dumps({
                    "owner": "attacker", "session_id": OBSERVED,
                    "namespace": "isolated/round25",
                }).encode("ascii")
                self.assertFalse(await authority.validate(lease))
                state["value"] = original_value
                state["held"] = False
                self.assertFalse(await authority.validate(lease))
                state["held"] = True
                state["session"] = "foreign-session"
                self.assertFalse(await authority.validate(lease))
                # Never claim the altered KV row is a valid old lease.
        asyncio.run(scenario())

    def test_bad_renewal_reply_irreversibly_drops_local_deadline(self):
        # This is transport-level safety only. Never interpret as native
        # PostgreSQL, Consul consensus, Root grant or owner-transfer evidence.
        async def exercise(payload, *, lost_reply=False):
            state = {"held": False, "value": None}
            key = "isolated/round25/leader"
            calls = []

            def handler(req):
                calls.append((req.method, req.url.path))
                if req.url.path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if req.url.path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["held"] = True
                        state["value"] = req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": key, "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if req.url.path == "/v1/session/renew/" + OBSERVED:
                    if lost_reply:
                        raise httpx.ReadTimeout("unknown renewal response")
                    return httpx.Response(200, json=payload)
                raise AssertionError("unexpected Consul request")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25", isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                self.assertEqual(authority._deadlines[lease.session_id], 0)
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                self.assertEqual(sum(path == "/v1/session/renew/" + OBSERVED
                                     for _, path in calls), 1)

        bad = ([None], ["forged"], [False], [0], [[]],
               [{"ID": "foreign-session"}], [{"ID": OBSERVED.upper()}],
               {"ID": OBSERVED}, [], None, False)
        for payload in bad:
            with self.subTest(payload=repr(payload)):
                asyncio.run(exercise(payload))
        asyncio.run(exercise(None, lost_reply=True))

    def test_opaque_transport_only_session_never_creates_sql_identity(self):
        from unified_system.grid_writer_fence_model import (
            _consul_session_id, native_writer_admission,
        )
        session = "OpaqueSession_2"
        self.assertTrue(_consul_session_id(session))
        with self.assertRaises(ResourceFenceBlocked):
            self.identity(session)
        with self.assertRaisesRegex(
                ResourceFenceBlocked, "NATIVE_DB_FENCE_NOT_ADMITTED"):
            native_writer_admission()

    def test_original_lease_to_revoker_unknown_sql_remains_blocked(self):
        # One cross-module synthetic path using the ORIGINAL E revoker.
        # No real A Job / C PostgreSQL / Consul process and no native GO.
        from types import SimpleNamespace
        from unified_system.lab_writer_revoke import LabWriterRevoker
        from unified_system.lab_process_extinction import (
            RootProcessObservation, UNKNOWN,
        )

        async def exercise(*, uncertain_sql, remote_expired):
            events = []
            state = {"held": False, "value": b"", "destroy": 0}
            key = "isolated/round25/leader"

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["held"] = True
                        state["value"] = req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": key, "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy"] += 1
                    state["held"] = False
                    return httpx.Response(200, json=True)
                raise AssertionError("unexpected Consul path")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25", isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                identity = self.identity(token=lease.token)
                self.assertEqual(identity.session_id, lease.session_id)
                alive = {"value": True}
                guard = SimpleNamespace(_identity=identity, blocked=False)

                def block_transfer():
                    events.append("TRANSFER_BLOCKED")
                    guard.blocked = True

                guard.block_transfer = block_transfer

                def live_c(pg, *, identity, generation, backend_pid):
                    events.append("C_LIVE_READ")
                    if not alive["value"]:
                        raise ValueError("old backend gone")
                    return {
                        "schema": "lab-postgres-fence-revalidation.v1",
                        "scope": "ISOLATED_LAB_ONLY",
                        "resource_id": "grid-market-data-primary",
                        "owner": identity.owner,
                        "namespace": identity.namespace,
                        "generation": generation, "token": identity.token,
                        "backend_pid": backend_pid,
                        "backend_start": "2026-11-27T09:00:00+00:00",
                        "session_id": identity.session_id,
                        "instance_id": identity.instance_id,
                        "node_incarnation_id": identity.node_incarnation_id,
                        "source_sha256": identity.source_sha256,
                        "schema_sha256": identity.schema_sha256,
                        "db_backend_observed": True,
                        "db_fence_current_at_read": True,
                        "native_writer_admitted": False,
                        "trading_authorized": False,
                    }

                def exact_c(pg, *, owner, namespace, generation, token,
                            backend_pid, backend_start, timeout=120):
                    events.append("C_EXACT_REVOKE")
                    self.assertTrue(guard.blocked)
                    self.assertFalse(alive["value"])
                    self.assertEqual((owner, namespace, generation, token),
                                     ("owner", "isolated/round25", 9, lease.token))
                    self.assertEqual((backend_pid, backend_start),
                                     (4042, "2026-11-27T09:00:00+00:00"))
                    if uncertain_sql:
                        raise RuntimeError("SQL UPDATE outcome unknown")
                    return False

                exact_c.__module__ = "unified_system.lab_pg_fence"

                class Executor:
                    poisoned = False
                    async def call(self, task, timeout):
                        return task()

                class StopLane:
                    async def stop_owned(self, handle, *, timeout):
                        events.append("A_STOP")
                        alive["value"] = False
                    async def old_child_extinct(self, handle, *, timeout):
                        return RootProcessObservation(
                            "unified.root-process-observation.v1", UNKNOWN,
                            handle, 4042, ["created", "image"], "UNKNOWN",
                        )

                revoker = object.__new__(LabWriterRevoker)
                revoker._guard = guard
                revoker._driver = object()
                revoker._handle = "original-job"
                revoker._authority = authority
                revoker._lease = lease
                revoker._pg = object()
                revoker._c = SimpleNamespace(
                    revoke_lab_fence=exact_c,
                    revalidate_lab_fence=live_c,
                    LabAdmissionRejected=ValueError,
                )
                revoker._generation = 9
                revoker._token = lease.token
                revoker._backend_pid = 4042
                revoker._once = False
                revoker._last = None
                revoker._executor = Executor()
                revoker._stop_lane = StopLane()

                if remote_expired:
                    state["held"] = False
                    self.assertFalse(await authority.validate(lease))
                result = await revoker.revoke(blocking_timeout=1)
                self.assertEqual(result.result, "PARTIAL_DENIED")
                self.assertTrue(guard.blocked)
                self.assertFalse(result.sql_fence_revoked)
                self.assertFalse(result.old_backend_rejected)
                self.assertFalse(result.consul_released)
                self.assertFalse(result.native_admitted)
                self.assertFalse(result.trading_authorized)
                self.assertEqual(state["destroy"], 0)
                self.assertEqual(events, [
                    "TRANSFER_BLOCKED", "C_LIVE_READ", "A_STOP",
                    "C_EXACT_REVOKE",
                ])
                self.assertIs(await revoker.revoke(blocking_timeout=1), result)
                self.assertEqual(state["destroy"], 0)

        for uncertain_sql in (False, True):
            for remote_expired in (False, True):
                with self.subTest(uncertain_sql=uncertain_sql,
                                  remote_expired=remote_expired):
                    asyncio.run(exercise(
                        uncertain_sql=uncertain_sql,
                        remote_expired=remote_expired,
                    ))

    def test_destroy_false_or_lost_reply_retains_revoked_session_witness(self):
        # Genuine Consul destroy returns literal JSON true on success; even
        # HTTP 200 false is NOT proof that the old session was destroyed.
        # Preserve the locally revoked identity to permit exact retry.
        from unified_system.consul_authority import CoordinationLost

        async def exercise(first_reply):
            state = {"held": False, "value": b"", "reply": first_reply,
                     "destroy_calls": 0, "kv_reads": 0}
            key = "isolated/round25/leader"

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["held"] = True
                        state["value"] = req.content
                        return httpx.Response(200, json=True)
                    state["kv_reads"] += 1
                    return httpx.Response(200, json=[{
                        "Key": key,
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy_calls"] += 1
                    if state["reply"] == "lost":
                        raise httpx.ReadTimeout("destroy outcome unknown")
                    if state["reply"] == "false":
                        return httpx.Response(200, json=False)
                    if state["reply"] == "wrong_type":
                        return httpx.Response(200, json={"ok": True})
                    state["held"] = False
                    return httpx.Response(200, json=True)
                raise AssertionError("unexpected Consul request")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                if first_reply == "lost":
                    expected = CoordinationUnavailable
                else:
                    expected = CoordinationLost
                with self.assertRaises(expected):
                    await authority.release(lease)

                self.assertIs(authority._sessions[OBSERVED], lease)
                self.assertEqual(authority._deadlines[OBSERVED], 0)
                kv_reads = state["kv_reads"]
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                self.assertEqual(state["kv_reads"], kv_reads)
                self.assertEqual(state["destroy_calls"], 1)

                # A later, explicitly confirmed idempotent destroy may clean
                # the local tracking record; still never issue a writer grant.
                state["reply"] = "true"
                await authority.release(lease)
                self.assertEqual(state["destroy_calls"], 2)
                self.assertNotIn(OBSERVED, authority._sessions)
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))

        for first_reply in ("false", "lost", "wrong_type"):
            with self.subTest(first_reply=first_reply):
                asyncio.run(exercise(first_reply))

    def test_copied_equal_lease_cannot_validate_renew_release_or_write(self):
        # The canonical server identity and token are observable in the
        # Consul KV record; equality of three dataclass fields is not proof
        # that Root itself issued this exact in-memory session capability.
        from unified_system.consul_authority import CoordinationLost

        async def exercise():
            state = {"held": False, "value": b"", "destroy": 0,
                     "txn": 0, "renew": 0}
            key = "isolated/round25/leader"

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["held"] = True
                        state["value"] = req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": key,
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/session/renew/" + OBSERVED:
                    state["renew"] += 1
                    return httpx.Response(200, json=[{"ID": OBSERVED}])
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy"] += 1
                    state["held"] = False
                    return httpx.Response(200, json=True)
                if path == "/v1/txn":
                    state["txn"] += 1
                    return httpx.Response(200, json={"Results": []})
                raise AssertionError("unexpected Consul request")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                original = await authority.acquire("owner")
                forged = ConsulLease(original.owner, original.session_id,
                                     original.token)
                self.assertEqual(forged, original)
                self.assertIsNot(forged, original)
                self.assertFalse(await authority.validate(forged))
                self.assertFalse(await authority.renew(forged))
                await authority.release(forged)
                with self.assertRaises(CoordinationLost):
                    await authority.write_control(forged, "state", {"x": 1})
                self.assertEqual(
                    (state["destroy"], state["txn"], state["renew"]), (0, 0, 0))
                self.assertIs(authority._sessions[OBSERVED], original)
                self.assertTrue(await authority.validate(original))
                self.assertTrue(await authority.renew(original))
                await authority.release(original)
                self.assertEqual(state["destroy"], 1)
                self.assertNotIn(OBSERVED, authority._sessions)

        asyncio.run(exercise())

    def test_consul_txn_requires_target_kv_commit_result(self):
        from unified_system.consul_authority import CoordinationLost

        async def exercise(response, should_accept):
            state = {"value": b"", "held": False, "requests": []}
            key = "isolated/round25/leader"
            target = "isolated/round25/state/probe"

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["value"] = req.content
                        state["held"] = True
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": key, "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/txn":
                    sent = json.loads(req.content)
                    self.assertEqual(len(sent), 3)
                    self.assertEqual(
                        [item["KV"]["Verb"] for item in sent],
                        ["check-session", "check-index", "set"])
                    self.assertEqual(sent[0]["KV"]["Session"], OBSERVED)
                    self.assertEqual(sent[1]["KV"]["Index"], 41)
                    self.assertEqual(sent[2]["KV"]["Key"], target)
                    state["requests"].append(sent)
                    return httpx.Response(200, json=response)
                raise AssertionError("unexpected Consul request")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                if should_accept:
                    self.assertIsNone(await authority.write_control(
                        lease, "probe", {"value": 17}))
                else:
                    with self.assertRaises(CoordinationLost):
                        await authority.write_control(lease, "probe", {"value": 17})
                self.assertEqual(len(state["requests"]), 1)

        target = "isolated/round25/state/probe"
        positive = {"Results": [{"KV": {"Key": target, "ModifyIndex": 42}}]}
        asyncio.run(exercise(positive, True))
        for bad in (
            {}, {"Results": []}, {"Results": None}, {"Results": "wrong"},
            {"Results": [None]},
            {"Results": [{"KV": {"Key": "foreign", "ModifyIndex": 42}}]},
            {"Results": [{"KV": {"Key": target, "ModifyIndex": 0}}]},
            {"Results": [{"KV": {"Key": target, "ModifyIndex": True}}]},
            {"Results": [{"KV": {"Key": target, "ModifyIndex": 42}}],
             "Errors": "invalid"},
            {"Results": [{"KV": {"Key": target, "ModifyIndex": 42}}],
             "Errors": [{"OpIndex": 1, "What": "check-index failed"}]},
        ):
            with self.subTest(bad=repr(bad)):
                asyncio.run(exercise(bad, False))

    def test_control_txn_does_not_return_success_after_lease_loss(self):
        # The Consul transaction might have committed just before the
        # locally observed expiry. Such an unknown/stale write is NOT a new
        # operation permit, and the caller must never retry blindly.
        from unified_system.consul_authority import CoordinationLost

        async def exercise(loss):
            state = {
                "now": 100.0, "held": False, "value": b"",
                "modify": 41, "kv_reads": 0, "txns": 0,
            }
            key = "isolated/round25/leader"
            target = "isolated/round25/state/probe"
            def clock():
                return state["now"]

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/" + key:
                    if req.method == "PUT":
                        state["held"] = True
                        state["value"] = req.content
                        return httpx.Response(200, json=True)
                    state["kv_reads"] += 1
                    return httpx.Response(200, json=[{
                        "Key": key, "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": state["modify"],
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/txn":
                    self.assertEqual(len(json.loads(req.content)), 3)
                    state["txns"] += 1
                    if loss == "deadline":
                        state["now"] = 115.0
                    elif loss == "session":
                        state["held"] = False
                    elif loss == "modify-index":
                        state["modify"] += 1
                    return httpx.Response(200, json={
                        "Results": [{"KV": {"Key": target, "ModifyIndex": 42}}],
                    })
                raise AssertionError("unexpected Consul path")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client, clock=clock)
            async with client:
                lease = await authority.acquire("owner")
                if loss:
                    with self.assertRaises(CoordinationLost):
                        await authority.write_control(
                            lease, "probe", {"value": 17})
                else:
                    self.assertIsNone(await authority.write_control(
                        lease, "probe", {"value": 17}))
                # Exactly one (potentially completed) write transaction;
                # there is no retry even if the reply proves stale authority.
                self.assertEqual(state["txns"], 1)
                self.assertEqual(state["kv_reads"], 3 if loss != "deadline"
                                 else 2)
                if loss:
                    self.assertFalse(await authority.validate(lease))

        for loss in (None, "deadline", "session", "modify-index"):
            with self.subTest(loss=loss):
                asyncio.run(exercise(loss))

    def test_mutating_consul_requests_never_retry_ambiguous_failover(self):
        # First leader may commit, then lose the reply. A second PUT against
        # another Consul endpoint would be a duplicate unknown mutation.
        async def exercise(method, failure):
            seen = []

            def handler(req):
                seen.append((req.method, req.url.host, req.url.path))
                if req.url.host == "first.example":
                    if failure == "timeout":
                        raise httpx.ReadTimeout("possibly committed; no reply")
                    return httpx.Response(503, json={"error": "unknown"})
                return httpx.Response(200, json={"second": True})

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://first.example:8500", "http://second.example:8500"),
                "isolated/round25", isolated_lab=True,
            ), client=client)
            async with client:
                if method == "GET":
                    result = await authority._request(
                        "GET", "/v1/kv/isolated/round25/leader")
                    self.assertEqual(result, {"second": True})
                    self.assertEqual(len(seen), 2)
                    self.assertEqual(seen[1][1], "second.example")
                else:
                    with self.assertRaises(CoordinationUnavailable):
                        await authority._request(method, "/v1/session/create")
                    self.assertEqual(seen, [
                        (method, "first.example", "/v1/session/create")])

        for failure in ("timeout", "server_error"):
            for method in ("PUT", "POST", "DELETE", "GET"):
                with self.subTest(failure=failure, method=method):
                    asyncio.run(exercise(method, failure))

    def test_failed_acquire_unknown_destroy_does_not_auto_replay(self):
        # If KV acquire returns false, unacquired session cleanup MUST NOT
        # execute destroy twice when the first destroy reply is lost.
        async def exercise(destroy_reply):
            state = {"create": 0, "acquire": 0, "destroy": 0}

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    state["create"] += 1
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/isolated/round25/leader":
                    self.assertEqual(req.method, "PUT")
                    self.assertEqual(req.url.params.get("acquire"), OBSERVED)
                    state["acquire"] += 1
                    return httpx.Response(200, json=False)
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy"] += 1
                    if destroy_reply == "timeout":
                        raise httpx.ReadTimeout("destroy may have committed")
                    return httpx.Response(
                        200, json=(destroy_reply == "confirmed"))
                raise AssertionError("unexpected Consul path")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                if destroy_reply == "confirmed":
                    self.assertIsNone(await authority.acquire("owner"))
                else:
                    with self.assertRaises(CoordinationUnavailable):
                        await authority.acquire("owner")
                self.assertEqual(state, {
                    "create": 1, "acquire": 1, "destroy": 1})
                self.assertEqual(authority._sessions, {})
                self.assertEqual(authority._deadlines, {})

        for reply in ("confirmed", "false", "timeout"):
            with self.subTest(reply=reply):
                asyncio.run(exercise(reply))

    def test_unknown_control_txn_poison_blocks_further_writes(self):
        # Original single Consul authority, MockTransport only. A network
        # timeout may hide COMMIT; no second mutation under that lease.
        async def exercise(outcome):
            state = {
                "held": False, "value": b"", "index": 41,
                "calls": 0, "destroy": 0, "reads": 0,
            }
            leader = "/v1/kv/isolated/round25/leader"
            target = "isolated/round25/state/probe"

            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == leader:
                    if req.method == "PUT":
                        state["held"] = True
                        state["value"] = req.content
                        return httpx.Response(200, json=True)
                    state["reads"] += 1
                    return httpx.Response(200, json=[{
                        "Key": "isolated/round25/leader",
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": state["index"],
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/txn":
                    state["calls"] += 1
                    self.assertEqual(len(json.loads(req.content)), 3)
                    if outcome == "timeout":
                        raise httpx.ReadTimeout("possibly committed before reply")
                    if outcome == "500":
                        return httpx.Response(503, json={"error": "unknown"})
                    if outcome == "409":
                        return httpx.Response(409, json={"Errors": []})
                    if outcome == "false-reply":
                        return httpx.Response(200, json={"Results": []})
                    if outcome == "lost-session":
                        state["held"] = False
                    if outcome == "new-modify-index":
                        state["index"] += 1
                    return httpx.Response(200, json={
                        "Results": [{"KV": {"Key": target, "ModifyIndex": 43}}],
                    })
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy"] += 1
                    return httpx.Response(200, json=True)
                raise AssertionError("unexpected Consul request")

            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                with self.assertRaises(CoordinationUnavailable):
                    await authority.write_control(lease, "probe", {"k": 1})
                self.assertEqual(authority._deadlines[OBSERVED], 0)
                self.assertIs(authority._sessions[OBSERVED], lease)
                before = state["calls"]
                before_reads = state["reads"]
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                with self.assertRaises(CoordinationUnavailable):
                    await authority.write_control(lease, "probe", {"k": 2})
                self.assertEqual(state["calls"], before)
                self.assertEqual(state["reads"], before_reads)
                self.assertEqual(state["destroy"], 0)

        for outcome in ("timeout", "500", "409", "false-reply",
                        "lost-session", "new-modify-index"):
            with self.subTest(outcome=outcome):
                asyncio.run(exercise(outcome))

    def test_mutation_uses_full_deadline_read_failover_divides_budget(self):
        # Mutations are single-attempt; shortening their timeout by the
        # number of configured backup endpoints causes false UNKNOWN results.
        async def exercise(method):
            calls = []
            def handler(req):
                calls.append((req.url.host, req.extensions["timeout"]["read"]))
                if req.url.host == "first.example":
                    raise httpx.ReadTimeout("first leader outcome unknown")
                return httpx.Response(200, json={"second": True})
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://first.example:8500", "http://second.example:8500"),
                "isolated/round25", isolated_lab=True,
                request_timeout=2.0,
            ), client=client)
            async with client:
                if method == "GET":
                    self.assertEqual(
                        await authority._request("GET", "/v1/kv/test"),
                        {"second": True})
                    self.assertEqual(calls, [
                        ("first.example", 1.0), ("second.example", 1.0)])
                else:
                    with self.assertRaises(CoordinationUnavailable):
                        await authority._request("PUT", "/v1/session/create")
                    self.assertEqual(calls, [("first.example", 2.0)])
        for method in ("GET", "PUT"):
            with self.subTest(method=method):
                asyncio.run(exercise(method))

    def test_cancelled_consul_renew_invalidates_original_lease(self):
        # Cancellation may occur after the server has applied a renewal but
        # before Root sees an ACK. Never preserve the old local deadline.
        async def exercise():
            state = {"held": False, "value": b"", "renew": 0}
            leader = "/v1/kv/isolated/round25/leader"
            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == leader:
                    if req.method == "PUT":
                        state["held"], state["value"] = True, req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": "isolated/round25/leader",
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/session/renew/" + OBSERVED:
                    state["renew"] += 1
                    raise asyncio.CancelledError()
                raise AssertionError("unexpected Consul request")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                with self.assertRaises(asyncio.CancelledError):
                    await authority.renew(lease)
                self.assertEqual(state["renew"], 1)
                self.assertIs(authority._sessions[OBSERVED], lease)
                self.assertEqual(authority._deadlines[OBSERVED], 0)
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                self.assertEqual(state["renew"], 1)
        asyncio.run(exercise())

    def test_cancelled_consul_txn_or_post_read_prevents_replay(self):
        # A canceled task does not prove rollback of the original mutation.
        async def exercise(cancel_step):
            state = {"held": False, "value": b"", "txns": 0, "reads": 0}
            leader = "/v1/kv/isolated/round25/leader"
            target = "isolated/round25/state/probe"
            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == leader:
                    if req.method == "PUT":
                        state["held"], state["value"] = True, req.content
                        return httpx.Response(200, json=True)
                    state["reads"] += 1
                    # First read belongs to acquire, second to initial
                    # validate, third is a post-txn consistency check.
                    if cancel_step == "post-read" and state["reads"] == 3:
                        raise asyncio.CancelledError()
                    return httpx.Response(200, json=[{
                        "Key": "isolated/round25/leader",
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/txn":
                    state["txns"] += 1
                    if cancel_step == "txn":
                        raise asyncio.CancelledError()
                    return httpx.Response(200, json={
                        "Results": [{"KV": {"Key": target, "ModifyIndex": 42}}],
                    })
                raise AssertionError("unexpected Consul request")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                with self.assertRaises(asyncio.CancelledError):
                    await authority.write_control(lease, "probe", {"n": 1})
                self.assertEqual(state["txns"], 1)
                self.assertIs(authority._sessions[OBSERVED], lease)
                self.assertEqual(authority._deadlines[OBSERVED], 0)
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                with self.assertRaises(CoordinationUnavailable):
                    await authority.write_control(lease, "probe", {"n": 2})
                self.assertEqual(state["txns"], 1)
        for cancel_step in ("txn", "post-read"):
            with self.subTest(cancel_step=cancel_step):
                asyncio.run(exercise(cancel_step))

    def test_close_revokes_local_lease_without_remote_destroy(self):
        # Shutdown cannot leave a trusted locally issued lease active, even
        # when the caller owns an injected isolated HTTP client.
        async def exercise():
            state = {"held": False, "value": b"", "txn": 0, "destroy": 0}
            key = "/v1/kv/isolated/round25/leader"
            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == key:
                    if req.method == "PUT":
                        state["held"], state["value"] = True, req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": "isolated/round25/leader",
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/txn":
                    state["txn"] += 1
                    return httpx.Response(200, json={"Results": []})
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy"] += 1
                    return httpx.Response(200, json=True)
                raise AssertionError("unexpected Consul path")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                self.assertTrue(await authority.validate(lease))
                await authority.close()
                await authority.close()  # shutdown is idempotent
                self.assertEqual(authority._deadlines[OBSERVED], 0)
                self.assertIs(authority._sessions[OBSERVED], lease)
                self.assertFalse(await authority.validate(lease))
                self.assertFalse(await authority.renew(lease))
                with self.assertRaises(CoordinationUnavailable):
                    await authority.write_control(lease, "probe", {"n": 1})
                with self.assertRaises(CoordinationUnavailable):
                    await authority.acquire("new-owner")
                self.assertEqual((state["txn"], state["destroy"]), (0, 0))
        asyncio.run(exercise())

    def test_close_while_acquiring_cannot_mint_late_lease(self):
        # A concurrent shutdown while the original KV acquire is in flight
        # must not deliver a locally trusted capability after close() returns.
        async def exercise():
            entered, release = asyncio.Event(), asyncio.Event()
            state = {"held": False, "value": b"", "destroy": 0}
            key = "/v1/kv/isolated/round25/leader"
            async def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == key:
                    if req.method == "PUT":
                        entered.set()
                        await release.wait()
                        state["held"], state["value"] = True, req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": "isolated/round25/leader",
                        "Session": OBSERVED if state["held"] else "",
                        "ModifyIndex": 41,
                        "Value": base64.b64encode(state["value"]).decode(),
                    }])
                if path == "/v1/session/destroy/" + OBSERVED:
                    state["destroy"] += 1
                    state["held"] = False
                    return httpx.Response(200, json=True)
                raise AssertionError("unexpected Consul path")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                pending = asyncio.create_task(authority.acquire("owner"))
                await asyncio.wait_for(entered.wait(), 1)
                await authority.close()
                release.set()
                with self.assertRaises(CoordinationUnavailable):
                    await asyncio.wait_for(pending, 1)
                self.assertEqual(authority._sessions, {})
                self.assertEqual(authority._deadlines, {})
                self.assertEqual(state["destroy"], 1)
                self.assertFalse(state["held"])
        asyncio.run(exercise())

    def test_control_read_rejects_forged_kv_metadata_and_shape(self):
        # This is historical state data, not lease/Root authority. Consul
        # must not silently return a scalar or a row for a foreign key.
        async def exercise(case):
            state_key = "isolated/round25/state/probe"
            original = {
                "owner": "owner", "token": 41, "session_id": OBSERVED,
                "payload": {"value": 17},
            }
            row = {
                "Key": state_key, "ModifyIndex": 42,
                "Value": base64.b64encode(json.dumps(original).encode()).decode(),
            }
            if case == "foreign-key":
                row["Key"] = "isolated/foreign/state/probe"
            elif case == "missing-index":
                row.pop("ModifyIndex")
            elif case == "boolean-index":
                row["ModifyIndex"] = True
            elif case == "missing-owner":
                row["Value"] = base64.b64encode(b'{"payload":17}').decode()
            elif case == "scalar":
                row["Value"] = base64.b64encode(b'17').decode()
            elif case == "non-finite":
                row["Value"] = base64.b64encode(
                    b'{"owner":"owner","token":41,'
                    b'"session_id":"' + OBSERVED.encode() +
                    b'","payload":NaN}').decode()
            elif case == "oversized":
                row["Value"] = base64.b64encode(
                    b' ' * 32769 + json.dumps(original).encode()).decode()
            rows = {"unexpected": "mapping"} if case == "mapping" else [row]
            def handler(req):
                self.assertEqual(req.method, "GET")
                self.assertEqual(req.url.path, "/v1/kv/" + state_key)
                self.assertIn("consistent", req.url.params)
                return httpx.Response(200, json=rows)
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                if case == "valid":
                    self.assertEqual(await authority.read_control("probe"), original)
                else:
                    with self.assertRaises(CoordinationUnavailable):
                        await authority.read_control("probe")
        for case in ("valid", "foreign-key", "missing-index",
                     "boolean-index", "missing-owner", "scalar",
                     "non-finite", "oversized", "mapping"):
            with self.subTest(case=case):
                asyncio.run(exercise(case))

    def test_control_read_closed_during_consistent_get_denies_late_reply(self):
        # A consistent read started before shutdown must not return a stale
        # state record after the authority has closed and revoked all leases.
        async def exercise():
            entered, released = asyncio.Event(), asyncio.Event()
            record = {
                "owner": "owner", "token": 41, "session_id": OBSERVED,
                "payload": {"value": 17},
            }
            key = "isolated/round25/state/probe"
            row = {
                "Key": key, "ModifyIndex": 42,
                "Value": base64.b64encode(json.dumps(record).encode()).decode(),
            }
            async def handler(req):
                self.assertEqual(req.method, "GET")
                self.assertEqual(req.url.path, "/v1/kv/" + key)
                self.assertIn("consistent", req.url.params)
                entered.set()
                await released.wait()
                return httpx.Response(200, json=[row])
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                pending = asyncio.create_task(authority.read_control("probe"))
                await asyncio.wait_for(entered.wait(), timeout=1)
                await authority.close()
                released.set()
                with self.assertRaises(CoordinationUnavailable):
                    await asyncio.wait_for(pending, timeout=1)
        asyncio.run(exercise())

    def test_original_write_control_read_control_roundtrip(self):
        # The existing writer and reader must share one control data shape,
        # preserving exact string decimals without a second implementation.
        async def exercise():
            leader = "isolated/round25/leader"
            control = "isolated/round25/state/probe"
            state = {"leader": None, "payload": None, "writes": 0}
            def handler(req):
                path = req.url.path
                if path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": OBSERVED})
                if path == "/v1/kv/" + leader:
                    if req.method == "PUT":
                        state["leader"] = req.content
                        return httpx.Response(200, json=True)
                    return httpx.Response(200, json=[{
                        "Key": leader, "ModifyIndex": 41, "Session": OBSERVED,
                        "Value": base64.b64encode(state["leader"]).decode(),
                    }])
                if path == "/v1/txn":
                    operations = json.loads(req.content)
                    self.assertEqual(
                        [row["KV"]["Verb"] for row in operations],
                        ["check-session", "check-index", "set"])
                    self.assertEqual(operations[2]["KV"]["Key"], control)
                    state["payload"] = operations[2]["KV"]["Value"]
                    state["writes"] += 1
                    return httpx.Response(200, json={
                        "Results": [{"KV": {"Key": control, "ModifyIndex": 42}}],
                    })
                if path == "/v1/kv/" + control:
                    self.assertIn("consistent", req.url.params)
                    return httpx.Response(200, json=[{
                        "Key": control, "ModifyIndex": 42,
                        "Value": state["payload"],
                    }])
                raise AssertionError("unexpected Consul path")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                lease = await authority.acquire("owner")
                payload = {"volume": "0.10000000000000001"}
                self.assertIsNone(await authority.write_control(
                    lease, "probe", payload))
                self.assertEqual(await authority.read_control("probe"), {
                    "owner": "owner", "token": lease.token,
                    "session_id": OBSERVED, "payload": payload,
                })
                self.assertEqual(state["writes"], 1)
        asyncio.run(exercise())

    def test_consul_control_404_after_close_is_not_valid_absence(self):
        # During a consistent GET, shutdown may precede a 404 reply. An
        # already-closed Root authority must refuse even the missing record.
        async def exercise():
            entered = asyncio.Event()
            released = asyncio.Event()
            async def handler(req):
                self.assertEqual(req.method, "GET")
                self.assertEqual(req.url.path, "/v1/kv/isolated/round25/state/probe")
                self.assertIn("consistent", req.url.params)
                entered.set()
                await released.wait()
                return httpx.Response(404)
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                pending = asyncio.create_task(authority.read_control("probe"))
                await asyncio.wait_for(entered.wait(), 1)
                await authority.close()
                released.set()
                with self.assertRaises(CoordinationUnavailable):
                    await asyncio.wait_for(pending, 1)
                self.assertFalse(await authority.validate(
                    ConsulLease("owner", OBSERVED, 41)))
        asyncio.run(exercise())

    def test_control_read_rejects_duplicate_json_members_at_any_depth(self):
        # Canonical writer emits unique keys. Python's ordinary json.loads
        # accepts ambiguous duplicate members and silently takes the last
        # value; Consul historical readback must instead fail closed.
        async def exercise(raw):
            state_key = "isolated/round25/state/probe"
            row = {
                "Key": state_key, "ModifyIndex": 42,
                "Value": base64.b64encode(raw).decode(),
            }
            def handler(req):
                self.assertEqual(req.method, "GET")
                self.assertEqual(req.url.path, "/v1/kv/" + state_key)
                self.assertIn("consistent", req.url.params)
                return httpx.Response(200, json=[row])
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25",
                isolated_lab=True,
            ), client=client)
            async with client:
                with self.assertRaises(CoordinationUnavailable):
                    await authority.read_control("probe")
        prefix = (b'{"owner":"owner","token":41,'
                  b'"session_id":"' + OBSERVED.encode() + b'",')
        originals = (
            b'{"owner":"owner","owner":"attacker","token":41,'
            b'"session_id":"' + OBSERVED.encode() + b'","payload":{}}',
            prefix + b'"payload":{"value":"1","value":"999"}}',
            prefix + b'"payload":{"nested":{"x":1,"x":2}}}',
        )
        for raw in originals:
            with self.subTest(raw=raw):
                asyncio.run(exercise(raw))

    def test_malformed_server_session_never_calls_kv_acquire(self):
        async def scenario(bad):
            seen = []
            def handler(req):
                seen.append(req.url.path)
                if req.url.path == "/v1/session/create":
                    return httpx.Response(200, json={"ID": bad})
                raise AssertionError("invalid session must not access KV")
            client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            authority = ConsulSessionAuthority(ConsulConfig(
                ("http://127.0.0.1:8500",), "isolated/round25", isolated_lab=True,
            ), client=client)
            async with client:
                with self.assertRaises(CoordinationUnavailable):
                    await authority.acquire("owner")
            self.assertEqual(seen, ["/v1/session/create"])
        for bad in (None, True, "", "../../escape", "with/slash", "%2f",
                    "with space", "\n", "a" * 129, "é"):
            with self.subTest(value=repr(bad)):
                asyncio.run(scenario(bad))


if __name__ == "__main__":
    unittest.main()
