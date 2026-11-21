# Root CI evidence implementation plan

Goal: transfer the unique twelve-file CI evidence infrastructure to Root without widening authority.
Architecture: one Root tool closure, independently pinned from its Math workload; private CI vault distinct from app stores. Spec: DESIGN.md. Implementation runs inline per parent ownership assignment.

1. RED: inert tests for closed phase mapping, fail-before-later-effects, secret-sentinel redaction and cleanup.
2. Port exact reviewed modules with canonical relative imports; archive original bytes/test roles. Preserve guards and add initialization stage callbacks.
3. GREEN: pure diagnostic/orchestration code only; syntax-check remaining modules without importing collector/SQLite/PKI.
4. Reusable Root workflow: closed raw hash loader, exact Root collector identity, Math workload binding, least-privilege permissions. No self-referential commit constant.
5. Static closure/source/role parity and inert controls; independent review; freeze/publish R1. Hand off exact R1 pin to Math caller. Live auth/native remains NOT_RUN until hosted proof.
