# Original final-component obligation binding

Source-only metadata custody; runtime qualification remains NO_GO.

The independent baseline is the published Root commit 035ad06fbe7cc15fd4ab1f40a7029afe9cf8fbdf, path docs/qualification/root-components-20261120/groups.json, Git blob 44e237868ac857a6c47279a8e5405d69cae74704. Its raw SHA-256 is fa337c890ebd33b65cccfc577b70b41a120d974bbd14fb1cef9e0934e1176fda. The canonical payload SHA-256 is 5ca6f840a1e645d48a05e63adb29974f74f332f63fbca4f3b3edae615a4c391a.

The payload is exactly the source final group's expected_ids (161) and preserved_prior_ids (145), encoded with Python json.dumps(sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False), ASCII. Array order is preserved. The digest is a code constant, never a value supplied by the mutable manifest. Historical raw bytes, all original/current arrays, 13 translations and current 162-role inventory are unchanged.

Before set/sort/hash work, the reader bounds manifest input to 1 MiB, each ID list to 4096 entries, each literal string to 2048 characters and aggregate ID text to 262144 characters. These are representation budgets, not claims of functional coverage.

Independent coupled substitution of a non-registry ID in all four old/current arrays was accepted before this repair on Python 3.11/3.12; it is now refused even if the caller supplies a matching self-computed digest. Wrong hardcoded pin and oversized input calibrations also refuse. Original 43 pure tests pass on both versions under socket/subprocess/ctypes/SQLite denial. No actual discovery, SourceFence, native process or runtime admission was performed.

Evidence: outputs/root-component-ledger-binding-1795213961478 (original baseline bytes, RED/GREEN probes, all 12 suite logs).
