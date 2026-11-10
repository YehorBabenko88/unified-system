# Exact ed4 CI observation

Bounded observation: 10 GETs; no retries or mutations. Original JSON, successful-job logs and artifact ZIPs retained privately.

- Pure-source PR run 42721792598: Ubuntu job129517288707 and Windows job129517289007 QUEUED, runner_id=0, empty runner and steps, null conclusions.
- Mandatory PR run42721792637: Windows2025 job129517289049 SUCCESS (23:37:30–23:38:08Z); Ubuntu job129517288550 QUEUED/unassigned/no steps.
- Mandatory push run42721780126: Windows2025 job129517241158 SUCCESS (23:36:14–23:37:04Z); Ubuntu job129517241491 QUEUED/unassigned/no steps.

Each completed Windows job has original-log proof of7 gate regression tests passing, plus artifact proof of16 distinct mandatory composed tests, no errors/failures/skips/expected failures/unexpected successes. Both artifact ZIP digests match GitHub and source before/after matches exact ed4 and all4 bound repositories. Status PASS_SYNTHETIC_CAUSAL_COMPOSITION_ONLY. No FAILURE observed in this selected scope; no failure logs fetched. Queued started_at values do not prove work executed. Queue root cause UNKNOWN; no full matrix/physical qualification.
