# Physical acceptance plan — NOT AUTHORIZED

PHYSICAL_ACCEPTANCE = BLOCKED / NO-GO. All office fault injection is prohibited until separate owner approval of an exact phase plan. Estimates are not promises; complete historical duration depends on measured source bytes, quotas and available history.

|Phase|Scenario|Risk|Estimated time|
|---|---|---|---|
|P01|Read-only office baseline and recovery access|LOW|5-10 min|
|P02|Admitted isolated LAB capsule on one selected node|MEDIUM|10-20 min|
|P03|Six-node authenticated endpoints and current registry|MEDIUM|10-15 min|
|P04|Ten-instrument bounded historical pilot|MEDIUM|15-30 min pilot; full history ETA from measured bytes/source coverage|
|P05|600-second live public data and paper execution|MEDIUM|10 min capture + 5 min verification|
|P06|Terminan relocation and concurrent authorized windows|MEDIUM|10-20 min|
|P07|Owned worker stop/reassign/rejoin|HIGH|5-10 min|
|P08|LS5 owned coordinator process failure|HIGH|5-10 min|
|P09|PC4 coordinator process failure after full recovery|HIGH|5-10 min|
|P10|PC3 coordinator process failure after full recovery|HIGH|5-10 min|
|P11|Loss of two owned voters / no quorum|HIGH|5-10 min|
|P12|Replica corruption on copied disposable fixture only|HIGH|10-15 min|
|P13|Disk pressure on separately approved disposable test volume|HIGH|10-20 min|
|P14|Actual backup and isolated restore|MEDIUM|20-40 min for bounded fixture|
|P15|Schedule transition including DST / coordinator duty protection|MEDIUM|10-20 min plus offline DST vectors|
|P16|Bounded network-degradation simulation|MEDIUM|10-20 min|
|P17|Owned update and rollback|HIGH|10-20 min per selected node|
|P18|Windows restart per separately selected host|HIGH|10-25 min per host|
|P19|Controlled Tailscale-independence test|HIGH|10-20 min pilot then approved node sequence|
|P20|Safe uninstall preparation only|LOW|5-10 min|

Detailed prerequisites, abort conditions, recovery and evidence are in physical-acceptance-plan.json. All scenarios are NOT_RUN. No automatic Tailscale retirement, router change, reboot, purge or security-policy change is authorized. Isolated source/harness tests are separate from this plan.
