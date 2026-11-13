"""Qualification SOURCE. --inert runs CPU/data fixtures, never real driver code.

Actual sealing/import/loop/client/SQL require separate external Root allocations.
Fixture archives cannot qualify as the pinned real wheel or native dependency.
"""
import base64
import csv
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import unittest
import zipfile


def _need(ok,code='ASYNCPG_QUALIFICATION_REJECTED'):
    if not ok: raise ValueError(code)


def transaction_trace_observation(events):
    """Driver command acknowledgements, NOT independent server-state sampling.

    Pure synthetic tests establish this reducer only, not a real transaction.
    """
    _need(type(events) is tuple and len(events)<=64)
    commands=[]
    for row in events:
        _need(type(row) is tuple and len(row)==2)
        query,ok=row
        _need(type(query) is str and len(query)<=8192 and type(ok) is bool)
        if ok: commands.append(' '.join(query.upper().split()))
    return dict(serializable_begin_ack=any(query.startswith('BEGIN ') and
        'ISOLATION LEVEL SERIALIZABLE' in query for query in commands),
        readonly_repeatable_begin_ack=any(query.startswith('BEGIN ') and
        'ISOLATION LEVEL REPEATABLE READ' in query and 'READ ONLY' in query for query in commands),
        independent_server_state_observed=False)


def probe_asyncpg_import(*,wheel_path,dependency_root):
    """Future PhaseB/C ONLY; caller owns actual import/native effects admission.

    Requires fresh interpreter asyncpg namespace and externally configured roots.
    Does not edit sys.path, load DLLs with ctypes or manufacture an approval.
    Actual OS/native-image census and import confinement remain Root-owned.
    """
    import importlib.machinery
    import sys
    from tools.collector.seal_asyncpg_dependency import verify_sealed_dependency,NATIVE
    verify_sealed_dependency(wheel_path,dependency_root)
    root=Path(dependency_root)
    _need(not any(name=='asyncpg' or name.startswith('asyncpg.') for name in sys.modules),
          'ASYNCPG_NAMESPACE_ALREADY_LOADED')
    spec=importlib.machinery.PathFinder.find_spec('asyncpg')
    _need(spec is not None and type(spec.origin) is str and
          Path(spec.origin)==root/'asyncpg/__init__.py','ASYNCPG_IMPORT_ORIGIN')
    driver=importlib.import_module('asyncpg')  # NOT executed by --inert.
    expected={'asyncpg':'asyncpg/__init__.py','asyncpg.connection':'asyncpg/connection.py',
        'asyncpg.transaction':'asyncpg/transaction.py',
        **{name[:-4].rsplit('.',1)[0].replace('/','.') :name for name in NATIVE}}
    origins={}
    for name,path in expected.items():
        module=importlib.import_module(name)
        _need(module.__spec__ is not None and type(module.__spec__.origin) is str)
        _need(Path(module.__spec__.origin)==root/path,'ASYNCPG_IMPORT_ORIGIN')
        origins[name]=dict(path=str(root/path),sha256=hashlib.sha256((root/path).read_bytes()).hexdigest())
    _need(type(driver.__version__) is str and driver.__version__=='0.32.0')
    _need(driver.Record is sys.modules['asyncpg.protocol.record'].Record
          and driver.Connection is sys.modules['asyncpg.connection'].Connection)
    verify_sealed_dependency(wheel_path,dependency_root)
    return driver,dict(scope='ACTUAL_IMPORT_OBSERVATIONS_ONLY',origins=origins,
        os_native_image_census_observed=False,runtime_admitted=False,publisher_authenticated=False)


class _TransactionTrace:
    def __init__(self): self.events=[];self.failed=False;self.seen=0
    def __call__(self,record):
        self.seen+=1
        if self.seen>512: self.failed=True;return
        query=record.query
        if type(query) is not str or len(query)>8192: self.failed=True;return
        if not query.lstrip().upper().startswith(('BEGIN','COMMIT','ROLLBACK')): return
        if len(self.events)>=64: self.failed=True;return
        self.events.append((query,record.exception is None))


def _record_values(row,record_type,fields):
    _need(type(record_type) is type and type(row) is record_type,'ACTUAL_ASYNCPG_RECORD_REQUIRED')
    _need(type(fields) is tuple and all(type(key) is str for key in fields))
    keys=tuple(row.keys());_need(all(type(key) is str for key in keys))
    _need(len(keys)==len(fields) and set(keys)==set(fields))
    values=tuple(row[key] for key in fields)
    _need(all(type(value) is str for value in values))
    return values


