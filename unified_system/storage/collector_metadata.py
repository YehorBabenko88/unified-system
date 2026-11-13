"""Bounded v1 metadata projection; caller owns connection/runtime admission.

No connection, authentication, pool, migration, raw store or authority is created.
Structural driver compatibility cannot authenticate/admit a supplied connection.
Gap labels are caller reports; scientific quality/coverage remain UNKNOWN.
"""
from dataclasses import dataclass
import hashlib
import re

from .raw_capture import LocalRawCaptureReadback
from .collector_context import LocalCollectorCheckpoint


class MetadataBlocked(ValueError):
    pass


def _need(ok):
    if not ok: raise MetadataBlocked('COLLECTOR_METADATA_REJECTED')


def _text(value, limit):
    _need(type(value) is str and 1 <= len(value) <= limit and '\x00' not in value)
    return value


def _hex(value, size=64):
    _need(type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}', value) is not None)
    return value


def _choice(value, choices):
    _need(type(value) is str)
    _need(value in choices)
    return value


def _integer(value, low, high):
    _need(type(value) is int and low <= value <= high)
    return value


@dataclass(frozen=True)
class CollectorMetadataBinding:
    context_id: str
    binding_sha256: str
    store_id: str
    instrument_id: str
    identity_kind: str
    identity_contract_sha256: str | None


@dataclass(frozen=True)
class MetadataObservation:
    observation_sha256: str
    raw_journal_digest: str
    payload_sha256: str | None
    payload_byte_count: int
    observation_kind: str
    continuity = property(lambda self: 'UNKNOWN')


@dataclass(frozen=True)
class MetadataReadback:
    binding: CollectorMetadataBinding
    lifecycle_state: str
    observations: tuple
    checkpoint: LocalCollectorCheckpoint | None
    holds: tuple
    custody = property(lambda self: 'LOCAL_UNATTESTED')
    publication_confirmed = property(lambda self: False)
    native_outcome = property(lambda self: 'UNKNOWN')
    quality = property(lambda self: 'UNKNOWN')
    coverage = property(lambda self: 'UNKNOWN')


def _binding(value):
    _need(type(value) is CollectorMetadataBinding)
    _hex(value.context_id, 32); _hex(value.binding_sha256)
    _need(type(value.store_id) is str and re.fullmatch(
        '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}', value.store_id) is not None)
    _text(value.instrument_id, 256)
    _choice(value.identity_kind, ('SYNTHETIC','UNKNOWN'))
    if value.identity_contract_sha256 is not None: _hex(value.identity_contract_sha256)
    return value


def _row(row, fields):
    # Validate driver-returned keys before any hashing/equality on them.
    keys = tuple(row.keys())
    _need(all(type(key) is str for key in keys))
    _need(len(keys) == len(fields) and set(keys) == set(fields))
    return {key: row[key] for key in keys}


def _rows(rows, maximum):
    _need(type(rows) in (list, tuple) and len(rows) <= maximum)
    return rows


def _observation(row):
    row = _row(row, ('context_id','observation_sha256','raw_journal_digest',
        'payload_sha256','payload_byte_count','observation_kind','continuity'))
    _hex(row['context_id'], 32)
    _hex(row['observation_sha256']); _hex(row['raw_journal_digest'])
    if row['payload_sha256'] is not None: _hex(row['payload_sha256'])
    _integer(row['payload_byte_count'], 0, 1048576)
    _need(row['payload_sha256'] is not None or row['payload_byte_count'] == 0)
    _choice(row['observation_kind'], ('OPAQUE','SYNTHETIC','GAP'))
    _choice(row['continuity'], ('UNKNOWN',))
    return row['context_id'], MetadataObservation(*(row[key] for key in (
        'observation_sha256','raw_journal_digest','payload_sha256','payload_byte_count','observation_kind')))


def _checkpoint(value, context_id, observations):
    if value is None: return None
    _need(type(value) is LocalCollectorCheckpoint)
    _hex(value.context_id, 32); _hex(value.observation_sha256); _hex(value.raw_journal_digest)
    _integer(value.local_lifecycle_sequence, 1, 128)
    _need(value.context_id == context_id)
    found = observations.get(value.observation_sha256)
    _need(found is not None and found.raw_journal_digest == value.raw_journal_digest)
    return value


