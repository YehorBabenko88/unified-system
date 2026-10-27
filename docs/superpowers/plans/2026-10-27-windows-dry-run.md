# Windows dry-run implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task.

**Goal:** Implement workstream D as specified in docs/CODEX_WORKSTREAMS.md.
**Architecture:** Offline detached CMS signature over exact UTF-8 manifest bytes, with an explicitly supplied SHA256 certificate pin. Validate identity, bounded artifacts, local paths, reparse points and ACLs before returning a plan. Never install or mutate inputs.
**Tech Stack:** Windows PowerShell 5.1/7, .NET SignedCms, dependency-free assertions.
**Spec:** docs/CODEX_WORKSTREAMS.md at 50e6e63cb183f6dcf1dee3c753f966717ee3b110.

## Global constraints
No service, DB, network, installation or ACL mutations. Only disposable test temp may be written. No G0/G1/live trading. Independent branch from frozen integration PR1, never push its source branch.

## Review focus
Reject unsigned/tampered/incorrectly pinned manifests; reject wrong SID; reject traversal/ADS/UNC/reparse paths; reject untrusted writable ACLs; never confuse signature validity with deployment admission.

### Task 1: Offline verifier and negative tests
Files: scripts/WindowsDryRun.psm1, tests/windows/Test-WindowsDryRun.ps1.
Interface: Test-UnifiedDryRun -Root -Manifest -Signature -PublisherSha256 -ExpectedIdentitySid returns DRY_RUN_ONLY, otherwise throws.
- [ ] Write disposable signed fixture and assertions for signature, pin, identity, traversal, reparse and ACL negatives, and unchanged input snapshots.
- [ ] Run tests and observe missing-module failure.
- [ ] Implement strict local verifier and document offline trust and race limitations.
- [ ] Run PowerShell 5.1 and 7 tests plus existing Python suite.
- [ ] Add Windows CI matrix, commit, push own branch and create Draft PR; capture exact-head CI receipts without merging.
