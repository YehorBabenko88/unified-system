"""Agent G: offline source-only retirement/migration gate; never an activation authority.

The contract is deliberately specific to the historic Grid strategy runtime.
It consumes explicit source text supplied by the auditor, not ambient imports,
GitHub network, database, services or live credentials. PASS means the tested
legacy capability remains present, NOT that it has been safely retired.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Mapping

SOURCE_HEAD = "165aa614cf6f79d451eac2faa48d6084fbd03d31"
LEGACY = ("grid/strategy_runner.py", "grid/strategy_executor.py",
          "grid/strategy_runtime.py", "grid/ml_process_supervisor.py",
          "grid/strategy_jobs.py", "grid/strategy_plugins.py")
DENY = "RETIREMENT_BLOCKED"


@dataclass(frozen=True)
class Decision:
    status: str
    reasons: tuple[str, ...]
    release_authorized: bool = False
    deletion_authorized: bool = False

    def __post_init__(self):
        if self.release_authorized or self.deletion_authorized:
            raise ValueError("source-only retirement gate cannot authorize releases or deletion")


def _imports(tree: ast.AST, name: str, symbol: str) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level != 1 or node.module != name:
            continue
        if any(alias.name == symbol for alias in node.names):
            return True
    return False


def _calls(tree: ast.AST, function: str) -> bool:
    return any(isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name)
               and node.func.id == function
               for node in ast.walk(tree))


def _has_async_def(tree: ast.AST, name: str) -> bool:
    return any(isinstance(n, ast.AsyncFunctionDef) and n.name == name
               for n in ast.walk(tree))


def _literal_strategy_module(tree: ast.AST) -> bool:
    # This is a positive legacy-custody check, never a proof of no other dynamic imports.
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            values = node.elts
            if any(isinstance(v, ast.Constant) and v.value == "-m" for v in values) and any(
                isinstance(v, ast.Constant) and v.value == "grid.strategy_runtime" for v in values
            ):
                return True
    return False


def assess_legacy_strategy_boundary(
    sources: Mapping[str, str], *, source_head: str
) -> Decision:
    """Fail closed if exact pinned source and original consumer chain are not proven."""
    reasons = []
    if source_head != SOURCE_HEAD:
        reasons.append("SOURCE_PIN_MISMATCH")
    if type(sources) is not dict:
        reasons.append("SOURCE_MAP_UNVERIFIED")
        return Decision(DENY, tuple(reasons))
    trees = {}
    for path in LEGACY:
        content = sources.get(path)
        if not isinstance(content, str) or not content.strip():
            reasons.append("MISSING_SOURCE:" + path)
            continue
        try:
            trees[path] = ast.parse(content, filename=path)
        except SyntaxError:
            reasons.append("SYNTAX_INVALID:" + path)
    if len(trees) != len(LEGACY):
        return Decision(DENY, tuple(reasons))
    checks = (
        ("RUNNER_EXECUTOR_IMPORT", _imports(trees["grid/strategy_runner.py"],
                                            "strategy_executor", "execute_job_subprocess")),
        ("RUNNER_EXECUTION_CALL", _calls(trees["grid/strategy_runner.py"],
                                         "execute_job_subprocess")),
        ("EXECUTOR_SUPERVISOR_IMPORT", _imports(trees["grid/strategy_executor.py"],
                                                "ml_process_supervisor", "run_supervised_process")),
        ("EXECUTOR_SUPERVISOR_CALL", _calls(trees["grid/strategy_executor.py"],
                                            "run_supervised_process")),
        ("EXECUTOR_MODULE_LAUNCH", _literal_strategy_module(
            trees["grid/strategy_executor.py"])),
        ("RUNTIME_ENTRY", _has_async_def(trees["grid/strategy_runtime.py"], "main")),
        ("RUNTIME_DATABASE", _calls(trees["grid/strategy_runtime.py"], "create_pool")),
        ("SUPERVISOR_ENTRY", _has_async_def(
            trees["grid/ml_process_supervisor.py"], "run_supervised_process")),
        ("STRATEGY_JOBS_SCHEMA", any(
            isinstance(n, ast.AsyncFunctionDef) and n.name == "ensure_strategy_schema"
            for n in ast.walk(trees["grid/strategy_jobs.py"]))),
        ("STRATEGY_PLUGIN_REGISTRY", any(
            isinstance(n, ast.AsyncFunctionDef) and n.name == "get_plugin"
            for n in ast.walk(trees["grid/strategy_plugins.py"]))),
    )
    for name, matched in checks:
        if not matched:
            reasons.append("LEGACY_CHAIN_UNVERIFIED:" + name)
    if reasons:
        return Decision(DENY, tuple(reasons))
    return Decision(DENY, ("ACTIVE_LEGACY_CONSUMER_CHAIN", "CANONICAL_TERMINAN_CUTOVER_NOT_PROVEN",
                            "WIN_LINUX_IMPORT_AND_INSTALLER_PARITY_NOT_PROVEN",
                            "OWNER_B_D_H_I_F_ACK_NOT_PROVEN"))
