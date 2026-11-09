# A5 additive source composition on ROOT PR59

ROOT source base: `3af06455b601a328e94339327a0597eada802c38`, tree `c5fa79b31a0f12b2db9e1b506edcaa3e48930293`. This is explicitly not an admitted runtime/effect/wire base.

Import exactly 33 previously absent A5-owned files from PR57 `cf08b2d05f853f8c24392467c7690657cba69728`. Each file's source, byte count and SHA256 is recorded in `source-composition-3af0645.json`. These include the closed local job shell, owned suspended worker, pure CPU policy, their tests and specification fixtures. FORMAT_ONLY samples remain unissued data. The imported qualifier script is source only and is not executed by the selected tests. PR52 is not included or executed.

No existing ROOT-base file is changed. In particular A2 identity, A4 storage, ROOT source/security/transport/CI, direct target, UI and integration manifest/ownership files retain exact base bytes. The ROOT manifest SHA256 `3d20438f30fcb2b14661ae2681136d3c27007a5f1bc7f34c062f078a47184236` and ownership SHA256 `767b2dbdb6d4a2560add2f404c05b515a7479fe1fbae400de4295b85ccdf8ef4` were checked from primary Git blobs.

## Verification plan and scope

1. Assert all imported paths were absent from ROOT base and all 33 bytes still equal the declared cf08 primary blobs.
2. Assert every pre-existing base path retains its original blob identity; only these imports and two A5 source-composition documents may be added.
3. Commit on independent `feature/agent5-source-composition-20261109`, then use a fresh raw checkout with no hardlinks and verify all tracked bytes/no extras before and after selected tests.
4. Run all `tests/gateway_jobs/test_*.py`: 41 default local/pure tests, with explicit native preparation NOT_RUN. Run the two existing owned suspended-child cases only under explicit selection; aggregate 43 includes the same 41, not an additional independent population. No ResumeThread, derived CPU setter, CPU workload, qualifier or PR52 invocation.
5. Record exact HEAD/tree/receipt and request separate A8 review. Parent source results and prior PR57 results do not transfer to the new source.

Working composition default run observed 41 PASS, zero skips, and explicit native NOT_RUN. Exact committed-source results are in the external receipt, not inferred from this working run. ROOT's 22 Consul/mTLS and 17 local storage tests were not rerun here and are not part of A5's count.

## Owner ACK and remaining API work

A5 ACK scope: these additive exact-byte imports only. This is not an ACK for positive dispatch, job admission, cancellation effects, native restart reconciliation, resource qualification or storage publication. Source review of the imported A2 profile-v2 API confirms it provides principal sessions/captures only. Actual job/Assignment/quota/worker enrollment/one-use permit methods still require A2 implementation plus explicit shared API coACK. A4 native publication and actual scientific payload READ remain separate gates.

Public submit and `GatewayWorker.start` remain DENY. `admitted_fields=[]`; all six resource dimensions remain unsupported for admission. Local UNKNOWN recovery and local quiescence are not distributed job status, cancellation, hold release or permission. No independent authority, consensus, queue, ledger or publication implementation is introduced. Overall INTEGRATION_PENDING / NO-GO.
