"""J Round35: fail-closed synthetic PostgreSQL18 and Consul acceptance.

No user database, trading, service installation, deletion, or release authority.
Actual native tests MUST fail (not skip) in CI if the disposable fixtures are absent.
"""
import json
import os
from pathlib import Path
import subprocess
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "integration" / "round34" / "checkpoint_sql_reconstruction.v1.json"
PINS = ROOT / "integration" / "round35" / "owner_pins.v1.json"
A = "a" * 64
B = "b" * 64
STREAM = "bybit:BTCUSDT:1m"
PG_NAME = "j_round35_disposable"
PG_CONTAINER = os.environ.get("J_R35_PG_CONTAINER", "")
CONSUL_ADDR = os.environ.get("J_R35_CONSUL_ADDR", "")
NATIVE = os.environ.get("J_R35_DISPOSABLE_ONLY") == "1"
SCHEMA = """
CREATE TABLE public.lab_writer_fence
 (resource_id text, backend_pid int, owner text, namespace text,
 generation bigint, token bigint, source_sha256 text, schema_sha256 text);
CREATE TABLE public.lab_stream_checkpoint
 (stream_id text, symbol text, cursor_value bigint, source_start_ms bigint,
 fingerprint text, content_id text, owner text, namespace text,
 generation bigint, token bigint);
CREATE TABLE public.provenance_minutes
 (symbol text, start_ms bigint, fingerprint text, content_id text, record jsonb);
CREATE TABLE public.lab_stream_pending
 (stream_id text, symbol text, start_ms bigint, fingerprint text,
 content_id text, owner text, namespace text, source_sha256 text,
 schema_sha256 text, generation bigint, token bigint);
"""
FENCE = ("INSERT INTO public.lab_writer_fence VALUES "
         "('lab',pg_backend_pid(),'owner','namespace',1,7,'src','schema');")
CHECKPOINT = (
    "INSERT INTO public.lab_stream_checkpoint VALUES "
    f"('{STREAM}','BTCUSDT',300000,300000,'{A}','{B}',"
    "'owner','namespace',1,7);"
)
PROVENANCE = (
    "INSERT INTO public.provenance_minutes VALUES "
    f"('BTCUSDT',300000,'{A}','{B}',"
    f"'{{\"dataset_fingerprint\":\"{A}\"}}'::jsonb);"
)
PENDING = (
    "INSERT INTO public.lab_stream_pending VALUES "
    f"('{STREAM}','BTCUSDT',300000,'{A}','{B}',"
    "'owner','namespace','src','schema',1,7);"
)


def original_candidates():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    if payload["scope"] != "DISPOSABLE_LAB_ONLY_DO_NOT_EXECUTE_ON_USER_DATABASE":
        raise AssertionError("original SQL source provenance mismatch")
    by_label = {item["label"]: item for item in payload["candidates"]}
    if set(by_label) != {"cad4", "076"}:
        raise AssertionError("unexpected SQL candidate roster")
    return by_label


def pg_run(sql):
    if not NATIVE or not PG_CONTAINER.startswith("j-r35-pg-"):
        raise RuntimeError("J_R35_DISPOSABLE_PG_REQUIRED")
    proc = subprocess.run(
        ["docker", "exec", "-i", PG_CONTAINER, "psql", "-X",
         "-v", "ON_ERROR_STOP=1", "-U", "jlab", "-d", PG_NAME, "-At"],
        input=sql, text=True, capture_output=True, timeout=25, check=False)
    return proc


def consul_request(path, method="GET", token=None, body=None):
    if not NATIVE or CONSUL_ADDR != "http://127.0.0.1:18500":
        raise RuntimeError("J_R35_LOCAL_CONSUL_REQUIRED")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Consul-Token"] = token
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(CONSUL_ADDR + path, method=method, data=data, headers=headers)
    try:
        with urlopen(req, timeout=8) as res:
            return res.status, res.read()
    except HTTPError as exc:
        return exc.code, exc.read()


