import datetime as dt
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from unified_system.observer.model import ObserverError,SourcePolicy
from unified_system.observer.mission import (ENGINE_PINS,ENGINE_VERSION,
    MissionJournalCopySource,PinnedExistingMissionReader)

NOW=dt.datetime(2026,11,11,20,tzinfo=dt.timezone.utc)
ROOT=Path(__file__).resolve().parents[2]

class MissionCopyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();engine=self.root/'engine';engine.mkdir()
        for name,pin in ENGINE_PINS.items():
            raw=(ROOT/'unified_system'/(name+'.py')).read_bytes()
            if hashlib.sha256(raw).hexdigest()!=pin:
                # Developer worktrees may use CRLF; qualification capsule always
                # holds exact primary bytes. No normalized source is executed.
                raw=subprocess.check_output([shutil.which('git'),'--no-replace-objects',
                    '-C',str(ROOT),'show',ENGINE_VERSION+':unified_system/'+name+'.py'],timeout=5)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),pin)
            (engine/(name+'.py')).write_bytes(raw)
        self.reader=PinnedExistingMissionReader(engine)
        self.path=self.root/'fixture.db'
        self.reader.controller.create(self.path)
        self.raw=self.path.read_bytes()
        self.policy=SourcePolicy('mission-copy','mission_projection',ENGINE_VERSION,mode='UNQUALIFIED')

    def source(self,**kw):
        return MissionJournalCopySource(self.policy,self.path,self.root/'copies',self.reader,
                                       read_copy_admitted=kw.get('admitted',True))

    def test_existing_reader_only_opens_owncopy_no_source_sql_or_mutation(self):
        original=sqlite3.connect
        def guarded(path,*args,**kw):
            self.assertNotIn('fixture.db',str(path));return original(path,*args,**kw)
        journal=self.reader.controller.__init__.__globals__['Journal']
        with patch('sqlite3.connect',side_effect=guarded), \
             patch.object(journal,'initialize',side_effect=AssertionError('MUTATION')), \
             patch.object(journal,'append',side_effect=AssertionError('MUTATION')):
            facts=self.source().read(NOW)
        self.assertEqual(facts[0].value,1)
        self.assertEqual(facts[0].digest,hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.assertEqual(list(self.root.glob('fixture.db-*')),[])

    def test_admission_and_engine_pin_are_mandatory(self):
        with self.assertRaises(ObserverError):self.source(admitted=False)
        p=self.root/'engine/contracts.py';p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaises(ObserverError):PinnedExistingMissionReader(p.parent)

    def test_busy_sidecars_never_repaired(self):
        source=self.source()
        for suffix in ('-wal','-shm','-journal'):
            sidecar=Path(str(self.path)+suffix);sidecar.write_bytes(b'busy')
            with self.assertRaises(ObserverError):source.read(NOW)
            self.assertEqual(sidecar.read_bytes(),b'busy');sidecar.unlink()
        self.assertEqual(self.path.read_bytes(),self.raw)

    def test_wal_header_and_corrupt_source_fail_closed(self):
        source=self.source()
        for raw in (self.raw[:18]+b'\2\2'+self.raw[20:],b'corrupt'):
            self.path.write_bytes(raw)
            with self.assertRaises(ObserverError):source.read(NOW)
            self.assertEqual(self.path.read_bytes(),raw)

    def test_changed_source_never_publishes(self):
        source=self.source()
        original=Path.stat;calls=0
        def stat(path,*args,**kw):
            nonlocal calls
            if path==self.path:
                calls+=1
                if calls==3:
                    with path.open('ab') as stream:stream.write(b'x')
            return original(path,*args,**kw)
        with patch.object(Path,'stat',stat):
            with self.assertRaises(ObserverError):source.read(NOW)

    def test_restart_reuses_verified_owncopy_and_rejects_foreign_files(self):
        self.source().read(NOW)
        facts=self.source().read(NOW)
        self.assertEqual(facts[0].value,1)
        self.assertEqual(len(list((self.root/'copies').glob('*.sqlite'))),1)
        (self.root/'copies/foreign.txt').write_text('unowned')
        with self.assertRaises(ObserverError):self.source().read(NOW)

    def test_incompatible_journal_schema_is_not_treated_as_committed(self):
        db=sqlite3.connect(self.path)
        try:db.execute('DROP TABLE transitions');db.commit()
        finally:db.close()
        error=self.reader.controller.open.__func__.__globals__['ContractError']
        with self.assertRaises(error):self.source().read(NOW)

    def test_hardlinked_source_and_unstable_header_are_rejected(self):
        alias=self.root/'hardlink.db';os.link(self.path,alias)
        with self.assertRaises(ObserverError):self.source().read(NOW)
        alias.unlink()
        changed=bytearray(self.raw);changed[92:96]=b'\xff\xff\xff\xff';self.path.write_bytes(changed)
        with self.assertRaises(ObserverError):self.source().read(NOW)

    def test_source_inside_copy_directory_is_rejected_without_changes(self):
        with self.assertRaises(ObserverError):
            MissionJournalCopySource(self.policy,self.path,self.root,self.reader,read_copy_admitted=True)
        self.assertEqual(self.path.read_bytes(),self.raw)
        self.assertEqual(set(p.name for p in self.root.iterdir()),{'fixture.db','engine'})
