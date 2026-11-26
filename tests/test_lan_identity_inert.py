"""Pure six-node identity/ALPN/registry refusal; no TLS, I/O or services."""
import hashlib
import threading
import unittest
import uuid
from unified_system.lan_transport import (PeerRegistry, LanTransport,
    TransportError, LEGACY_PROTOCOL, MUX_PROTOCOL)

NODES = ("LS5", "PC1", "PC2", "PC3", "PC4", "LS7")


def registry_document():
    cluster = str(uuid.uuid4())
    certs = {node: ("peer-cert-" + node).encode("ascii") for node in NODES}
    rows = []
    for index, node in enumerate(NODES):
        rows.append({"node_id": node, "enrollment_id": str(uuid.uuid4()),
                     "fingerprints": [hashlib.sha256(certs[node]).hexdigest()],
                     "roles": ["control", "ingestion", "storage"],
                     "endpoints": [{"address": "127.0.0.1",
                                    "port": 10000 + index, "priority": 0,
                                    "transport": "lan"}], "enabled": True})
    return {"schema": "unified.lan-peer-registry.v1", "cluster_id": cluster,
            "generation": 1, "nodes": rows}, certs


class FakeTLS:
    def __init__(self, der, cluster, node, protocol=LEGACY_PROTOCOL):
        self.der, self.cluster, self.node, self.protocol = der, cluster, node, protocol
    def selected_alpn_protocol(self): return self.protocol
    def getpeercert(self, binary_form=False):
        if binary_form: return self.der
        return {"subjectAltName": [("URI", "urn:unified:" + self.cluster + ":" + self.node)]}


class IdentityRefusalTests(unittest.TestCase):
    def setUp(self):
        self.document, self.certs = registry_document()
        self.registry = PeerRegistry.from_document(self.document)
        self.tls = FakeTLS(self.certs["PC1"], self.document["cluster_id"], "PC1")

    def test_admitted_exact_identity(self):
        self.assertEqual(self.registry.authenticate(self.tls, "PC1"), "PC1")

    def test_wrong_expected_node_fails(self):
        with self.assertRaisesRegex(TransportError, "AUTH_REJECTED"):
            self.registry.authenticate(self.tls, "PC2")

    def test_wrong_peer_uri_or_cluster_fails(self):
        for node, cluster in (("PC2", self.document["cluster_id"]),
                              ("PC1", str(uuid.uuid4()))):
            with self.subTest(node=node, cluster=cluster):
                tls = FakeTLS(self.certs["PC1"], cluster, node)
                with self.assertRaisesRegex(TransportError, "AUTH_REJECTED"):
                    self.registry.authenticate(tls)

    def test_wrong_fingerprint_fails(self):
        tls = FakeTLS(b"another-cert", self.document["cluster_id"], "PC1")
        with self.assertRaisesRegex(TransportError, "AUTH_REJECTED"):
            self.registry.authenticate(tls, "PC1")

    def test_missing_or_mismatched_alpn_fails(self):
        for protocol in (None, "", MUX_PROTOCOL):
            with self.subTest(protocol=protocol):
                tls = FakeTLS(self.certs["PC1"], self.document["cluster_id"], "PC1", protocol)
                with self.assertRaisesRegex(TransportError, "AUTH_REJECTED"):
                    self.registry.authenticate(tls, "PC1")

    def test_disabled_peer_cannot_authenticate(self):
        self.document["nodes"][1]["enabled"] = False
        registry = PeerRegistry.from_document(self.document)
        with self.assertRaisesRegex(TransportError, "AUTH_REJECTED"):
            registry.authenticate(self.tls, "PC1")

    def test_duplicate_fingerprint_is_registry_failure(self):
        self.document["nodes"][2]["fingerprints"] = list(self.document["nodes"][1]["fingerprints"])
        with self.assertRaisesRegex(TransportError, "REGISTRY_REJECTED"):
            PeerRegistry.from_document(self.document)

    def test_revoked_pin_closes_existing_connection(self):
        transport = object.__new__(LanTransport)
        transport.registry = self.registry
        transport.node_id = "LS5"
        transport.lock = threading.RLock()
        seen = []
        transport.connections = {"PC1": type("ConnectionWitness", (),
            {"close": lambda unused, reason: seen.append(reason)})()}
        self.document["generation"] = 2
        self.document["nodes"][1]["fingerprints"] = ["f" * 64]
        LanTransport.update_registry(transport, PeerRegistry.from_document(self.document))
        self.assertEqual(seen, ["POLICY_REVOKED"])

    def test_old_or_equal_generation_cannot_replace_registry(self):
        transport = object.__new__(LanTransport)
        transport.registry = self.registry
        transport.node_id = "LS5"
        transport.lock = threading.RLock()
        transport.connections = {}
        with self.assertRaisesRegex(TransportError, "REGISTRY_ROLLBACK"):
            LanTransport.update_registry(transport, PeerRegistry.from_document(self.document))


if __name__ == "__main__":
    unittest.main()
