# Exact reusable workflow identity discovery

Observed workload repository is always YehorBabenko88/math. Collector repository is always YehorBabenko88/unified-system. These closed fields are not interchangeable. The collector input pin is Root R1, while sourceSha/workflowSha come from the caller run context and are checked against standard Math workload OIDC claims.

The caller workflow_ref must be YehorBabenko88/math/.github/workflows/confidential-synthetic-e2e.yml@refs/pull/<positive-number>/merge. The reusable job_workflow_ref must be YehorBabenko88/unified-system/.github/workflows/ci-evidence-collector.yml@<R1_SHA>, and job_workflow_sha must equal R1. Root collector R1 is independent of the current Root system SDK/cohort revision.

Expected GITHUB_RUN_ID/ATTEMPT select the exact Math run and attempt. Discovery requires matching repository/event/run/attempt, in_progress status, exactly one PR and exactly one current job from the attempt jobs endpoint. The source commit must match the exact expected merge SHA/tree with two parents: captured PR base then PR head; run.head_sha must match that PR head.

There is NO fixed production job-name string. The single independently read current REST job supplies policy.jobName (string bounded to512 characters); later workload validation additionally requires it nonempty. Its run_id/head_sha/status/check_run_url bind jobId/checkRunId. Later platform verification rechecks the listed/live job name against that captured value and the signature-verified check_run_id. Synthetic fixtures may use qualification / collector, but that string is not a production guard. Math Mnext must retain a one-job collector workflow; adding a second job to that workflow is not silently accepted.

Errors are serialized only through closed stage/code enums. stageCode accepts a recognized own data-property code and does not invoke getters or inherited properties; verifyWorkload always creates a sanitized fixed error, preserving recognized inner stages without forwarding arbitrary native error objects. No message/stack/cause/path/URL/bearer/claim is logged or made public.