async def qualify_asyncpg_client(*,wheel_path,dependency_root,connection_factory,
        binding,history,checkpoint,lifecycle_state,observation_kinds):
    """Future PhaseC actual-unit leaf. Never called by the inert suite/CLI.

    Root supplies an authenticated factory and default loop/custody; at most two
    sequential genuine connections, no pool. A returned exact Connection passes
    ownership here for close; factory retains custody of any invalid returned
    object. Close failure/cancellation propagates UNKNOWN, never a clean receipt.
    """
    import asyncio
    from dataclasses import replace
    from unified_system.storage.collector_metadata import (
        CollectorMetadataAdapter,CollectorMetadataBinding,MetadataBlocked)
    from unified_system.storage.raw_capture import LocalRawCaptureReadback
    from unified_system.storage.collector_context import LocalCollectorCheckpoint
    _need(type(binding) is CollectorMetadataBinding and type(history) is tuple and 1<=len(history)<=16)
    _need(all(type(item) is LocalRawCaptureReadback for item in history)
          and type(checkpoint) is LocalCollectorCheckpoint and callable(connection_factory))
    _need(type(lifecycle_state) is str and lifecycle_state in ('STOPPED','UNKNOWN','TERMINAL'))
    driver,imports=probe_asyncpg_import(wheel_path=wheel_path,dependency_root=dependency_root)
    traces=[]

    async def use(operation):
        connection=await connection_factory()
        _need(type(connection) is driver.Connection,'ACTUAL_ASYNCPG_CONNECTION_REQUIRED')
        trace=_TransactionTrace();primary=None
        try:
            _need(connection.is_in_transaction() is False)
            connection.add_query_logger(trace)
            identity=await connection.fetchrow('SELECT current_user::text AS role, session_user::text AS login, current_database()::text AS database')
            role,login,database=_record_values(identity,driver.Record,('role','login','database'))
            _need(role==login=='unified_lab_collector_app' and database=='unified_lab_collector_c0c2')
            return await operation(connection)
        except BaseException as error:
            primary=error
            raise
        finally:
            try:
                await connection.close(timeout=5)
                _need(connection.is_closed() is True,'CONNECTION_CLOSE_UNKNOWN')
                await asyncio.sleep(0)  # Flush this driver's scheduled logger callbacks.
                connection.remove_query_logger(trace)
                _need(not trace.failed,'TRANSACTION_TRACE_UNKNOWN')
                traces.extend(trace.events)
            except BaseException as cleanup:
                if primary is not None:
                    raise BaseExceptionGroup('actual client primary/retirement uncertainty',[primary,cleanup]) from None
                raise

    probe_id='synthetic-asyncpg-rollback-probe'
    request=dict(binding=binding,history=history,checkpoint=checkpoint,
        lifecycle_state=lifecycle_state,observation_kinds=observation_kinds)
    async def first(connection):
        count=await connection.fetchval('SELECT count(*) FROM collector_metadata_v1.instrument WHERE instrument_id=$1',probe_id)
        _need(type(count) is int and count==0)
        adapter=CollectorMetadataAdapter(connection)
        value=await adapter.project(**request)
        _need(await adapter.project(**request)==value,'EXACT_REPLAY_MISMATCH')
        try:
            await adapter.project(**dict(request,binding=replace(binding,instrument_id=probe_id)))
        except MetadataBlocked: pass
        else: raise ValueError('ROLLBACK_CASE_NOT_REJECTED')
        return value
    projected=await use(first)
    async def second(connection):
        actual=await CollectorMetadataAdapter(connection).readback(binding=binding)
        _need(actual==projected,'FRESH_READBACK_MISMATCH')
        count=await connection.fetchval('SELECT count(*) FROM collector_metadata_v1.instrument WHERE instrument_id=$1',probe_id)
        _need(type(count) is int and count==0,'ROLLBACK_NOT_OBSERVED')
        rows=await connection.fetch('SELECT context_id,observation_sha256,raw_journal_digest FROM collector_metadata_v1.observation_ref WHERE context_id=$1 ORDER BY observation_sha256 LIMIT 17',binding.context_id)
        _need(type(rows) is list and len(rows)<=16)
        values=tuple(_record_values(row,driver.Record,('context_id','observation_sha256','raw_journal_digest')) for row in rows)
        _need(values==tuple((binding.context_id,item.observation_sha256,item.raw_journal_digest)
                           for item in actual.observations),'NATIVE_RECORD_READBACK_MISMATCH')
        return actual
    actual=await use(second)
    from tools.collector.seal_asyncpg_dependency import verify_sealed_dependency
    verify_sealed_dependency(wheel_path,dependency_root)
    observed=transaction_trace_observation(tuple(traces))
    _need(observed['serializable_begin_ack'] and observed['readonly_repeatable_begin_ack'])
    return dict(scope='ACTUAL_CLIENT_OBSERVATIONS_ONLY',classification='LOCAL_UNATTESTED',
        context_id=actual.binding.context_id,binding_sha256=actual.binding.binding_sha256,
        observation_count=len(actual.observations),fresh_readback_equal=True,
        exact_native_record_rows_observed=len(actual.observations),
        rollback_after_tentative_insert_observed=True,sql_error_injection_observed=False,
        imports=imports,transaction_commands=observed,connection_closed_flag_observed=True,
        os_connection_backend_retirement_proven=False,publication_confirmed=False,
        native_authority='UNKNOWN',runtime_admitted=False,backup_restore_qualified=False)


