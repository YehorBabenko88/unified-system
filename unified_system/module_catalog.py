"""Coordinated release identities and logical ownership, not runtime authority.

Capabilities here describe code ownership. Advertising or installing a module
does not authenticate it or grant deployment, training or execution permission.
The older lifecycle/status wire schema is migrated independently.
"""
from types import MappingProxyType


OWNER_CAPABILITIES = MappingProxyType({
    'unified-system': ('release_orchestration', 'module_compatibility', 'deployment_lifecycle'),
    'grid': ('market_capture', 'footprint_storage', 'source_dataset_sealing'),
    'strattester': ('strategy_execution', 'backtesting', 'strategy_training', 'research_result_sealing'),
    'math': ('scientific_graph_execution', 'numerical_kernels'),
    'meta_analyse': ('microstructure_analytics', 'paper_session_analytics'),
    'terminan': ('research_presentation', 'fleet_presentation'),
})
MODULE_IDS = frozenset(OWNER_CAPABILITIES)
