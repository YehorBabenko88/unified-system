"""Isolated E bridge contract tests; NO native PG18 or host admission.

Every C/Consul/OS witness below is a fake injected object. Positive assessment
only checks *compatibility*, never authorizes native service or SQL writes.
"""
import asyncio
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from unified_system.consul_authority import (
    ConsulConfig, ConsulLease, ConsulSessionAuthority,
)
from unified_system.grid_writer_fence_model import (
    ResourceFenceBlocked, WriterLeaseIdentity,
)
from unified_system.grid_writer_lab_bridge import (
    LabFenceAssessment,assess_lab_c_fence,native_writer_admission,
)
from unified_system.market_data_entry_contract import (
    APPROVED_GRID_COMMIT,GRID_REPOSITORY,V2_SOURCE_VERSION,V2_FILES,
)


class Source:
    def __init__(self,root):
        self.root=root
        self.active=True
        self.calls=0
    def require_current(self):
        self.calls+=1
        return self.active
    def source_scope(self,module,actual,commit):
        if (module!="market_data" or actual!=self.root
                or commit!=APPROVED_GRID_COMMIT):
            raise ValueError("REVOKED_SOURCE")
        return self.root


class Legacy:
    active=True
    quiescent=True
    def require_current(self):
        return self.active
    def confirmed_quiescent(self):
        return self.quiescent


class LabPg:
    started=True
    postmaster=1401
    def _verify_owned(self):
        return None
    def _verify_postmaster(self):
        return self.postmaster