class StaticContract(unittest.TestCase):
    def test_exact_sql_source_is_unqualified(self):
        c = original_candidates()
        self.assertEqual(c["cad4"]["git_blob_sha"],
                         "cad4ccf970470eb86a487c484cee9be15ea9614d")
        self.assertEqual(c["076"]["git_blob_sha"],
                         "076980d9556bf3a685091f16129ef321cb1372be")
        self.assertEqual(c["cad4"]["lexical_parenthesis_balance"], 1)
        self.assertEqual(c["076"]["lexical_parenthesis_balance"], 0)
        self.assertTrue(all(x["actual_pg18_execute"] == "NOT_RUN"
                            for x in c.values()))

    def test_owner_pins_never_grant_release(self):
        x = json.loads(PINS.read_text(encoding="utf-8"))
        self.assertEqual(x["schema"], "unified-system.j.round35.disposable.v1")
        self.assertRegex(x["source_j_head"], r"^[a-f0-9]{40}$")
        self.assertNotEqual(x["source_j_head"], x["frozen_pr166_sha"])
        self.assertRegex(x["observation_epoch"], r"^round35-(?:next-cycle|master-[0-9]+)$")
        self.assertEqual(x["frozen_pr166_sha"],
                         "9349d7f3ed93ef82d120976816b968e0b716b067")
        self.assertEqual(x["release"], "CODE_NO_GO_PRODUCTION_NO_GO")
        self.assertFalse(x["authorize_release"])
        self.assertFalse(x["authorize_physical_delete"])
        self.assertFalse(x["authorize_live_trading"])
        for role in ("C", "E", "D", "G", "I", "Math"):
            self.assertRegex(x["sources"][role]["sha"], r"^[a-f0-9]{40}$")


@unittest.skipUnless(NATIVE, "Native disposable environment NOT_RUN")
class NativeDisposable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not PG_CONTAINER.startswith("j-r35-pg-"):
            raise RuntimeError("REFUSE_NON_DISPOSABLE_PG")
        if CONSUL_ADDR != "http://127.0.0.1:18500":
            raise RuntimeError("REFUSE_EXTERNAL_CONSUL")
        p = pg_run("SELECT current_database(),current_setting('server_version_num');")
        if p.returncode or not any(
            line.startswith(PG_NAME + "|18") for line in p.stdout.splitlines()
        ):
            raise RuntimeError("PG18_DISPOSABLE_IDENTITY_OR_VERSION_MISMATCH")

    def pg_case(self, label, insertions, expected):
        sql = ("BEGIN;\n" + SCHEMA + "\n" +
               "\n".join(insertions) + "\n" +
               original_candidates()[label]["generated_sql"] + ";\nROLLBACK;\n")
        result = pg_run(sql)
        self.assertEqual(result.returncode, 0, result.stderr[:500])
        lines = [x.strip() for x in result.stdout.splitlines()]
        self.assertIn(expected, lines)

    def test_pg18_rejects_original_open_cte(self):
        sql = ("BEGIN;\n" + SCHEMA + "\n" +
               original_candidates()["cad4"]["generated_sql"] + ";\nROLLBACK;\n")
        p = pg_run(sql)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("syntax error", p.stderr.lower())

    def test_pg18_denies_missing_active_fence(self):
        self.pg_case("076", [], "DENIED")

    def test_pg18_unresolved_without_checkpoint(self):
        self.pg_case("076", [FENCE], "UNRESOLVED")

    def test_pg18_exact_checkpoint_ack(self):
        self.pg_case("076", [FENCE, CHECKPOINT, PROVENANCE, PENDING],
                     "EXACT_ALREADY_ACKNOWLEDGED")

    def test_pg18_rejects_mismatched_pending_lease(self):
        bad = PENDING.replace("'src','schema',1,7", "'other','schema',1,7")
        self.pg_case("076", [FENCE, CHECKPOINT, PROVENANCE, bad],
                     "UNRESOLVED")

    def test_consul_acl_denies_anonymous_and_renews_session(self):
        status, _ = consul_request("/v1/acl/tokens")
        self.assertEqual(status, 403, "CONSUL_ACL_NOT_FAIL_CLOSED")
        code, raw = consul_request("/v1/acl/bootstrap", method="PUT")
        self.assertEqual(code, 200, "CONSUL_BOOTSTRAP_UNAVAILABLE")
        token = json.loads(raw)["SecretID"]
        self.assertTrue(len(token) >= 30)
        code, raw = consul_request("/v1/session/create", method="PUT",
                                   token=token,
                                   body={"Name": "j-r35-inert", "TTL": "30s",
                                         "Behavior": "release"})
        self.assertEqual(code, 200, raw[:100])
        session = json.loads(raw)["ID"]
        code, raw = consul_request("/v1/session/renew/" + session,
                                   method="PUT", token=token)
        self.assertEqual(code, 200, raw[:100])
        self.assertEqual(json.loads(raw)[0]["ID"], session)


if __name__ == "__main__":
    unittest.main(verbosity=2)
