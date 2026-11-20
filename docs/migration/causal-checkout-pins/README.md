# Checkout commits from the qualification cohort

Root29 hosted Windows3.12 job136437548751 correctly refused SOURCE_PIN_MISMATCH: causal workflow downloaded Data105 while its active qualification cohort requires reviewed Data113. Both active SDK workflows now emit checkout refs directly from their own qualification cohort.json, the same values consumed by SourceFence. The helper accepts only the three canonical repositories and literal40hex commits; output cannot inject extra GitHub output records. Root checkout stays event-HEAD pinned.

Original seven causal CI controls,21installed cases, all workflow jobs/axes and SourceFence remain unchanged. No separate static YAML-parsing acceptance claim is made. Existing independent static-parser findings are retained in PR history, and the temporary parser introduced by this PR is removed. No earlier domain/regression test is removed.

Local verification reads both actual cohort files and emitted commits with isolated Python3.11/3.12. Hosted source admission and full currentHEAD Windows/Linux qualification remain required. NO_GO.
