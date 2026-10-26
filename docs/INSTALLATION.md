# Installation plan, not an installer
This release only validates an offline lockfile and returns a **DRY_RUN_ONLY** plan. It never creates services, modifies PostgreSQL, touches ACL/firewall, downloads executables, writes files or starts modules.

A production installer must separately establish publisher authenticity, trust anchors, immutable release artifacts, dependency closure, explicit owner authorization, privilege separation, atomic staging, reversible migration policy and physical acceptance. SHA256 alone proves byte equality against the supplied lock, not trust in the lock.

No deployment or G1 operations are authorized.
