# Historical coordination audit verifier

The six-owner v1 coordination baseline is historical preparation evidence. Its immutable snapshots and thirteen original safety tests are retained, while its verifier is removed from the active `unified_system` package.

| Previous | Current historical audit location |
|---|---|
| unified_system/integration_registry.py | scripts/historical_registry.py |
| tests/test_integration_registry.py | tests/test_historical_registry.py |
| tests/test_integration_registry_gate.py | tests/test_historical_registry_gate.py |
| .github/workflows/integration-registry.yml | .github/workflows/historical-registry.yml |

The verifier bytes, original thirteen test bodies, result refusal expression, source pre/post checks and historical contracts remain unchanged. Only imports, workflow/test paths and descriptive workflow identity move. There is no old runtime import alias. This audit never admits current modules, installation, trading or deployment; the canonical four-owner cohort and SourceFence remain separate. Native/SourceFence execution is not part of local validation. NO_GO.
