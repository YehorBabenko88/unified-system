"""Local fail-closed job preparation. No owner backend, authority or registry.

The local intent is NOT an approved shared submission/cancellation wire codec.
No callback/provider binding or positive execution path is implemented.
"""
from dataclasses import dataclass
import hashlib
import json
import re
import uuid
from .intelligence_gateway import decode, prepare_research_plan, GatewayInvalid


class JobInvalid(ValueError):
    pass


@dataclass(frozen=True)
class LocalOriginal:
    """Untrusted immutable local retry identity, never an authority proof."""
    raw: bytes
    request_id: str
    idempotency_key: str
    sha256: str


class JobUnavailable(RuntimeError):
    def __init__(self, original=None):
        super().__init__('JOB_OWNER_CONTRACTS_UNAVAILABLE')
        self.original = original
        self.outcome = 'UNKNOWN'


def prepare_intent(raw):
    """Strict local preparation only; no job ID, caller identity or admission."""
    try:
        value = decode(raw)
        if type(value) is not dict or set(value) != {'schema','request_id','idempotency_key','plan'}:
            raise ValueError
        if value['schema'] != 'unified.gateway.job-local-preparation.v1':
            raise ValueError
        request_id = value['request_id']
        if type(request_id) is not str:
            raise ValueError
        parsed = uuid.UUID(request_id)
        if parsed.version != 4 or str(parsed) != request_id:
            raise ValueError
        key = value['idempotency_key']
        if type(key) is not str or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key) is None:
            raise ValueError
        prepare_research_plan(value['plan'])
        canonical = json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
        if raw != canonical:
            raise ValueError
        return LocalOriginal(raw,request_id,key,hashlib.sha256(raw).hexdigest())
    except (GatewayInvalid, ValueError, TypeError, KeyError, AttributeError):
        raise JobInvalid('INVALID_LOCAL_JOB_PREPARATION') from None


class ResearchJobs:
    """Unbound composition shell. No owner object is called or accepted."""
    async def submit(self, original_request_bytes, *, context):
        original = prepare_intent(original_request_bytes)
        return dict(status='NOT_SUBMITTED',request_id=original.request_id,
                    intent_sha256=original.sha256,job_id=None,effects_authorized=False,
                    reason='JOB_OWNER_CONTRACTS_UNAVAILABLE')

    async def lookup(self, original_request_bytes, *, context):
        raise JobUnavailable(prepare_intent(original_request_bytes))

    async def reconnect(self, original_request_bytes, *, context):
        raise JobUnavailable(prepare_intent(original_request_bytes))

    async def status(self, job_id, *, context):
        # No registry or status visibility contract. No fabricated job observation.
        raise JobUnavailable()

    async def cancel(self, original_cancel_bytes, *, context):
        # A NEW cancel command needs a separate exact co-approved codec.
        # Do not interpret submission/local preparation as cancellation authority.
        raise JobUnavailable()
