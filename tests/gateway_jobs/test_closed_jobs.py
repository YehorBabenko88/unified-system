"""No-binding local tests only: no owner fixture, grant or native PASS."""
import asyncio
import hashlib
import json
import runpy
import unittest
from pathlib import Path
from unified_system.gateway_jobs import ResearchJobs, JobUnavailable, JobInvalid, prepare_intent

plan = runpy.run_path(str(Path(__file__).parents[1] / 'test_intelligence_gateway.py'))['plan']

def raw(**changes):
    value = dict(schema='unified.gateway.job-local-preparation.v1',
                 request_id='11111111-1111-4111-8111-111111111111',
                 idempotency_key='local-original-key', plan=plan())
    value.update(changes)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')

class ClosedJobs(unittest.IsolatedAsyncioTestCase):
    async def test_no_binding_never_submits_even_claimed_context(self):
        for context in (None, True, {'role':'ADMIN','approved':True}, object()):
            r=await ResearchJobs().submit(raw(),context=context)
            self.assertEqual(r['status'],'NOT_SUBMITTED')
            self.assertIsNone(r['job_id']);self.assertFalse(r['effects_authorized'])
            self.assertEqual(r['request_id'],'11111111-1111-4111-8111-111111111111')

    async def test_lookup_and_reconnect_unknown_preserve_exact_original(self):
        b=raw()
        for name in ('lookup','reconnect'):
            with self.assertRaises(JobUnavailable) as raised:
                await getattr(ResearchJobs(),name)(b,context=None)
            e=raised.exception
            self.assertEqual(e.outcome,'UNKNOWN')
            self.assertEqual(e.original.raw,b)
            self.assertEqual(e.original.sha256,hashlib.sha256(b).hexdigest())
            self.assertEqual(e.original.idempotency_key,'local-original-key')

    async def test_cancel_has_no_supported_codec_or_effective_cancellation(self):
        with self.assertRaises(JobUnavailable) as raised:
            await ResearchJobs().cancel(raw(),context={'owner':'admin'})
        self.assertIsNone(raised.exception.original)
        self.assertEqual(raised.exception.outcome,'UNKNOWN')

    async def test_status_is_unavailable_not_fabricated_registry(self):
        with self.assertRaises(JobUnavailable):
            await ResearchJobs().status('11111111-1111-4111-8111-111111111111',context=None)

    def test_strict_local_intent_rejects_unapproved_fields_and_identity(self):
        for b in (raw(owner='admin'),raw(request_id='11111111-1111-4111-8111-111111111111\n'),
                  raw(idempotency_key='x\n'),raw(schema='production.v1'), b'{"a":1,"a":2}',
                  b' '*32769, raw()+b' ', raw(plan={})):
            with self.subTest(raw=b[:50]),self.assertRaises(JobInvalid):prepare_intent(b)

    def test_identity_is_immutable_local_data_not_authority(self):
        original=prepare_intent(raw())
        with self.assertRaises(AttributeError):original.request_id='replacement'
        self.assertEqual(original.raw,raw())

    def test_no_backend_injection_constructor(self):
        with self.assertRaises(TypeError):ResearchJobs(owner_bindings=lambda:True)