def _snapshot(binding, history, checkpoint, state, kinds):
    _binding(binding); _choice(state, ('ACTIVE','STOPPED','UNKNOWN','TERMINAL'))
    _need(type(history) is tuple and len(history) <= 16 and type(kinds) is dict)
    for key, value in kinds.items():
        _hex(key); _choice(value, ('OPAQUE','SYNTHETIC','GAP'))
    observations = {}
    for item in history:
        _need(type(item) is LocalRawCaptureReadback)
        _need(type(item.observation_bytes) is bytes)
        _integer(item.observation_byte_count, 1, 16384)
        _hex(item.observation_sha256); _hex(item.journal_record_digest)
        _need(len(item.observation_bytes) == item.observation_byte_count)
        _need(hashlib.sha256(item.observation_bytes).hexdigest() == item.observation_sha256)
        _integer(item.payload_byte_count, 0, 1048576)
        if item.payload_bytes is None:
            _need(item.payload_sha256 is None and item.payload_byte_count == 0)
        else:
            _need(type(item.payload_bytes) is bytes)
            _hex(item.payload_sha256)
            _need(len(item.payload_bytes) == item.payload_byte_count)
            _need(hashlib.sha256(item.payload_bytes).hexdigest() == item.payload_sha256)
        _need(item.observation_sha256 not in observations and item.observation_sha256 in kinds)
        observations[item.observation_sha256] = MetadataObservation(item.observation_sha256,
            item.journal_record_digest, item.payload_sha256, item.payload_byte_count, kinds[item.observation_sha256])
    _need(set(kinds) == set(observations))
    _need(sum(item.payload_byte_count for item in observations.values()) <= 4194304)
    _checkpoint(checkpoint, binding.context_id, observations)
    return observations


_CONTEXT_READ = """/* context_read */
SELECT c.context_id,c.instrument_id,c.binding_sha256,c.store_id::text AS store_id,c.custody,c.lifecycle_state,
       i.identity_kind,i.identity_contract_sha256
FROM collector_metadata_v1.context c JOIN collector_metadata_v1.instrument i USING(instrument_id)
WHERE c.context_id=$1 AND c.binding_sha256=$2 LIMIT 2"""
_OBS_READ = """/* observations_read */
SELECT context_id,observation_sha256,raw_journal_digest,payload_sha256,payload_byte_count,
       observation_kind,continuity FROM collector_metadata_v1.observation_ref
WHERE context_id=$1 ORDER BY observation_sha256 LIMIT 17"""
_CP_READ = """/* checkpoint_read */
SELECT context_id,observation_sha256,raw_journal_digest,local_lifecycle_sequence,
       native_outcome,publication_confirmed FROM collector_metadata_v1.local_checkpoint
WHERE context_id=$1 LIMIT 2"""
_HOLD_READ = """/* holds_read */
SELECT hold_id,reason FROM collector_metadata_v1.retention_hold
WHERE context_id=$1 ORDER BY hold_id LIMIT 129"""


