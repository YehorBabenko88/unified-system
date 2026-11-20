# Isolated causal CI fixture paths

Hosted Root186 Windows3.11 job136416151087 failed before the21-case causal runner: isolated unittest discovery exposed only tests/, and TemporaryDirectory used a DOS short-name spelling while the installed CLI resolves its site path.

Declare the owned source root in this test module; resolve the synthetic SDK site just as the real CLI does. No production validator, raw hash, package owner check, expected test inventory or hosted Git fixture is weakened.

Local source-only reproduction: importing the six non-Git cases through isolated discovery failed with ModuleNotFoundError before the change. All same six cases pass on Python3.11 and3.12 after the change with sockets, child processes, ctypes and os.system denied. The seventh real Git fixture remains mandatory hosted and NOT_RUN locally under the Norton restrictions. Hosted full suite/native/installer acceptance remains NO_GO.

Follow-up Windows hosted job136422941699 executed all seven original controls; six passed, and the source-postcheck fixture reached QUALIFICATION_INPUT_OUTSIDE_ROOT because its replacement q.ROOT still used an unresolved DOS short-name base. Resolve every synthetic temporary root before assigning it as the canonical builder ROOT. The original SOURCE_POSTCHECK_FAILED assertion stays unchanged; no production outside-root guard is weakened. Actual Git source fixture passed in that job.