class BridgeTests(unittest.TestCase):
    def setUp(self):
        t=TemporaryDirectory();self.addCleanup(t.cleanup)
        root=Path(t.name).resolve()
        self.source_root=root/"sources/market_data"
        self.source_root.mkdir(parents=True)
        self.manifest={
            "schema":"unified.lab-release.v1","mode":"LAB_SIMULATION",
            "sources":{"market_data":{
                "repository":GRID_REPOSITORY,"commit":APPROVED_GRID_COMMIT,
                "version":V2_SOURCE_VERSION,"root":"sources/market_data",
            }},"files":{},"dependencies":[],
        }
        contents={}
        self.files=(
            "market_data/provenance.py","market_data/history_api.py",
            "market_data_v2/qualified_read_contract.py",
            "market_data_v2/read_api.py",
        )
        for rel in (*self.files,"grid/migrations.py",
                    "market_data_v2/__init__.py"):
            data=("inert:"+rel).encode("ascii")
            p=self.source_root/rel
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_bytes(data)
            contents[rel]=data
            self.manifest["files"]["sources/market_data/"+rel]={
                "sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),
            }
        wheel="dependencies/market-data.lock"
        self.manifest["files"][wheel]={
            "sha256":hashlib.sha256(b"inert-wheel-lock").hexdigest(),
            "bytes":len(b"inert-wheel-lock"),
        }
        self.manifest["dependencies"].append({
            "name":"market-data","version":"0.2.0.dev0","lock_path":wheel,
        })
        digest=hashlib.sha256()
        for rel in self.files:
            digest.update(rel.encode("ascii")+b"\0"+contents[rel]+b"\0")
        source_sha=digest.hexdigest()
        schema_sha=hashlib.sha256(contents["grid/migrations.py"]).hexdigest()
        config=ConsulConfig(
            ("http://127.0.0.1:8500",),"unified/primary",isolated_lab=True,
        )
        self.authority=ConsulSessionAuthority(config,client=object())
        self.authority.validate=AsyncMock(return_value=True)
        self.lease=ConsulLease("root-controller",str(uuid.uuid4()),101)
        self.identity=WriterLeaseIdentity(
            self.lease.owner,config.namespace,self.lease.session_id,
            self.lease.token,str(uuid.uuid4()),str(uuid.uuid4()),
            source_sha,schema_sha,
        )
        self.source=Source(self.source_root)
        self.legacy=Legacy()
        self.pg=LabPg()
        self.c_claims=[]
        def c_claim(*args,**kwargs):
            self.c_claims.append((args,kwargs))
            raise AssertionError("SQL CLAIM MUST NEVER OCCUR")
        self.c=SimpleNamespace(
            fence_identity=lambda:{
                "schema":"lab-postgres-writer-fence.v1",
                "resource_id":"grid-market-data-primary",
                "scope":"ISOLATED_LAB_ONLY","execution_authority":False,
                "native_admission":False,
            },
            fenced_lab_witness=lambda pg:{
                "schema":"lab-postgres-fenced-custody.v1",
                "scope":"ISOLATED_LAB_ONLY","direct_writer_insert":False,
                "writer_exec":True,"reader_exec":False,
                "execution_authority":False,"trading_authorized":False,
            },
            claim_lab_fence=c_claim,
        )
    def assess(self):
        return asyncio.run(assess_lab_c_fence(
            authority=self.authority,lease=self.lease,source=self.source,
            manifest=self.manifest,identity=self.identity,generation=1,
            pg=self.pg,c_module=self.c,legacy_witness=self.legacy,
            source_root=self.source_root,
        ))

    def test_pinned_source_and_consul_shape_checks_never_grant_native(self):
        result=self.assess()
        self.assertIsInstance(result,LabFenceAssessment)
        self.assertEqual(result.code,"LAB_EVIDENCE_VALIDATED_NOT_NATIVE")
        self.assertIs(result.native_admitted,False)
        self.assertEqual(self.c_claims,[])
        self.authority.validate.assert_awaited()

    def test_lost_quorum_lease_rejected(self):
        self.authority.validate=AsyncMock(return_value=False)
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()
        self.assertEqual(self.c_claims,[])

    def test_old_writer_not_quiescent_rejected(self):
        self.legacy.quiescent=False
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_revoke_source_before_assessment_rejected(self):
        self.source.active=False
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_wrong_session_token_namespace_cannot_be_accepted(self):
        from dataclasses import replace
        for field,value in (("token",102),
                            ("namespace","unified/foreign"),
                            ("session_id",str(uuid.uuid4()))):
            old=self.identity
            self.identity=replace(old,**{field:value})
            with self.subTest(field=field),self.assertRaises(ResourceFenceBlocked):
                self.assess()
            self.identity=old

    def test_different_source_or_schema_hash_rejected(self):
        from dataclasses import replace
        for field in ("source_sha256","schema_sha256"):
            old=self.identity
            self.identity=replace(old,**{field:"f"*64})
            with self.subTest(field=field),self.assertRaises(ResourceFenceBlocked):
                self.assess()
            self.identity=old

    def test_changed_file_bytes_never_match_manifest(self):
        rel="market_data_v2/read_api.py"
        path=self.source_root/rel
        path.write_bytes(b"tampered payload")
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_missing_source_file_fails_closed(self):
        (self.source_root/"grid/migrations.py").unlink()
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_wrong_postmaster_pid_is_rejected(self):
        self.pg.postmaster=0
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_c_witness_direct_insert_bypass_fails_closed(self):
        original=self.c.fenced_lab_witness
        self.c.fenced_lab_witness=lambda _:dict(
            original(self.pg),direct_writer_insert=True)
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_untrusted_production_authority_not_accepted(self):
        self.authority.config=ConsulConfig(
            ("https://127.0.0.1:8500",),"unified/primary",
            acl_token="fake",ca_bundle="ca",client_certificate="cert",
            client_key="key",isolated_lab=False,
        )
        with self.assertRaises(ResourceFenceBlocked):
            self.assess()

    def test_direct_native_bridge_admission_always_denied(self):
        with self.assertRaisesRegex(ResourceFenceBlocked,
                                    "NATIVE_DB_FENCE_NOT_ADMITTED"):
            native_writer_admission(self.source,self.manifest,self.pg)

if __name__=="__main__":
    unittest.main()