class CollectorMetadataAdapter:
    """The caller must supply an admitted connection, not an already-open txn.

    No retries/timeouts are hidden here. Exceptions/cancellation propagate through
    the driver's transaction context; caller owns uncertain commit reconciliation.
    Successful return is metadata readback, never native publication authority.
    """
    def __init__(self, connection):
        self._connection = connection

    async def _read(self, binding, *, lock=False):
        conn = self._connection
        rows = _rows(await conn.fetch(_CONTEXT_READ + (' FOR UPDATE OF c' if lock else ''),
                                     binding.context_id, binding.binding_sha256), 1)
        _need(len(rows) == 1)
        row = _row(rows[0], ('context_id','instrument_id','binding_sha256','store_id',
                            'custody','lifecycle_state','identity_kind','identity_contract_sha256'))
        store_id = row['store_id']
        _need(type(store_id) is str)
        actual = CollectorMetadataBinding(row['context_id'], row['binding_sha256'], store_id,
            row['instrument_id'], row['identity_kind'], row['identity_contract_sha256'])
        _binding(actual); _need(actual == binding)
        _choice(row['custody'], ('LOCAL_UNATTESTED',))
        state = _choice(row['lifecycle_state'], ('ACTIVE','STOPPED','UNKNOWN','TERMINAL'))
        observations = {}
        for raw in _rows(await conn.fetch(_OBS_READ, binding.context_id), 16):
            context_id, item = _observation(raw)
            _need(context_id == binding.context_id and item.observation_sha256 not in observations)
            observations[item.observation_sha256] = item
        _need(sum(item.payload_byte_count for item in observations.values()) <= 4194304)
        cp_rows = _rows(await conn.fetch(_CP_READ, binding.context_id), 1)
        checkpoint = None
        if cp_rows:
            value = _row(cp_rows[0], ('context_id','observation_sha256','raw_journal_digest',
                                    'local_lifecycle_sequence','native_outcome','publication_confirmed'))
            _choice(value['native_outcome'], ('UNKNOWN',))
            _need(type(value['publication_confirmed']) is bool and value['publication_confirmed'] is False)
            checkpoint = _checkpoint(LocalCollectorCheckpoint(*(value[key] for key in (
                'context_id','observation_sha256','raw_journal_digest','local_lifecycle_sequence'))),
                binding.context_id, observations)
        holds = {}
        for raw in _rows(await conn.fetch(_HOLD_READ, binding.context_id), 128):
            value = _row(raw, ('hold_id','reason'))
            hold_id = _text(value['hold_id'], 256); reason = _text(value['reason'], 1024)
            _need(hold_id not in holds); holds[hold_id] = reason
        return MetadataReadback(binding, state,
            tuple(observations[key] for key in sorted(observations)), checkpoint,
            tuple(sorted(holds.items())))

    async def readback(self, *, binding):
        _binding(binding)
        async with self._connection.transaction(isolation='repeatable_read', readonly=True):
            return await self._read(binding)

    async def project(self, *, binding, history, checkpoint, lifecycle_state, observation_kinds):
        wanted = _snapshot(binding, history, checkpoint, lifecycle_state, observation_kinds)
        conn = self._connection
        async with conn.transaction(isolation='serializable'):
            await conn.execute("""/* instrument_insert */ INSERT INTO collector_metadata_v1.instrument
                (instrument_id,identity_kind,identity_contract_sha256) VALUES($1,$2,$3)
                ON CONFLICT (instrument_id) DO NOTHING""", binding.instrument_id,
                binding.identity_kind, binding.identity_contract_sha256)
            instruments = _rows(await conn.fetch("""/* instrument_read */
                SELECT instrument_id,identity_kind,identity_contract_sha256
                FROM collector_metadata_v1.instrument WHERE instrument_id=$1 LIMIT 2""",
                binding.instrument_id), 1)
            _need(len(instruments) == 1)
            instrument = _row(instruments[0], ('instrument_id','identity_kind','identity_contract_sha256'))
            _text(instrument['instrument_id'], 256)
            _choice(instrument['identity_kind'], ('SYNTHETIC','UNKNOWN'))
            if instrument['identity_contract_sha256'] is not None: _hex(instrument['identity_contract_sha256'])
            _need(tuple(instrument[key] for key in ('instrument_id','identity_kind','identity_contract_sha256'))
                  == (binding.instrument_id,binding.identity_kind,binding.identity_contract_sha256))
            await conn.execute("""/* context_insert */ INSERT INTO collector_metadata_v1.context
                (context_id,instrument_id,binding_sha256,store_id,lifecycle_state,custody)
                VALUES($1,$2,$3,$4,$5,'LOCAL_UNATTESTED') ON CONFLICT(context_id) DO NOTHING""",
                binding.context_id,binding.instrument_id,binding.binding_sha256,binding.store_id,lifecycle_state)
            before = await self._read(binding, lock=True)
            existing = {item.observation_sha256:item for item in before.observations}
            _need(all(key in wanted and wanted[key] == item for key,item in existing.items()))
            if before.lifecycle_state in ('UNKNOWN','TERMINAL'):
                _need(lifecycle_state == before.lifecycle_state)
            old = before.checkpoint
            stale = False
            if old is not None:
                _need(checkpoint is not None)
                if checkpoint.local_lifecycle_sequence == old.local_lifecycle_sequence:
                    _need(checkpoint == old)
                if checkpoint.local_lifecycle_sequence < old.local_lifecycle_sequence:
                    stale = True
                    _need(existing == wanted)
            for item in wanted.values():
                await conn.execute("""/* observation_insert */ INSERT INTO collector_metadata_v1.observation_ref
                    (context_id,observation_sha256,raw_journal_digest,payload_sha256,payload_byte_count,
                     observation_kind,continuity) VALUES($1,$2,$3,$4,$5,$6,'UNKNOWN')
                    ON CONFLICT(context_id,observation_sha256) DO NOTHING""", binding.context_id,
                    item.observation_sha256,item.raw_journal_digest,item.payload_sha256,
                    item.payload_byte_count,item.observation_kind)
            if checkpoint is not None and not stale:
                await conn.execute("""/* checkpoint_upsert */ INSERT INTO collector_metadata_v1.local_checkpoint
                    (context_id,observation_sha256,raw_journal_digest,local_lifecycle_sequence,
                     native_outcome,publication_confirmed) VALUES($1,$2,$3,$4,'UNKNOWN',false)
                    ON CONFLICT(context_id) DO UPDATE SET observation_sha256=EXCLUDED.observation_sha256,
                    raw_journal_digest=EXCLUDED.raw_journal_digest,
                    local_lifecycle_sequence=EXCLUDED.local_lifecycle_sequence""", binding.context_id,
                    checkpoint.observation_sha256,checkpoint.raw_journal_digest,checkpoint.local_lifecycle_sequence)
            if not stale:
                await conn.execute("""/* context_update */ UPDATE collector_metadata_v1.context
                    SET lifecycle_state=$3 WHERE context_id=$1 AND binding_sha256=$2""",
                    binding.context_id,binding.binding_sha256,lifecycle_state)
            result = await self._read(binding)
            _need({item.observation_sha256:item for item in result.observations} == wanted)
            _need(result.checkpoint == (old if stale else checkpoint))
            _need(result.lifecycle_state == (before.lifecycle_state if stale else lifecycle_state))
            return result
