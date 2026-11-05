# Offline Windows toolchain integrity foundation

`unified_system/windows-toolchain.catalog.json` records five Windows x64 archive
candidates. `unified_system.windows_toolchain` checks only existing local files:
no downloading, extraction, interpreter execution, service/registry/PATH mutation
or installation occurs. The catalog and verifier must themselves be externally
reviewed and pinned before a bootstrap consumer relies on them.

The Python NuGet 3.12.10, Node 22.23.4 and MinGit 2.56.0.4 candidates have exact
SHA256 and byte lengths from independently inspected local files whose bytes
were checked against vendor-published metadata. Their native execution is
`NOT_RUN`. PostgreSQL18.6-5 carries the existing MetaAnalyse
`c108b8c` `scripts/prepare-ci-postgres18.ps1` checksum; NSSM2.24-101-g897c7ad carries
the Chocolatey package's `VERIFICATION` checksum for its upstream archive. These
two archives were not locally available or natively verified. They therefore
have `expected_bytes: null` and a conservative maximum bound, not an invented
exact byte length. Their distinct provenance classifications remain visible.

Each artifact fixes its component/version, HTTPS vendor URL, leaf filename,
SHA256, optional exact byte length, maximum byte count and checksum-provenance
scope. URLs are descriptive policy data; the validator never opens them. Known
components cannot silently disappear from a policy. Required Windows Python
wheel closure and official Consul binary/publisher policy remain explicitly
**unlocked**. There are no placeholder hashes or implied acceptance for either.

## Read-only use

```sh
python -B -m unified_system.windows_toolchain --artifact-dir /absolute/local/artifacts
```

The default catalog is adjacent to the module; `--catalog /absolute/local/file`
can select separately reviewed catalog data. API consumers can call
`validate_artifact_directory(path, catalog=validated_policy)` or use the default.
Neither supplying a policy nor passing its digest authenticates its publisher.
Do not copy catalog hashes from a candidate and interpret that as independent
review or production authorization.

The artifact directory must already exist. The validator reuses the owned
Python lexical namespace/fixed-drive policy before metadata access and the
process driver's ancestor-first symlink/reparse guard. UNC/network drives,
linked ancestors, nonregular files and multiply linked archive leaves cannot
qualify. Fresh `lstat`/`fstat` identity checks surround bounded streaming SHA256
reads; no cached Windows `DirEntry.stat` link counts are used. Unknown directory
files are ignored rather than executed or recursively processed.

The public report contains catalog component/version/filename identifiers and
`BYTES_MATCH`, `MISSING`, `SIZE_MISMATCH`, `DIGEST_MISMATCH` or `UNVERIFIED`, with
no machine paths or raw exceptions. `all_locked_artifacts_match` describes only
archive-byte integrity. `installation_closure` remains false even when all five
archives match, because mandatory wheel and Consul components are still unlocked.
CLI exit 1 means that known incomplete closure; malformed policy/path rejection
exits 2. There is no full-closure PASS or installation success exit. Native
execution, publisher authentication and execution/physical authority are never
inferred from matching bytes.

## Remaining installer work

A staged archive is not a complete installation. A subsequent separately
reviewed boundary must enforce strict archive count/path/link/size rules,
materialize an immutable versioned tree, derive and check individual executable
pins from admitted bytes, and test actual native runtime behavior. It still
needs a locked Windows wheel closure, official Consul artifact/publisher policy,
role-specific PostgreSQL provisioning and hard-fencing/recovery configuration,
least-privilege service setup, enrollment and current signed/fenced rollout
permits, and actual Windows interrupted-install/activation/rollback acceptance.
This foundation authorizes none of those actions and makes no installer-ready,
production-ready or physical acceptance claim. ADMINIT/office execution remains
outside the authorized scope.
