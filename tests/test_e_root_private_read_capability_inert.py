"""Protected Root-generated Terminan read capability — inert negative suite.

No subprocess is started; fake process witnesses are *not* Windows/PID
attestation, PostgreSQL custody, live lease proof or an E2E certificate.
"""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from unified_system.runtime import ModuleSpec
from unified_system.runtime_process import (
    PRIVATE_DATA_CAPABILITY_ENV, ProcessDriver, _public_environment,
)


SOURCE = "f57781a947af138a2099bebe553b89c3c5ee726e"
TOKEN = "a" * 64
EPOCH = "b" * 32
RELEASE = "lab-release-1"


def source_driver():
    driver = object.__new__(ProcessDriver)
    driver.children = {EPOCH: object()}
    driver.programs = {
        "market_data": {"health_url":"http://127.0.0.1:8766/health",
                        "env":{"UNIFIED_SOURCE_COMMIT": SOURCE}},
    }
    driver._load = lambda _: {
        "module_id":"market_data","version":"0.2.0.dev0",
        "release_id": RELEASE,"state":"RUNNING","created":["fake-only"],
        "token":TOKEN,"source_commit":SOURCE,
    }
    driver.alive = lambda _: True
    driver.ready = lambda spec,handle,release: {
        "ready":True,"module_id":"market_data",
        "version":spec.version,"release_id":release,
    }
    return driver


