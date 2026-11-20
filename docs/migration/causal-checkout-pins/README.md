# Active checkout/cohort consistency

Root29 hosted Windows3.12 job136437548751 correctly refused SOURCE_PIN_MISMATCH: causal workflow downloaded Data105 e1ea525273aa2181e7357ca84a774ac2fb30ced0 while its active cohort had already moved to reviewed Data113a44ce268c39170dfd377b25c75aa3648fcf3476e. Synchronize that checkout; do not weaken SourceFence.

Three source-only controls compare both current workflow source-pin maps to their own qualification cohorts and refuse stale or duplicate checkouts. They are mandatory before the original seven causal CI controls and unchanged21-case installed runner. Demonstrated RED mismatch, then GREEN on Python3.11/3.12. No domain runtime, SDK pin manifest, admission, source guard or case roster is relaxed. Native/full hosted acceptance remains NO_GO.

Independent P2 found that a second SDK checkout with an expression ref was ignored by the static parser. Every declared SDK repository checkout now requires one recognized checkout action, one canonical repository and one literal40hex ref before duplicate detection; expressions/branches/duplicate ref keys refuse. SourceFence remains an independent runtime defense.
