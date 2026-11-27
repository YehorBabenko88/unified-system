# Math caller handoff after Root tool R1

Publish Root tool commit R1 first. Math Mnext invokes YehorBabenko88/unified-system/.github/workflows/ci-evidence-collector.yml@<R1_SHA> with collector-sha:<R1_SHA>. Both caller and callee require contents:read, actions:read and id-token:write. Keep Math pull_request source/merge/run/job/subject and same-repository guards.

R1 is Root collector code, not the Math workload or current Root SDK revision. A later Root system cohort may pin Mnext; R1 stays immutable with no self-reference.

Three original Math caller/isolation roles remain held: immutable least-privilege caller; no additional issuer request while an intentionally held qualification is unresolved; unrelated/native workflow isolation for the constrained qualification lane. Map these to canonical Mnext policy before deleting old Math files/workflows. They are not claimed completed by Root inert tests.

Twenty original auth/storage/signature/ZIP/privacy roles are ported as hosted-only tests; three loader roles map to Root static controls. No local positive OIDC, PKI or SQLite qualification has run.
