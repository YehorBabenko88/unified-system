# Round 6 E — read-only bridge and dependent lifecycle check

**Candidate / not accepted:** E draft PR #164, strictly LAB_SIMULATION,
against B source `f57781a947af138a2099bebe553b89c3c5ee726e`, C #163
`dc60465385c8201254efd94c36049ecdbcec59c1`,
D #126 `fb64be03dda72307bed4be4b25e5d51242882769`.
The live source SHAs of other PRs can advance independently; do not silently
relabel this fixed cohort.

New `unified_system/grid_writer_lab_bridge.py` imports the existing Root
`ConsulSessionAuthority`, source `StartupSourceAdmission` protocol and
C-owned `lab_pg_fence` owner APIs (passed by the caller); no second Consul
client, SQL implementation, process killer, paper engine or HTTP endpoint.

Its `assess_lab_c_fence` is **diagnostic and non-actuating**. It requires
a LAB-only Consul authority and exact owned lease object, source grant
that remains current, a separate old-worker quiescence witness, an owned
C LAB PG instance and a C catalogue witness confirming direct writer
INSERT disabled. It checks positive actual postmaster PID, not the
`None` sentinel. It independently hashes exact source bytes under
the admitted source root and manifest for four B modules using C's
`SHA256(relative ASCII path + NUL + bytes + NUL)` algorithm; schema SHA
is the SHA256 of Grid `grid/migrations.py` bytes. Both must match E's
`WriterLeaseIdentity`, alongside owner/namespace/Consul session/token
and generation. It rechecks source grant and Consul lease at the end.
Returning `LabFenceAssessment(native_admitted=False)` cannot grant
native startup and does not invoke `claim_lab_fence` or any SQL write.

**Unresolved trust boundary:** a synthetic process quiescence object can
satisfy this isolated assessment; the API therefore can never authorize
real service startup. Real Windows SCM/Job process extinction, shutdown
of legacy unmanaged Grid WS/REST and old loopback listener, Root live
Consul authority, C's single resource-side claim/revoke and backend
connection, native credential wiring and a restart/epoch revocation
protocol still require an independently approved native admission
adapter. Existing `native_writer_admission` **always DENIES**.

`lab_runtime.require_v2_terminan_dependency` now rejects protected v2
LAB configurations where Terminan does not explicitly depend on
`market_data`. The existing `RuntimeSupervisor.tick` stops declared
dependents if market_data becomes unready; this is a polling-time
lifecycle property, NOT continuous secure epoch revocation. D's HTTP
bearer+source pre/post admission must still refuse stale capability.
Legacy Strattester capsules are unchanged.

New E isolated tests cover lease/source/manifest/digest/PostgreSQL witness
mismatches, no SQL claim side effects and the dependency stop cascade.
They use synthetic source bytes, fake Consul and fake PG:
**not native PostgreSQL18 E2E, production owner proof or Windows tests**.
The dedicated six-cell E workflow uses the repository's existing
hash-pinned unittest dependency lock; it does not trigger a rerun
of unchanged queued workflows. Await exact HEAD CI and independently
executed C/B native PG18 lanes. No real provider/exchange authenticity,
completeness or paper/trading capability is asserted.

**CODE NO_GO / PRODUCTION NO_GO.**

## C Round-6 owner-side readback revalidation (post initial design)

C [#163](https://github.com/YehorBabenko88/unified-system/pull/163)
introduced `revalidate_lab_fence(pg, identity, generation, backend_pid)`.
The E read-only bridge now **requires** that exact C API and strictly compares
its full 21-field `lab-postgres-fence-revalidation.v1` receipt against E's
typed `WriterLeaseIdentity`, exact C backend PID, current generation, active
PostgreSQL backend start identity, and source/schema digests. It also requires
the receipt to declare `native_writer_admitted=false` and to **NOT** claim
Root Consul or host process proof. Stale/revoked DB generation and a receipt
forged to grant native execution are rejected. C remains the only SQL owner:
the bridge never claims/releases a writer and has no database write.
