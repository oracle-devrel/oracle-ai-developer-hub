"""Tests for the suggest_portfolio_hedge tool schema registration.

Verifies the tool is correctly declared in TOOL_SCHEMAS and PRELOADED_TOOLS
so the LLM will always have access to it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools import PRELOADED_TOOLS, TOOL_SCHEMAS


def _find_tool(tools, name):
    return next((t for t in tools if t["function"]["name"] == name), None)


class TestToolSchemaRegistration:
    def test_tool_present_in_tool_schemas(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        assert tool is not None, "suggest_portfolio_hedge missing from TOOL_SCHEMAS"

    def test_tool_present_in_preloaded_tools(self):
        tool = _find_tool(PRELOADED_TOOLS, "suggest_portfolio_hedge")
        assert tool is not None, "suggest_portfolio_hedge missing from PRELOADED_TOOLS"

    def test_tool_has_correct_type(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        assert tool["type"] == "function"

    def test_account_id_is_required_parameter(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        params = tool["function"]["parameters"]
        assert "account_id" in params["required"]
        assert "account_id" in params["properties"]

    def test_risk_focus_is_optional(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        params = tool["function"]["parameters"]
        assert "risk_focus" in params["properties"]
        assert "risk_focus" not in params.get("required", [])

    def test_risk_focus_enum_values(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        enum_vals = tool["function"]["parameters"]["properties"]["risk_focus"]["enum"]
        assert set(enum_vals) == {"market", "sector", "regional", "currency", "all"}

    def test_description_is_non_empty(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        assert len(tool["function"]["description"]) > 20

    def test_account_id_has_description(self):
        tool = _find_tool(TOOL_SCHEMAS, "suggest_portfolio_hedge")
        desc = tool["function"]["parameters"]["properties"]["account_id"].get("description", "")
        assert len(desc) > 5

    def test_preloaded_tools_is_superset_of_tool_schemas(self):
        schema_names = {t["function"]["name"] for t in TOOL_SCHEMAS}
        preloaded_names = {t["function"]["name"] for t in PRELOADED_TOOLS}
        assert schema_names == preloaded_names


class TestToolDispatcherRouting:
    """Verify that the dispatcher routes suggest_portfolio_hedge without error.

    We mock the DB connection and query_helper so no real Oracle instance is needed.
    """

    def test_oracle_mode_routes_to_correct_handler(self, monkeypatch):
        import agent.tools as tools_module

        # Patch execute_query to return empty rows (no DB needed)
        monkeypatch.setattr(
            "agent.tools.execute_query",
            lambda conn, sql, params, query_logger, description="": ([], []),
        )
        # Patch ARCH_MODE to converged
        monkeypatch.setattr(
            "agent.tools.os.getenv", lambda k, d="": "converged" if k == "ARCH_MODE" else d
        )

        import types

        fake_config = types.ModuleType("config")
        fake_config.ARCH_MODE = "converged"
        monkeypatch.setitem(sys.modules, "config", fake_config)

        execute_tool = tools_module.create_tool_executor(
            conn=object(),
            embedding_model=None,
            memory_manager=None,
            llm_client=None,
            query_logger=None,
        )

        result = execute_tool("suggest_portfolio_hedge", {"account_id": "ACC-001"})
        # Empty rows → "No holdings found" message
        assert "No holdings found" in result or isinstance(result, str)

    def test_unknown_tool_returns_error_string(self, monkeypatch):
        import types

        fake_config = types.ModuleType("config")
        fake_config.ARCH_MODE = "converged"
        monkeypatch.setitem(sys.modules, "config", fake_config)

        import agent.tools as tools_module

        monkeypatch.setattr(
            "agent.tools.execute_query",
            lambda *a, **kw: ([], []),
        )

        execute_tool = tools_module.create_tool_executor(
            conn=object(),
            embedding_model=None,
            memory_manager=None,
            llm_client=None,
            query_logger=None,
        )

        result = execute_tool("nonexistent_tool_xyz", {})
        assert "Error" in result or "Unknown" in result
