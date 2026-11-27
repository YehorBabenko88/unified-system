# Runner blocker investigation

Confirmed cause: **UNKNOWN**. Six bounded GitHub GETs, no retries/mutations or repeated job polling.

Confirmed facts: public repository with User owner, enabled Actions, all actions allowed, default workflow token read-only. Selected-actions409 explicitly reports all actions/workflows allowed. Zero repository self-hosted runners is not GitHub-hosted inventory and cannot explain standard hosted-label jobs. Organization/enterprise runner-group endpoints are inapplicable to the personal owner; selected workflows do not request groups.

Exact source1d923f6a33e1f0f16cd476f1b4e5e65ee03a8a6c: mandatory and pure-source workflows have no concurrency key and use Ubuntu/Windows standard OS labels. This excludes a concurrency lock defined in these two workflows; it does not prove account capacity or scheduler availability.

One account Actions usage-summary request returned404. Billing availability/permission/restriction is UNKNOWN, not confirmed billing blockage. No amounts or private principals are included in this report.

Earlier exacted4 evidence remains separate: two Windows2025 mandatory jobs completed successfully while Ubuntu and pure-source jobs were unassigned/queued. That establishes some hosted execution occurred, not all hosted capacity. No unchanged jobs were repolled.

Primary semantics: [self-hosted inventory](https://docs.github.com/en/rest/actions/self-hosted-runners#list-self-hosted-runners-for-a-repository), [organization runner groups](https://docs.github.com/en/rest/actions/self-hosted-runner-groups), [user billing usage summary](https://docs.github.com/en/rest/billing/usage#get-billing-usage-summary-for-a-user).
