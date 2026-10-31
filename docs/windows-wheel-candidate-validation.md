# Offline Windows wheel candidate validation

`unified_system.windows_wheels` validates an explicitly supplied compiled lock
and an already existing local wheel directory. It performs no network requests,
package installation/import, extraction, subprocess execution or filesystem
writes. The lock, validator and input provenance must be independently reviewed
and pinned by their caller. Matching a lock does not authenticate its publisher.

```sh
python -B -m unified_system.windows_wheels \
  --lock /absolute/local/windows-cp312-cpu-candidate.lock \
  --wheel-dir /absolute/local/wheels
```

The API is `validate_windows_wheels(lock_path, wheel_dir)`. It returns a closed
public report with `CANDIDATE_BYTES_MATCH` or `BLOCKED`; CLI exit 0 means only the
former candidate-byte result. Every report keeps `dependency_closure_verified`,
`installation_closure`, `publisher_authenticated` and `execution_authority`
**false**, and native execution/physical activity `NOT_RUN`. This is not an
installer, dependency resolver or production readiness gate.

## Accepted inputs

The lock grammar is deliberately narrow: canonicalizable distribution names
pinned with `==` to one explicit version, followed by one or more lowercase
`--hash=sha256:<64 hex>` values. Standalone comments and backslash continuations
from the compiled UV lock are supported. Duplicate distributions/hashes,
unpinned constraints, extras, environment markers, URLs, index options, includes
and other pip directives are rejected. Inputs are bounded to 4 MiB, 512
packages, 4,096 hashes per package and bounded line/logical-record sizes. This
parser does not interpret PEP508 expressions or repeat the resolver's work.

The directory must contain exactly one wheel per pinned distribution, matching
its explicit version, and no extras, subdirectories or sdists. Distribution
names normalize runs of `-`, `_` and `.` case-insensitively. Version strings must
agree exactly across the lock, filename, dist-info directory and METADATA;
unsupported version aliases fail closed rather than being guessed. Platform
metadata is checked for a conservative CPython3.12 Windows AMD64 subset:
CP312 native ABI, compatible Python3 stable ABI versions through CP312, and
Python3 `none` ABI wheels for `any` or `win_amd64`. Universal `py2.py3-none-any`
is accepted only with its Python3 tag. Other native ABIs, later CPython
versions, Win32, ARM and non-Windows platforms cannot qualify.

Existing Root guards reject external/mapped namespaces and inspect path
ancestors before touching descendants. Archive leaves must be fresh-stat unique
regular files. The validator streams SHA256 and then reads ZIP/METADATA/WHEEL
through **the same open file descriptor**. Pre/post file and path identities
must agree, so replacing a pathname between hashing and inspection cannot
substitute another archive. No cached Windows DirEntry link counts are used.

Each wheel is at most 1 GiB, with at most 2 GiB of input across the directory.
Before constructing ZipFile, the validator bounds the EOCD/central directory
and rejects spanning/unsupported ZIP64 directory forms. Limits include 20,000
entries, a 16 MiB central directory, 512 MiB per expanded member and 2 GiB
expanded data per wheel. Only two metadata members are decompressed, each at
most 1 MiB; payload files are never extracted or evaluated. Archive paths reject
traversal, Windows device names, absolute/drive paths, backslashes, control or
non-ASCII names, trailing aliases, duplicate case-folded paths, file/directory
conflicts, encrypted entries, symlinks and reparse attributes. Accepted
compression is stored or deflated. Conservative limits can reject an otherwise
valid wheel; they must not be loosened merely to obtain a passing report.

Nested vendored `.dist-info` trees (for example setuptools `_vendor` data)
remain ordinary safe archive members and cannot supply authoritative metadata.
A `.data/purelib` or `.data/platlib` remap directly introducing another top-level
`.dist-info` is rejected; this is not a general installation-layout proof.
There must be exactly one top-level dist-info identity with unambiguous
METADATA `Name`, `Version`, `Metadata-Version` and WHEEL version/purity fields.
WHEEL tags must equal the expanded filename tags and satisfy the target subset.
Duplicate or conflicting metadata is rejected. Metadata parsing does not
resolve `Requires-Dist`, attest native DLL availability, or run package code.

## Candidate status and remaining work

The initial downloaded candidate was not complete: the manual inputs omitted
Strattester's selected-extra `pytest-json-report` requirement. Recompile from
actual reviewed source requirements and selected extras, retain their source
hashes/resolver inputs, and use the resulting new lock and complete wheel set.
The validator does not hardcode a candidate package count and cannot infer
whether an omitted source requirement should have been present.

After review, validate those final candidate bytes. A real isolated native
Windows offline install with hashes and no indexes, followed by `pip check`,
actual imports, native DLL/runtime checks and application acceptance remains
mandatory. Resolver markers/extras, transitive dependency satisfaction, CPU
backend selection and installed package behavior require that separate evidence.
Consul/toolchain publisher admission, signed six-module release closure,
enrollment/permits, PostgreSQL/service provisioning and physical acceptance are
also separate blockers. No ADMINIT/office action or installation authority is
provided by this validator.
