// Auditor-owned counterexamples for exact Terminan Sync source. No real transport.
const assert=require('node:assert/strict');const path=require('node:path');const fs=require('node:fs');const cp=require('node:child_process');const crypto=require('node:crypto');
const source=path.resolve(process.argv[2]);const head=process.argv[3]||'166b85e888d7d0ade24bd945761ad501a94e060c';
const git=(...args)=>cp.execFileSync('git',['-C',source,...args]);assert.equal(git('rev-parse','HEAD').toString().trim(),head);
const files={};for(const name of ['terminan/sync/protocol.js','terminan/sync/client.js','tests/sync/fixtures.cjs']){const actual=fs.readFileSync(path.join(source,name));assert.deepEqual(actual,git('show',head+':'+name));files[name]=crypto.createHash('sha256').update(actual).digest('hex');}
const P=require(path.join(source,'terminan/sync/protocol.js'));const {SyncClient}=require(path.join(source,'terminan/sync/client.js'));const F=require(path.join(source,'tests/sync/fixtures.cjs'));
(async()=>{
 const clock=F.clock();const s=new P.SyncState({clock:()=>clock.now(),validateDomain:()=>true});
 s.install(F.controlWithDataset());s.connection(true);assert.equal(s.status,'LIVE');
 const ds=F.datasetSnapshot();ds.authority_status.state='NO_QUORUM';s.install(ds);
 const dataset={case:'dataset_snapshot_noquorum',expected:'NO_QUORUM',actual:s.status,authority:s.authority,canMutate:s.canMutate};
 let subscriptions=0,closes=0;const t=F.clock();
 const adapter={getSnapshot:async()=>F.snapshot(),subscribe(options){subscriptions++;options.onError({code:'UNAVAILABLE'});return()=>{closes++;};}};
 const client=new SyncClient({adapter,clock:()=>t.now(),random:()=>0,validateDomain:()=>true});
 await client.start();const statusAfterFailure=client.state.status;t.advance(1001);await client.tick();
 const sync={case:'synchronous_subscribe_failure',expected:'NOT_LIVE_AND_RETRY',actual:statusAfterFailure,status_after_retry_deadline:client.state.status,connected:client.state.connected,subscriptions,closed_before_stop:closes};
 client.stop();
 const failures=[dataset,sync];console.log(JSON.stringify({head,files,scope:'SYNTHETIC_COMPONENT_COUNTEREXAMPLES_ONLY',failures,physical:'BLOCKED',authority:'COMMAND_UNAVAILABLE'},null,2));
 process.exitCode=dataset.actual==='NO_QUORUM'&&sync.actual!=='LIVE'&&subscriptions>1?0:1;
})().catch(e=>{console.error(e);process.exitCode=2;});
