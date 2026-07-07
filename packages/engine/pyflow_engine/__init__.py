"""Pyflow execution engine — pure-Python core with no web dependency.

The engine parses a workflow DAG, schedules it, executes each tool on a
backend-neutral Frame (Polars in Phase 0), and emits run events.
"""
from __future__ import annotations

from .document import WorkflowDoc
from .registry import ToolRegistry, build_default_registry
from .runner import Runner

__all__ = ["WorkflowDoc", "Runner", "ToolRegistry", "build_default_registry", "__version__"]

__version__ = "0.0.1"
