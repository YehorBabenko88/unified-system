# Owned async synthetic Collector lifecycle v1

Source implementation on Root cffef63aa557627fc125e66d6ee5703d679fdd45/treec2fb242b808a240d16954bb0906f37d68331299c, approved approach B. Exactly three new files; existing offline/profile/Grid Worker/Agent5/storage contracts unchanged. Prior902 results are not rewritten or transferred.

## API and ownership

`CollectorAsyncSession(profile, *, manifest_bytes, frames, context, log, observed_at_ms)`, then synchronous `start()`, `await wait()` or `await stop()`. Construction checks pure input/profile limits. start on the caller's running default loop accepts ownership of actual CollectorContext/CollectorLog, creates retained retirement first, receive/preflight second and deadline timer third. No custom loop, thread/executor, source admission, queue, storage or provider runtime is introduced. Context/log must already have been created/opened by their existing owner with externally admitted source/runtime and NEW owned paths.

A preflight task uses actual public context APIs and reads bounded existing owner markers only to match context/store/manifest/log limits. These marker comparisons do not establish authority; owner APIs perform their existing validation. It validates retained history/digests/source/instrument and context-total observation/payload budgets before constructing one actual Worker and RawCaptureRecorder. Fresh empty history has no checkpoint; only nonempty history requests it.

At most four frames,1MiB UTF8 per frame,4MiB total and120seconds per profile; exact integer limits and existing log bounds apply. The finite tuple is the bounded feed: sequential raw-before-parse writes give backpressure without another queue or producer. The sink delegates to actual A4 store_capture with scheduling yields before and after; this is scheduling, not asynchronous disk I/O. Current A4 SQLite/ObjectStore work is synchronous behind async signatures and cannot be cancelled halfway by ordinary loop scheduling.

## Outcome and retirement

An event-loop-local first-wins NORMAL/ABORT latch selects normal only after receive and acknowledged final disconnect. Direct monotonic deadline comparison occurs before selection, so starved timer dispatch cannot manufacture success. Once NORMAL is latched a later stop joins that normal retirement. Deadline overrun during later cleanup is recorded independently and yields UNKNOWN; it cannot undo persisted STOPPED.

Stop before start consumes the session without transferring ownership. Wait before start and repeated start reject. Every method binds to the same loop. Active stop/cancel/deadline selects ABORT and joins actual receive/delegated operation before close. A single retained retirement task is shield-observed by all waiters; repeated waiter cancellation continues observation until finished and then propagates cancellation with any primary/cleanup failures. Timer requests abort and returns, never awaits its own retirement join.

Task creation failure after ownership transfer remains owned. If first retirement creation fails, no receive/I/O exists and owners close synchronously. Later creation failure signals retained retirement; caller must observe wait/stop even when start raises. Unsubmitted coroutine is closed. No automatic restart/recreation/replay or replacement of resources.

Normal retirement verifies actual history/digests/gaps/checkpoint, calls public stop, records lifecycle before closing, then closes context/log. Abort does not call clean stop; existing public close of ACTIVE persists UNKNOWN after operation retirement. Existing UNKNOWN/TERMINAL are retained. Close persistence/FD/I/O-inflight errors remain explicit; no durableUNKNOWN or resource-closure claim follows a failed close. A normal persisted STOPPED followed by log-close error yields retirementUNKNOWN with persistedSTOPPED, not invented storageUNKNOWN. Expected receive cancellation preserves existing Worker disconnect-uncertainty notes in the receipt. Original primary and cleanup exceptions remain retained; failed retirement is never silently reported clean.

Results are LOCAL_UNATTESTED/SYNTHETIC only. Task retirement, persisted lifecycle and resource closure are separate facts. Provider continuity/power-loss durability/native outcome remain UNKNOWN. No publication, native authority, service, physical or provider acceptance follows.

## Test separation and source binding

`PureAsyncRules` explicitly selects actual pure function bodies through AST; it does not import/execute session/asyncio/Grid/Storage. Its initial five cases have actual retained RED5 missing-source then GREEN5 evidence; a sixth counter-scope regression has actual RED1/GREEN6 evidence. This only proves frame limits and pure latch/deadline rules.

`AsyncLifecycleE2E` is NOT_RUN pending a distinct Root/A8 exact source/runtime/effect allocation. External harness must supply `scratch_parent`, prospective `manifest_bytes`, and `source_map_sha256`. Manifest metadata must declare `async_test_provenance={scope:PROSPECTIVE_TEST_ONLY_NOT_ADMISSION,actual_application_map_sha256:...}` bound to actual new application source maps collected by the external custodian. Existing902 manifest673 is not a valid claim for currentcff+newfiles. The manifest's actual A3 revision must bind approved Grid3bf; existing Agent5dec4 is not invoked by this direct path. Supplied metadata is a test input, never Root source admission. The later integration manifest is a separately agreed artifact; no shared manifest is edited here.

E2E cases use actual Worker/Recorder/context/store/log, bounded test-only suspending delegation and public real-class ACK-loss interception. No fake loop/Worker/Journal/facts. They test scheduling/backpressure, active stop, repeated waiter cancellation, real frame and final-disconnect write ACK loss, retained history/gaps after clean reopen, task creation failures, starved timer, and persistedSTOPPED/log-close uncertainty. ACK loss models are not physical partial-write/crash evidence. Actual corruption/PG/process-crash qualification remains separate.

## Default loop and effects review required before execution