def _fixture(*, extra=None, bad_record=False, native_extra=False,tag='cp312-cp312-win_amd64'):
    values = {'asyncpg/__init__.py':b'raise RuntimeError("INERT NEVER IMPORT")\n',
        'asyncpg/protocol/protocol.cp312-win_amd64.pyd':b'INERT_PROTOCOL_DATA',
        'asyncpg/protocol/record.cp312-win_amd64.pyd':b'INERT_RECORD_DATA',
        'asyncpg/pgproto/pgproto.cp312-win_amd64.pyd':b'INERT_PGPROTO_DATA',
        'asyncpg-0.32.0.dist-info/METADATA':b'Metadata-Version: 2.1\nName: asyncpg\nVersion: 0.32.0\nRequires-Python: >=3.9.0\n\n',
        'asyncpg-0.32.0.dist-info/WHEEL':('Wheel-Version: 1.0\nRoot-Is-Purelib: false\nTag: '+tag+'\n\n').encode()}
    if extra: values.update(extra)
    if native_extra: values['asyncpg/unexpected.dll'] = b'INERT'
    output = io.StringIO(newline='')
    writer = csv.writer(output,lineterminator='\n')
    for name,data in values.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
        writer.writerow((name,'sha256='+('a'*43 if bad_record else digest),str(len(data))))
    writer.writerow(('asyncpg-0.32.0.dist-info/RECORD','',''))
    values['asyncpg-0.32.0.dist-info/RECORD'] = output.getvalue().encode()
    raw = io.BytesIO()
    with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,data in values.items(): archive.writestr(name,data)
    return raw.getvalue()


