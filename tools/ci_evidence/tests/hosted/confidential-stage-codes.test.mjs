import test from 'node:test';import assert from 'node:assert/strict';
import {verifyOidcSignature} from '../../github_identity.mjs';
import {validatePublicSummary} from '../../public_summary.mjs';
test('failure stage is fixed, public-safe and never reflects input',()=>{
 assert.throws(()=>verifyOidcSignature('secret-path-SID-token',{}),e=>e.code==='E_OIDC_HEADER'&&!e.message.includes('secret-path'));
 const p={schema:1,scope:'SYNTHETIC_HOSTED_ONLY',collectorRepository:'YehorBabenko88/unified-system',workloadRepository:'YehorBabenko88/math',status:'BLOCKED',phase:'STRICT_OIDC_OR_TRANSPORT',code:'E_OIDC_SIGNATURE',nativeAcceptance:'BLOCKED',operationalAcceptance:'UNQUALIFIED',physicalG1:'BLOCKED',production:'NO_GO',bookGate:'CLOSED',q01:'OPEN'};
 assert.equal(validatePublicSummary(p),true);assert.throws(()=>validatePublicSummary({...p,code:'raw-token-value'}),/BLOCKED/);
 assert.throws(()=>validatePublicSummary({...p,token:'raw-token-value'}),/BLOCKED/);
});

test('collector preserves inner fixed authorization failure code without exposing claims',async()=>{
 const {collectorFixture}=await import('./fixtures/context.mjs');const {verifyCollectorWorkload}=await import('../../oidc_request.mjs');const f=collectorFixture();const nonce='c'.repeat(64),challenge={...f.context,nonce,audience:'urn:unified-system:ci-evidence:'+nonce,issuedAt:f.now,expiresAt:f.now+120};
 assert.throws(()=>verifyCollectorWorkload(f.token(challenge,{nbf:f.now-300}),{jwks:f.jwks,platform:f.platform,policy:f.policy,challenge,now:f.now,collectorSha:f.collectorSha,approvedSubjects:f.subjects}),e=>e.code==='E_OIDC_TIME'&&e.message==='Confidential evidence BLOCKED');
});
