"""Synthetic Root/ Grid v2 source and protected-launch invariants.

These tests use inert files only. They are NOT Git provenance, native Windows,
PostgreSQL resource fencing or a running Market Data listener acceptance.
"""
import copy
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest

from tests.test_lab_release import fixture
from unified_system import lab_release, lab_runtime, service_module_runtime
from unified_system.grid_writer_fence_model import ResourceFenceBlocked
from unified_system.market_data_entry_contract import (
    APPROVED_GRID_COMMIT, GRID_REPOSITORY, LEGACY_ENTRY, V2_ENTRY,
    V2_FILES, V2_SOURCE_VERSION, V2_WHEEL_VERSION, MarketDataEntryRejected,
    entry_for_manifest,
)
from unified_system.service_bootstrap import ActivationBlocked


def put(root, manifest, path, data=b"synthetic-only"):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(data)
    manifest["files"][path] = {
        "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
    }


class RootGridV2InertTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.manifest = fixture(self.root)
        self.legacy = copy.deepcopy(self.manifest)
        source = self.manifest["sources"]["market_data"]
        source.update(repository=GRID_REPOSITORY, commit=APPROVED_GRID_COMMIT,
                      version=V2_SOURCE_VERSION)
        for path in V2_FILES:
            put(self.root, self.manifest, path, b"source-fixture-" + path.encode())
        self.lock = "deps/market-data-v2.lock"
        put(self.root, self.manifest, self.lock, b"market-data==0.2.0.dev0\n")
        self.manifest["dependencies"].append(
            {"name": "market-data", "version": V2_WHEEL_VERSION, "lock_path": self.lock}
        )
        put(self.root, self.manifest, "runtime/python.exe", b"inert-python")
        put(self.root, self.manifest,
            "sources/unified_system/unified_system/owned_python.py", b"inert-bootstrap")
        put(self.root, self.manifest,
            "sources/unified_system/unified_system/service_entry.py", b"inert-entry")
        self.manifest["directories"] = sorted({
            p.as_posix() for name in self.manifest["files"]
            for p in Path(name).parents if str(p) != "."
        })
        self.grant = SimpleNamespace(code_root=self.root)
        self.port = 8766
        self.bootstrap = (self.root / "sources/unified_system/unified_system/owned_python.py")

    def program(self, entry=V2_ENTRY):
        argv = [
            str(self.root / "runtime/python.exe"), "-I", "-S", "-B",
            str(self.bootstrap),
            "--source-root", str(self.root / "sources/market_data"),
            "--dependency-root", str(self.root / "dependencies/site-packages"),
            "--module", entry, "--", "serve",
        ]
        return {
            "argv": argv,
            "health_url": f"http://127.0.0.1:{self.port}/health",
            "env": {"MARKET_DATA_PORT": str(self.port)},
        }

    def test_root_module_spec_semver_and_exact_pep440_wheel_split(self):
        from unified_system.runtime import ModuleSpec, _valid
        self.assertIsNone(_valid(ModuleSpec("market_data", V2_SOURCE_VERSION)))
        with self.assertRaises(ValueError):
            _valid(ModuleSpec("market_data", V2_WHEEL_VERSION))
        self.assertEqual(self.manifest["sources"]["market_data"]["version"],
                         V2_SOURCE_VERSION)
        self.assertEqual(next(dep["version"] for dep in self.manifest["dependencies"]
                              if dep["name"] == "market-data"), V2_WHEEL_VERSION)

    def test_explicit_grid_source_selects_only_v2(self):
        self.assertEqual(entry_for_manifest(self.manifest), V2_ENTRY)
        self.assertEqual(entry_for_manifest(self.legacy), LEGACY_ENTRY)
        self.assertEqual(service_module_runtime._entry("market_data",self.manifest), V2_ENTRY)
        self.assertEqual(service_module_runtime._entry("terminan",self.manifest),
                         "terminan.server")

    def test_canonical_capsule_parser_accepts_pinned_lab_candidate_shape(self):
        raw = lab_release.canonical(self.manifest)
        # Manifest syntax + hash, not an externally verified Grid Git checkout.
        self.assertEqual(lab_release.parse_manifest(raw,hashlib.sha256(raw).hexdigest())
                         ["sources"]["market_data"]["repository"], GRID_REPOSITORY)
        old = lab_release.canonical(self.legacy)
        self.assertEqual(lab_release.parse_manifest(old,hashlib.sha256(old).hexdigest())
                         ["sources"]["market_data"]["repository"],
                         "YehorBabenko88/strattester")

    def test_unknown_source_sha_is_not_v2(self):
        changed = copy.deepcopy(self.manifest)
        changed["sources"]["market_data"]["commit"] = "f" * 40
        with self.assertRaisesRegex(MarketDataEntryRejected,"GRID_V2_SOURCE_NOT_ADMITTED"):
            entry_for_manifest(changed)
        with self.assertRaises(ActivationBlocked):
            service_module_runtime._entry("market_data", changed)

    def test_wrong_source_repository_never_becomes_grid_v2(self):
        for repository in ("YehorBabenko88/strattester", "untrusted/market_data", ""):
            changed = copy.deepcopy(self.manifest)
            changed["sources"]["market_data"]["repository"] = repository
            self.assertEqual(entry_for_manifest(changed), LEGACY_ENTRY)
            raw = lab_release.canonical(changed)
            if repository != "YehorBabenko88/strattester":
                with self.assertRaises(ValueError):
                    lab_release.parse_manifest(raw,hashlib.sha256(raw).hexdigest())
        # Retain all otherwise valid pinned paths: rejection must be due to
        # the *selected module*, not an absent executable in a smaller fixture.
        legacy = copy.deepcopy(self.manifest)
        legacy["sources"]["market_data"] = copy.deepcopy(
            self.legacy["sources"]["market_data"])
        old = self.program(V2_ENTRY)
        with self.assertRaises(ActivationBlocked):
            service_module_runtime._module_arguments(
                self.grant, {"programs":{"market_data":old}},
                legacy, "market_data")

    def test_v2_cannot_escape_lab_or_reuse_collector_manifest(self):
        for key,value in (("schema","unified.lab-release.collector.v2"),
                          ("mode","TRUSTED_RELEASE"),("mode","PRODUCTION")):
            m=copy.deepcopy(self.manifest)
            m[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(
                    MarketDataEntryRejected):
                entry_for_manifest(m)

    def test_missing_or_injected_module_hash_refused(self):
        for path in V2_FILES:
            changed = copy.deepcopy(self.manifest)
            changed["files"].pop(path)
            with self.subTest(path=path), self.assertRaises(MarketDataEntryRejected):
                entry_for_manifest(changed)
        changed = copy.deepcopy(self.manifest)
        changed["files"][V2_FILES[1]]["sha256"] = "A" * 64
        with self.assertRaises(MarketDataEntryRejected):
            entry_for_manifest(changed)
        changed = copy.deepcopy(self.manifest)
        changed["files"][V2_FILES[2]]["bytes"] = True
        with self.assertRaises(MarketDataEntryRejected):
            entry_for_manifest(changed)

    def test_unpinned_or_duplicate_wheel_dependency_refused(self):
        for mutation in ("old-version", "missing", "duplicate", "raw-token"):
            m = copy.deepcopy(self.manifest)
            wheel = next(x for x in m["dependencies"] if x["name"] == "market-data")
            if mutation == "old-version": wheel["version"] = "0.1.0"
            elif mutation == "missing": m["files"].pop(self.lock)
            elif mutation == "duplicate": m["dependencies"].append(copy.deepcopy(wheel))
            else: wheel["lock_path"] = "../../private-token"
            with self.subTest(mutation=mutation), self.assertRaises(
                    MarketDataEntryRejected):
                entry_for_manifest(m)

    def test_wrong_schema_or_version_refused_before_dispatch(self):
        for field, value in (("commit", "1"*40), ("version", "0.2.0"),
                             ("root", "other/market_data")):
            m = copy.deepcopy(self.manifest)
            m["sources"]["market_data"][field] = value
            with self.subTest(field=field), self.assertRaises(MarketDataEntryRejected):
                entry_for_manifest(m)

    def test_two_root_guards_agree_on_new_exact_argv(self):
        config = {"programs": {"market_data": self.program()}}
        argv = service_module_runtime._module_arguments(self.grant, config,
                                                         self.manifest, "market_data")
        self.assertEqual(argv, ["serve"])
        lab_runtime.launch_profile("market_data", config["programs"]["market_data"],
                                   self.root, self.manifest, self.root/"state", "LS5")
        wrapped = service_module_runtime.protected_programs(config,self.grant,self.manifest)
        self.assertEqual(wrapped["programs"]["market_data"]["argv"][-2:],
                         ["--module-source","market_data"])
        self.assertEqual(config["programs"]["market_data"]["argv"][-2:], ["--","serve"])

    def test_v2_does_not_fallback_to_legacy_entry(self):
        program = self.program(LEGACY_ENTRY)
        config = {"programs":{"market_data":program}}
        with self.assertRaises(ActivationBlocked):
            service_module_runtime._module_arguments(self.grant,config,self.manifest,
                                                     "market_data")
        with self.assertRaises(ValueError):
            lab_runtime.launch_profile("market_data",program,self.root,self.manifest,
                                       self.root/"state","LS5")

    def test_invalid_loopback_port_or_cli_argument_refused(self):
        for mutation in ("remote-host", "wrong-port", "extra-argv"):
            config = {"programs":{"market_data":self.program()}}
            p = config["programs"]["market_data"]
            if mutation == "remote-host":
                p["health_url"] = "http://0.0.0.0:8766/health"
            elif mutation == "wrong-port":
                p["env"]["MARKET_DATA_PORT"] = "8767"
            else:
                p["argv"].append("--unmanaged")
            with self.subTest(mutation=mutation), self.assertRaises(ActivationBlocked):
                service_module_runtime._module_arguments(self.grant,config,self.manifest,
                                                         "market_data")

    def test_grid_v2_native_module_import_is_blocked_without_c_db_fence(self):
        from unified_system import owned_python
        state=self.root/"state";cache=state/"only-cache";cache.mkdir(parents=True)
        config = {"programs":{"market_data":self.program()},
                  "state_root":str(state),"release_id":"lab-1"}
        fake=SimpleNamespace(require_current=lambda:True)
        def owned(*,admitted_run):
            return admitted_run()
        with patch.dict(os.environ, UNIFIED_PRIVATE_CACHE_ROOT=str(cache),
                        UNIFIED_MODULE_ID="market_data",
                        UNIFIED_MODULE_VERSION=V2_SOURCE_VERSION,
                        UNIFIED_RELEASE_ID="lab-1"),patch.object(
                        service_module_runtime,"StartupSourceAdmission",return_value=fake
                        ),patch.object(owned_python,"main",side_effect=owned),patch.object(
                        service_module_runtime.importlib,"import_module",
                        side_effect=AssertionError("NO_APPLICATION_IMPORT")) as imported:
            with self.assertRaisesRegex(ResourceFenceBlocked,
                                        "NATIVE_DB_FENCE_NOT_ADMITTED"):
                service_module_runtime.serve_module(self.grant,config,self.manifest,
                                                    "market_data")
            imported.assert_not_called()


if __name__ == "__main__":
    unittest.main()
