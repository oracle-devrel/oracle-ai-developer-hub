"""Oracle Viz MCP - a minimal, visualization-first MCP server for Oracle AI Database."""

from importlib import import_module

__version__ = "0.1.0"

__all__ = ["config", "mcp", "__version__"]


def __getattr__(name: str):
    """Keep app exports lazy so the CLI can report invalid configuration safely."""
    if name in {"config", "mcp"}:
        return getattr(import_module("oraviz_mcp.server"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
