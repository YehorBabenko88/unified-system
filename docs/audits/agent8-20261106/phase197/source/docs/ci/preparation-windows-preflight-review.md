# Preparation Windows Git preflight correction

Source-only repair based on clean Root96b17905a5be923857aa1e778085eaeec6f0f27f. Original Windows job130055333038 stopped at the inline ordinary-Git condition before Scheduler tests. The original log does not identify which conjunct failed or provide the selected file's metadata. Do not relabel that original run PASS or infer its exact hosted filesystem condition from LS5.

Read-only LS5 comparison found C:/Program Files/Git/cmd/git.exe nlink2 and C:/Program Files/Git/bin/git.exe nlink1. Both are43352bytes with SHA25678211c7ed73988da93a6d8a33d47ec6187f464d7ea2a9a00c182bbd7a1ecf30f. No Git file or installation was modified and neither executable was launched by this comparison.

The workflow's two bootstrap sites and the qualifier now explicitly select C:/Program Files/Git/bin/git.exe on Windows, /usr/bin/git on Ubuntu. There is no PATH lookup, fallback or relaxation of ordinary-file, single-link, ancestor, symlink/reparse, external-root or executable-mode checks. Existing no-replacement/no-optional-lock/fsmonitor-disabled arguments remain. Git bytes are read only after absolute/external, root-first ordinary ancestry, selected-file/single-link/executable and64MiB gates pass. Unsafe ancestry stops traversal before selected-file inspection and leaves raw_sha256 null; all execution gates still apply.

The runner-path binding step creates its new external QUALIFICATION_BASE and writes bootstrap.json before subsequent source/Git checks. Both inline sites preserve stage-specific Git preflight JSON before refusal or spawn: selected absolute path, raw SHA256 where safely readable, file mode/device/inode/linkcount/size/timestamps/attributes/symlink observation, ancestor observations/errors and passed=false. The driver's Git preflight similarly persists under its external evidence directory. Passing the path preflight does not qualify source, dependency, tests or runtime. Existing always-upload evidence artifact handling is retained.

TDD evidence: two added pure controls produced original RED11 with one selector assertion failure and one missing evidence-API error; after minimal implementation all11pure controls passed0skip in0.157s. The new metadata control also retains hardlink refusal using only owned inert temporary files, with subprocess launch forbidden. Static workflow Python blocks compile; external evidence creation precedes Git checks. No actual qualifier/main, Scheduler36, tempSQLite, crash child, socket, native, provider or office fixture was executed. The old30 inventory, six integrity IDs, mandatory36 gate, original crash command, existing workflows and all source outside the four allocated paths are untouched. Pure-control count9→11 is explicit.

Preserved local evidence directory: C:/Users/LS-5/.codex/preparation-win-preflight-evidence-20261110.

| Original evidence | SHA256 |
| --- | --- |
| red-11.txt | d164f81562e6e2af5749ebb4959628ea2a40917b9b719bbc13ebdf8b2ba02992 |
| final-green-11.txt | 75a7cf2808d6fbca6bb994c95ab7174352b181b09852f940a74f5893ab66c964 |
| local-git-readonly-stat.json | b9fe81133374f2062d2cf000410be1b1bd030793a318bd715bfb44ce7e01132b |

This repair is prepared for Draft source review. No dispatch, rerun, cancellation, inventory waiver, workflow removal, Windows/hosted PASS, native/runtime/physical admission or policy change is claimed. New-source hosted qualification uses the existing authorized CI cohort; original failures remain immutable.


Independent-review correction: the first diagnostic implementation inspected/hashed the selected file before validating its ancestors. This was a new preflight regression, not a defect attributed to the original hosted source. A new pure mocked-reparse-parent control reproduced selected-file traversal before rejection (unsafe-parent-red-12.txt). Corrected helper and both inline clones validate ancestors root-first and stop below the first unsafe parent; metadata persists passed=false/file=null/raw_sha256=null. The test forbids selected-file lstat/read_bytes and subprocess launch. The existing repository-local and hardlink controls now also require null diagnostic hashes on refusal. Twelve pure controls pass0skip in0.144s (unsafe-parent-green-12.txt). No actual qualifier or Scheduler fixtures were executed after this correction.
