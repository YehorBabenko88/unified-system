# Root035 retained CI bootstrap repair

Base: 035ad06fbe7cc15fd4ab1f40a7029afe9cf8fbdf. No runtime/cohort/source-admission changes.

Four retained discovery workflow callers use -I -S -B with a fresh external cache and explicit dependency path, without site startup. scripts/ci_unittest.py remains unchanged. Missing httpx/pytest entries copy the exact approved operator-command lock closure; Windows colorama hashes come from the approved Windows candidate lock. No local installs.

tests/__init__.py supplies a tracked origin. SourceFence admission is unchanged. Owner-boundary SDK refs derive from the same frozen cohort.json already enforced by its qualifier, replacing obsolete literals without changing that cohort.

The hosted preparation crash role preserves timeout20, os._exit(23), and four recovery assertions. Closed phase markers distinguish startup/import/open/prepare/crash hook; they do not establish the cause of the observed Windows timeout.

Local proof: eight new inert controls and ten unchanged operator helper controls on Python3.11/3.12, with child/socket/ctypes/SQLite/system effects denied. Actual crash process, SourceFence, PKI, services and broad native discovery NOT_RUN locally. Existing managed-runtime NO_GO remains. Three additional Windows native15s timeouts remain unqualified. No timeout increased or mandatory role removed.