class InertQualificationTests(unittest.TestCase):
    def setUp(self):
        try: self.seal = importlib.import_module('tools.collector.seal_asyncpg_dependency')
        except ModuleNotFoundError: self.fail('sealed dependency source is missing')
        self.root = Path(os.environ['A4_DEPENDENCY_INERT_SCRATCH'])/self._testMethodName
        self.root.mkdir(exist_ok=False)

    def test_closed_fixture_inventory_is_data_only(self):
        inventory = self.seal._archive_inventory(_fixture())
        self.assertEqual(len(inventory),7)
        self.assertEqual(len([row for row in inventory if row[0].endswith('.pyd')]),3)

    def test_real_wheel_gate_rejects_fixture_before_destination_creation(self):
        source = self.root/'fixture.whl'; source.write_bytes(_fixture())
        target = self.root/'not-created'
        with self.assertRaises(ValueError): self.seal.seal_asyncpg_dependency(source,target)
        self.assertFalse(target.exists())

    def test_materialized_fixture_rehashes_but_is_not_real_dependency(self):
        raw = _fixture(); inventory = self.seal._archive_inventory(raw)
        target = self.root/'fixture-data'
        observation = self.seal._materialize(target,inventory,hashlib.sha256(raw).hexdigest())
        self.assertFalse(observation['runtime_admitted'])
        self.assertFalse(observation['native_imported'])
        self.seal._verify_inventory(target,inventory,hashlib.sha256(raw).hexdigest())
        source = self.root/'fixture.whl'; source.write_bytes(raw)
        with self.assertRaises(ValueError): self.seal.verify_sealed_dependency(source,target)

    def test_existing_destination_never_overwritten(self):
        target=self.root/'occupied';target.mkdir();(target/'keep').write_bytes(b'keep')
        inventory=self.seal._archive_inventory(_fixture())
        with self.assertRaises(FileExistsError): self.seal._materialize(target,inventory,'a'*64)
        self.assertEqual((target/'keep').read_bytes(),b'keep')

    def test_record_corruption_denied(self):
        with self.assertRaises(ValueError): self.seal._archive_inventory(_fixture(bad_record=True))

    def test_paths_aliases_and_case_duplicates_denied(self):
        for path in ('../outside','asyncpg/../outside','asyncpg/CON.py','asyncpg/bad. ',
                     'asyncpg\\bad.py','asyncpg/__INIT__.py','asyncpg/module.pth','other/file'):
            with self.subTest(path=path),self.assertRaises(ValueError):
                self.seal._archive_inventory(_fixture(extra={path:b'inert'}))

    def test_extra_native_is_denied(self):
        with self.assertRaises(ValueError): self.seal._archive_inventory(_fixture(native_extra=True))

    def test_member_count_and_expansion_budgets_deny(self):
        with self.assertRaises(ValueError):
            self.seal._archive_inventory(_fixture(extra={f'asyncpg/f{i}.txt':b'' for i in range(506)}))
        with self.assertRaises(ValueError): self.seal._archive_inventory(b'x'*(8*1024*1024+1))

    def test_tamper_and_unexpected_file_reject_without_cleanup(self):
        raw=_fixture();inventory=self.seal._archive_inventory(raw);sha=hashlib.sha256(raw).hexdigest()
        target=self.root/'fixture-data';self.seal._materialize(target,inventory,sha)
        leaf=target/'asyncpg/__init__.py';leaf.write_bytes(b'corrupt')
        with self.assertRaises(ValueError): self.seal._verify_inventory(target,inventory,sha)
        self.assertEqual(leaf.read_bytes(),b'corrupt')

    def test_extra_file_rejects(self):
        raw=_fixture();inventory=self.seal._archive_inventory(raw);sha=hashlib.sha256(raw).hexdigest()
        target=self.root/'fixture-data';self.seal._materialize(target,inventory,sha)
        (target/'unaccounted').write_bytes(b'retain')
        with self.assertRaises(ValueError): self.seal._verify_inventory(target,inventory,sha)

    def test_strict_scalar_types_before_callbacks(self):
        class Hostile(str):
            def __hash__(self): raise AssertionError('unexpected hash')
            def __eq__(self,other): raise AssertionError('unexpected equality')
        with self.assertRaises(ValueError): self.seal._archive_inventory(Hostile('bytes'))
        with self.assertRaises(ValueError): self.seal._materialize(self.root/'bad',(),Hostile('a'*64))

    def test_empty_wrong_abi_and_bad_zip_denied(self):
        for raw in (b'',b'notzip',_fixture(tag='cp313-cp313-win_amd64')):
            with self.subTest(size=len(raw)),self.assertRaises(ValueError): self.seal._archive_inventory(raw)

    def test_transaction_trace_reducer_has_no_independent_server_claim(self):
        self.assertTrue(callable(globals().get('transaction_trace_observation')), 'client source helper missing')
        result=transaction_trace_observation((('BEGIN ISOLATION LEVEL SERIALIZABLE;',True),
            ('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;',True)))
        self.assertTrue(result['serializable_begin_ack'])
        self.assertTrue(result['readonly_repeatable_begin_ack'])
        self.assertFalse(result['independent_server_state_observed'])
        failed=transaction_trace_observation((('BEGIN ISOLATION LEVEL SERIALIZABLE;',False),))
        self.assertFalse(failed['serializable_begin_ack'])

    def test_trace_types_and_capacity_fail_closed(self):
        self.assertTrue(callable(globals().get('transaction_trace_observation')), 'client source helper missing')
        for rows in ((('BEGIN',1),),tuple(('BEGIN',True) for _ in range(65))):
            with self.assertRaises(ValueError): transaction_trace_observation(rows)

    def test_custom_record_class_is_not_native_row_evidence(self):
        self.assertTrue(callable(globals().get('_record_values')), 'exact record guard missing')
        class InertExpectedRow(dict): pass
        class InertCustomRow(InertExpectedRow): pass
        with self.assertRaises(ValueError):
            _record_values(InertCustomRow(role='app'),InertExpectedRow,('role',))
        with self.assertRaises(ValueError):
            _record_values({'role':'app'},InertExpectedRow,('role',))

    def test_inert_entry_never_imports_driver_or_asyncio(self):
        import sys
        self.assertFalse(any(name=='asyncpg' or name.startswith('asyncpg.') for name in sys.modules))
        self.assertNotIn('asyncio',sys.modules)


if __name__ == '__main__':
    import sys
    if sys.argv[1:] != ['--inert']: raise SystemExit('Only explicit --inert runs here; actual units require Root custody')
    unittest.main(argv=[sys.argv[0]],verbosity=2)
