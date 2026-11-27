# Canonical read-only control-plane names

This intentional API naming change provides no legacy aliases. Routes, methods, status codes, authority decisions and all test assertions are preserved except the explicitly renamed literals below.

| Previous active name | Canonical name |
|---|---|
| ReadOnlySupervisorApp | ReadOnlyControlPlaneApp |
| supervisor_status capability key | control_plane_status |
| SUPERVISOR_UNAVAILABLE reason | CONTROL_PLANE_UNAVAILABLE |
| INVALID_SUPERVISOR_STATE reason | INVALID_CONTROL_PLANE_STATE |
| test_supervisor_wsgi | test_control_plane_wsgi |
| tests/test_supervisor_terminan_http.py | tests/test_control_plane_consumer_http.py |
| SupervisorConsumerHTTP | ControlPlaneConsumerHTTP |

The HTTP consumer exercises Root's generic read-only status endpoint; it does not contact Terminan. Its loopback body remains unchanged except the application class identifier. Historical source hashes and archived qualification records retain their original names. Separate retirement work owns the four old cross-repository verification scripts and workflows.

Validation: fifteen direct WSGI/compatibility cases on Python 3.11 and 3.12, with socket, child-process, ctypes and SQLite access denied. Five changed Python file ASTs match the original after the explicit name/docstring substitutions; all seventeen test functions remain. The two HTTP tests are preserved and compiled, but not executed locally.
