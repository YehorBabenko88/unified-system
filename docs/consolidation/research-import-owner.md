# Research-import validation ownership

The pure research record validator belongs to Terminan. Root SDK integration now calls `terminan.research_import.validate_research_import`, while Root independently inspects digest/pin evidence through `inspect_historical_receipt`; independent source admission remains unavailable. Data no longer needs a research-result validator or research-import HTTP endpoint once the paired Data migration is accepted.

The original Root receiver test, acceptance/refusal/forgery assertions and case ID are preserved; only the owner import and function name change. The new Terminan API grants no execution, trading, source authentication or native authority. No legacy Data alias or runtime forwarding adapter is introduced. Current source cohorts must be frozen and qualified together before release. NO_GO.
