# Mux artifact-only upload repair

Historical run44815204899 at Root035ad06fbe7cc15fd4ab1f40a7029afe9cf8fbdf printed scoped worker success on both OS axes: unit33, real72, Root2072 raw files and Grid58cfe0f51bc05bb0ee2ed09368a9b64679358c63 raw672. The job then failed upload because .lab-evidence is hidden and upload-artifact excludes hidden files by default. These historical observations do not qualify the current canonical runtime.

Upload now explicitly names only three reviewed JSON files and enables hidden inclusion for those literal paths: source-bound.json, source-guard-controls.json, reconciliation-review2-models.json. The first retains exact33/72 executed IDs plus raw source path/hash maps and NO_GO/no-native-auth scope. The others retain8 source-guard case IDs and24 fixed model cases. No directory glob, raw logs, real-consul.json, scratch repositories, certificates, keys or tokens are uploaded by this step. Missing reports remain an error.

The worker, native tests, source pins, mandatory33/72 gate and NO_GO are unchanged. Two pure source-only allowlist controls run with socket/child/ctypes/SQLite/system denied; native worker and hosted upload are NOT_RUN locally. New hosted evidence is still required.
