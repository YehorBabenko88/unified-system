# Canonical managed source boundary

Source identity is exactly unified_system, market_data, math, terminan. Application dispatch accepts only market_data.cli main(["serve"], startup_admission=source) and terminan.server main(["--host", "127.0.0.1", "--port", port], startup_admission=source). The original owned-Python argv, manifest source roots, loopback health URL and data port are checked before application imports.

Canonical market-data authentication and data-first operational handoff remain unported. Runtime admission deliberately refuses ACTIVATION_MARKET_DATA_AUTH_UNPORTED before dropping privileges, opening databases or starting programs. Data-first profiles refuse ACTIVATION_DATA_FIRST_UNPORTED. Historical Grid authentication is not adopted. Raw entry ownership/hash/revocation checks remain mandatory. This source migration grants no operational readiness.

Validation: 25 selected pure tests on CPython 3.11 and 3.12 with an audit hook refusing all subprocess.Popen and os.system events; canonical admission, dispatcher argv, private grant/revocation and protected runtime ordering covered with fakes. Raw entry/native tests, installation, services and sockets were not executed under the security pause. No tests were disabled. The wider inherited installer fixture cohort requires coordinated canonical capsule updates and must not be represented by this scoped result.

Managed service registration must repin service_entry.py exact Git bytes after integration. service_entry.py embeds the exact LF service_bootstrap.py digest; explicit Git attributes preserve those bytes across checkouts. Release artifacts must be exported from committed Git blobs.
