"""Coordinated release identities and logical ownership, not runtime authority.

Capabilities here describe code ownership. Advertising or installing a module
does not authenticate it or grant deployment, training or execution permission.
Only these four identities participate in active releases. Retired repository
names are not capability aliases or independent services.
"""
from types import MappingProxyType


OWNER_CAPABILITIES = MappingProxyType({
    'unified_system': ('release_orchestration', 'module_compatibility', 'deployment_lifecycle'),
    'market_data': ('market_capture', 'footprint_storage', 'source_dataset_sealing'),
    'math': ('scientific_graph_execution', 'numerical_kernels'),
    'terminan': ('strategy_execution', 'backtesting', 'strategy_training',
                 'research_result_sealing', 'microstructure_analytics',
                 'paper_session_analytics', 'research_presentation', 'fleet_presentation'),
})
MODULE_IDS = frozenset(OWNER_CAPABILITIES)
