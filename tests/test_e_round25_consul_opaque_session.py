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
                state["held"] = False
                self.assertFalse(await authority.validate(lease))
                state["held"] = True
                state["session"] = "foreign-session"
                self.assertFalse(await authority.validate(lease))
                # Never claim the altered KV row is a valid old lease.
        asyncio.run(scenario())

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