class RootPrivateReadCapabilityTests(unittest.TestCase):
    def test_exact_private_capability_from_single_owned_source(self):
        d=source_driver()
        cap=d._market_data_read_capability(RELEASE)
        self.assertEqual(cap, {"port":8766,"token":TOKEN,
                               "source_commit":SOURCE,"release_id":RELEASE,
                               "epoch":EPOCH})
        self.assertEqual(set(cap), {"port","token","source_commit",
                                    "release_id","epoch"})

    def test_two_live_market_data_children_never_mint_capability(self):
        d=source_driver()
        d.children["c"*32]=object()
        with self.assertRaises(ValueError):
            d._market_data_read_capability(RELEASE)

    def test_missing_or_stopped_source_never_mints_capability(self):
        d=source_driver()
        d.alive=lambda _:False
        with self.assertRaises(ValueError):
            d._market_data_read_capability(RELEASE)
        d.children={}
        with self.assertRaises(ValueError):
            d._market_data_read_capability(RELEASE)

    def test_wrong_release_source_commit_or_current_ready_refused(self):
        for change in ("release","commit","unready","wrong-source"):
            d=source_driver()
            if change=="release":
                d._load=lambda _:dict(source_driver()._load(EPOCH),
                                       release_id="different")
            elif change=="commit":
                d.programs["market_data"]["env"]["UNIFIED_SOURCE_COMMIT"]="0"*40
            elif change=="wrong-source":
                d._load=lambda _:dict(source_driver()._load(EPOCH),
                                       source_commit="0"*40)
            else:
                d.ready=lambda *args:{"ready":False}
            with self.subTest(change=change),self.assertRaises(ValueError):
                d._market_data_read_capability(RELEASE)

    def test_invalid_process_token_or_endpoint_refused(self):
        d=source_driver()
        d._load=lambda _:dict(source_driver()._load(EPOCH),token="not-a-token")
        with self.assertRaises(ValueError):
            d._market_data_read_capability(RELEASE)
        d=source_driver()
        d.programs["market_data"]["health_url"]="http://0.0.0.0:8766/health"
        with self.assertRaises(ValueError):
            d._market_data_read_capability(RELEASE)

    def test_private_environment_config_is_rejected_case_insensitively(self):
        for key in (PRIVATE_DATA_CAPABILITY_ENV,
                    PRIVATE_DATA_CAPABILITY_ENV.lower(),
                    "PGPASSWORD","PgPassFile"):
            with self.subTest(key=key),self.assertRaises(ValueError):
                _public_environment({"env":{key:"user-supplied-token"}})

    def test_restart_has_new_source_epoch_and_old_identity_not_reused(self):
        d=source_driver()
        prior=d._market_data_read_capability(RELEASE)
        d.children={"c"*32:object()}
        d._load=lambda _:dict(source_driver()._load(EPOCH),token="d"*64)
        current=d._market_data_read_capability(RELEASE)
        self.assertNotEqual(prior["epoch"],current["epoch"])
        self.assertNotEqual(prior["token"],current["token"])
        self.assertEqual(current["source_commit"],SOURCE)

    def test_terminan_receives_only_owner_minted_private_capability(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            driver=object.__new__(ProcessDriver)
            driver.root=root
            driver.children={}
            driver.prestart_rejections={}
            driver.authorize=lambda action,module:action=="start" and module=="terminan"
            driver.child_environment=lambda _:{
                PRIVATE_DATA_CAPABILITY_ENV:"attacker-injected",
                "PGPASSWORD":"attacker-secret",
                "EXTRA_PUBLIC":"fixture",
            }
            driver.programs={
                "terminan":{
                    "argv":["/inert/python","-I","-B","/inert/terminan"],
                    "cwd":str(root),"env":{"UNIFIED_SOURCE_COMMIT":SOURCE},
                },
            }
            driver._file=lambda _:root/"absent-start-record"
            driver._verify=lambda _:None
            saves=[]
            driver._save=lambda _,data,**kwargs:saves.append(copy.deepcopy(data))
            driver._market_data_read_capability=lambda _:source_driver()._market_data_read_capability(RELEASE)
            capture=[]
            def fake_popen(*args,**kwargs):
                capture.append(kwargs)
                return SimpleNamespace(pid=12345)
            with patch.dict(os.environ,{PRIVATE_DATA_CAPABILITY_ENV:"ambient-injected"}),patch(
                    "unified_system.runtime_process.subprocess.Popen",
                    side_effect=fake_popen),patch(
                    "unified_system.runtime_process._identity",
                    return_value=["synthetic-fake-process"]):
                result=driver.start(ModuleSpec("terminan","0.2.0"),RELEASE,"e"*32)
            self.assertEqual(result,"e"*32)
            self.assertEqual(len(capture),1)
            env=capture[0]["env"]
            minted=json.loads(env[PRIVATE_DATA_CAPABILITY_ENV])
            self.assertEqual(minted,source_driver()._market_data_read_capability(RELEASE))
            self.assertNotEqual(env[PRIVATE_DATA_CAPABILITY_ENV],"attacker-injected")
            self.assertNotIn("PGPASSWORD",env)
            self.assertEqual(env["UNIFIED_MODULE_ID"],"terminan")
            self.assertEqual(env["UNIFIED_RELEASE_ID"],RELEASE)
            self.assertNotIn(TOKEN,json.dumps(saves))
            self.assertEqual(saves[-1]["market_data_epoch"],EPOCH)
            self.assertIsNotNone(capture[0]["stdin"])
            self.assertEqual(len(driver.children),1)

    def test_invalid_source_denies_terminan_before_any_child_start(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            d=object.__new__(ProcessDriver)
            d.root=root
            d.children={}
            d.prestart_rejections={}
            d.authorize=lambda *_:True
            d.programs={"terminan":{}}
            d._verify=lambda _:None
            d._file=lambda _:root/"no-intent"
            d._market_data_read_capability=lambda _:(_ for _ in ()).throw(
                ValueError("source-revoked"))
            with patch("unified_system.runtime_process.subprocess.Popen") as popen:
                with self.assertRaises(ValueError):
                    d.start(ModuleSpec("terminan","0.2.0"),RELEASE,"f"*32)
                popen.assert_not_called()
            self.assertFalse((root/"no-intent").exists())

if __name__ == "__main__":
    unittest.main()