Developer harness uses one stock asyncio.Runner/default loop per explicit case and retains its reference until close. Windows Proactor initialization creates self-pipe/socketpair and IOCP via stdlib native extensions; fallback socketpair may perform bounded ephemeral loopback bind/listen/connect/accept. No zero-socket/zero-WinAPI claim, fake loop_factory or old blanket guard bypass is allowed. External/provider/HTTP/WS/PG sockets, service listeners, executors/threads and protected runtime remain prohibited.

Harness records joined task outcomes/no pending tasks/no unexpected loop errors plus observed Python control socket fileno=-1, loop.is_closed and proactor IOCP field cleared after Runner.close. Those are observed runtime facts, not universal native handle/process-family closure or hard deadline proof. Root/A8 must review exact whole-runtime/native dependency pins and control-IPC effects plus outer custody before ONE software allocation. Current91 loop/socket/DLL DENY grants nothing here. Runner/native close may block: supervisor retains UNKNOWN rather than treating a cancelled Task or requested cleanup budget as physical I/O retirement.

Allowed own-state effects on later approved run include actual disposable A4 SQLite/ObjectStore/log files and retained test artifacts. No SQL, loop, IOCP or native extension execution has been allocated by merely publishing this source.

## Agent5 boundary and rollback

Do not nest session around existing run_offline. Existing _bind_worker uses to_thread and is outside the first no-thread envelope. Later joint API must retain A5parent Job/process/context custody, child Runner/loop ownership, A3session receive/retirement/context/log ownership and Root admission. Abort-stop is not NSSM graceful drain; never wire it directly to C3 service stop. Task/context result is not A4 parent whole-Job/I/O inspection proof.

Rollback retains source branch/evidence and leaves old path unchanged; no history deletion or state reset. No push/dispatch/install/provider/credentials/service/production change is part of this implementation. Overall NO-GO.


Receipt counter scope: input_frames_supplied/input_bytes_supplied always describe the accepted finite input tuple. raw_frames_received/raw_received_bytes are populated only when actual Worker.receive_offline returned; they remain null (UNKNOWN) after incomplete/partial receive or preflight/task-creation failure. Supplied bytes are never labeled as confirmed receive progress.

## Supported storage profile restriction (source review correction)

Own adapter SupportedProfileID is `unified.collector.async-storage.fixed.v1`; it is not a new A4 schema, authority or capacity reservation. Only this full existing public marker profile is supported, with exact closed dict keys and every scalar exact int (no bool, float or subclass): raw_profile={max_observations:16,max_payload_occurrence_bytes:4194304,max_state_bytes:16777216,sqlite_headroom_bytes:262144,inventory_file_limit:128}, lifecycle_headroom_bytes=65536,max_lifecycle_records=128,max_context_bytes=16777216. Narrower or otherwise different valid A4 profiles are rejected; support is not silently derived or widened.

A4's existing public require_ready() returns None and validates the actual owner's exact canonical marker, profile and identities. Under the caller's already required exclusive namespace custody the adapter calls it, reads at most8192 bytes from context.root/collector-owned.json with duplicate/nonfinite/float rejection, checks closed outer schema unified.storage.collector-context.v1 and context/store/binding/root plus the full fixed profile, then calls require_ready() again before Worker/factory/raw writes. No private _profile/_marker/Journal read, callerTrue, DTO proof or new A4 API is used. The bracket itself is not ABA protection or authority independent of external custody. If that custody is absent, this path is BLOCKED. Ownership has already transferred, so preflight rejection may write UNKNOWN during existing-owner cleanup; it is not zero filesystem effects.

This rejects unsupported profiles before Worker/raw writes, not a promise that the full batch can fit the lifecycle journal. require_ready reserves one operation only; repeated no-op reopens can leave insufficient lifecycle records despite the fixed maximum. Existing per-operation capacity failure and UNKNOWN/cleanup uncertainty remain explicit, partial history retained, no retry/reset/replay or false STOPPED/quiescence. Whole-batch lifecycle reservation would require a separately agreed A4 public contract and is not implemented here.

The seventh pure profile restriction regression has actual retained RED1 before helper implementation; the new actual narrow-context E2E case remains NOT_RUN. The immutable first source candidate1cf is preserved; only the three owned new files are corrected in a successor, without changing A4/shared code or reinterpreting its previous reviews. Runtime/defaultloop/SQL execution still requires separate Root/A8 allocation.

## Runner harness custody correction (source-only)

The E2E harness now covers Runner construction, get_loop, observation setup and body under one ownership try/finally. Once Runner exists it attempts close even when initialization or setup fails. Primary/body and cleanup failures are retained together in BaseExceptionGroup; close failure does not suppress the original error or prevent the observation record. An unsubmitted fresh coroutine is closed; a suspended body is not closed as a substitute for actual I/O retirement. Initialization/close/fact-acquisition failures produce explicit UNKNOWN observations; unknown loop/proactor facts are null and partial socket observations remain partial. No closed fact is asserted without observation. Missing control-socket/proactor snapshots prevent successful retirement acceptance.

InertRunnerControls AST-selects the actual run_owned method, substituting only its asyncio import in a local execution scope with inert fault objects. It does not change sys.modules, global import policy, default loop or any native runtime. Four original controls actually failed against the pre-fix method, then passed; six final controls cover constructor/get_loop/setup/body-only/close-only/combined-primary-close failure. These are semantic fault controls, not FakeLoop/default-loop/IOCP/handle/runtime PASS. The seventeen real E2E methods/eighteen default-loop lifetimes remain NOT_RUN until a distinct allocation. The prior cbb source7 evidence is preserved with its original pins, not relabeled as a runtime result.
