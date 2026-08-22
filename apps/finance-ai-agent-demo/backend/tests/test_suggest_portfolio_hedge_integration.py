"""Integration-style tests for _suggest_portfolio_hedge.

These tests call _suggest_portfolio_hedge directly with a mock DB connection
that returns controlled row data — no real Oracle instance required.
The goal is to verify the full pipeline: SQL execution → row parsing →
_build_hedge_recommendations → JSON output.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Minimal mock connection and execute_query that return fixture rows
# ---------------------------------------------------------------------------


class MockQueryLogger:
    def __init__(self):
        self.calls = []

    def log(self, *args, **kwargs):
        self.calls.append((args, kwargs))


def make_execute_query_stub(rows):
    """Return a drop-in for execute_query that yields `rows` with column names."""
    columns = [
        "ROW_TYPE",
        "ID",
        "LABEL",
        "TICKER",
        "SECTOR",
        "REGION",
        "ASSET_CLASS",
        "RISK_RATING",
        "PCT",
        "RISK_PROFILE",
        "ESG_MANDATE",
        "MAX_POSITION",
        "EXCLUDED_SECTORS",
    ]

    def _execute_query(conn, sql, params, query_logger, description=""):
        # Convert dict rows to tuples matching column order
        tuple_rows = [tuple(r.get(c) for c in columns) for r in rows]
        return tuple_rows, columns

    return _execute_query


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSuggestPortfolioHedgeOutput:
    def test_returns_valid_json_string(self, tech_heavy_rows, monkeypatch):
        import agent.tools as tools_module

        monkeypatch.setattr("agent.tools.execute_query", make_execute_query_stub(tech_heavy_rows))

        result_str = tools_module._suggest_portfolio_hedge(
            conn=object(),
            args={"account_id": "ACC-001", "risk_focus": "all"},
            query_logger=MockQueryLogger(),
        )
        result = json.loads(result_str)
        assert isinstance(result, dict)

    def test_result_contains_hedge_recommendations(self, tech_heavy_rows, monkeypatch):
        import agent.tools as tools_module

        monkeypatch.setattr("agent.tools.execute_query", make_execute_query_stub(tech_heavy_rows))

        result = json.loads(
            tools_module._suggest_portfolio_hedge(
                conn=object(),
                args={"account_id": "ACC-001", "risk_focus": "all"},
                query_logger=MockQueryLogger(),
            )
        )
        assert len(result["hedge_recommendations"]) > 0

    def test_no_holdings_returns_error_message(self, monkeypatch):
        import agent.tools as tools_module

        monkeypatch.setattr("agent.tools.execute_query", make_execute_query_stub([]))

        result = tools_module._suggest_portfolio_hedge(
            conn=object(),
            args={"account_id": "ACC-999"},
            query_logger=MockQueryLogger(),
        )
        assert "No holdings found" in result
        assert "ACC-999" in result

    def test_default_risk_focus_is_all(self, tech_heavy_rows, monkeypatch):
        import agent.tools as tools_module

        monkeypatch.setattr("agent.tools.execute_query", make_execute_query_stub(tech_heavy_rows))

        # Omit risk_focus — should default to 'all'
        result = json.loads(
            tools_module._suggest_portfolio_hedge(
                conn=object(),
                args={"account_id": "ACC-001"},
                query_logger=MockQueryLogger(),
            )
        )
        assert result["risk_focus"] == "all"

    def test_query_logger_is_called(self, tech_heavy_rows, monkeypatch):
        import agent.tools as tools_module

        logger = MockQueryLogger()
        called = []

        def _stub(conn, sql, params, query_logger, description=""):
            called.append(description)
            columns = [
                "ROW_TYPE",
                "ID",
                "LABEL",
                "TICKER",
                "SECTOR",
                "REGION",
                "ASSET_CLASS",
                "RISK_RATING",
                "PCT",
                "RISK_PROFILE",
                "ESG_MANDATE",
                "MAX_POSITION",
                "EXCLUDED_SECTORS",
            ]
            return [tuple(r.get(c) for c in columns) for r in tech_heavy_rows], columns

        monkeypatch.setattr("agent.tools.execute_query", _stub)
        tools_module._suggest_portfolio_hedge(
            conn=object(),
            args={"account_id": "ACC-001"},
            query_logger=logger,
        )
        assert any("ACC-001" in d for d in called)

    def test_esg_portfolio_excludes_leveraged_products(self, esg_rows, monkeypatch):
        import agent.tools as tools_module

        monkeypatch.setattr("agent.tools.execute_query", make_execute_query_stub(esg_rows))

        result = json.loads(
            tools_module._suggest_portfolio_hedge(
                conn=object(),
                args={"account_id": "ACC-ESG", "risk_focus": "all"},
                query_logger=MockQueryLogger(),
            )
        )
        rec_tickers = [r["ticker"] for r in result["hedge_recommendations"]]
        assert "SQQQ" not in rec_tickers

    def test_market_focus_filters_non_market_dimensions(self, tech_heavy_rows, monkeypatch):
        import agent.tools as tools_module

        monkeypatch.setattr("agent.tools.execute_query", make_execute_query_stub(tech_heavy_rows))

        result = json.loads(
            tools_module._suggest_portfolio_hedge(
                conn=object(),
                args={"account_id": "ACC-001", "risk_focus": "market"},
                query_logger=MockQueryLogger(),
            )
        )
        dims = {r["hedge_dimension"] for r in result["hedge_recommendations"]}
        assert dims <= {"market"}

    def test_account_id_in_params_passed_to_sql(self, tech_heavy_rows, monkeypatch):
        import agent.tools as tools_module

        received_params = {}

        def _stub(conn, sql, params, query_logger, description=""):
            received_params.update(params)
            columns = [
                "ROW_TYPE",
                "ID",
                "LABEL",
                "TICKER",
                "SECTOR",
                "REGION",
                "ASSET_CLASS",
                "RISK_RATING",
                "PCT",
                "RISK_PROFILE",
                "ESG_MANDATE",
                "MAX_POSITION",
                "EXCLUDED_SECTORS",
            ]
            return [tuple(r.get(c) for c in columns) for r in tech_heavy_rows], columns

        monkeypatch.setattr("agent.tools.execute_query", _stub)
        tools_module._suggest_portfolio_hedge(
            conn=object(),
            args={"account_id": "ACC-007"},
            query_logger=MockQueryLogger(),
        )
        assert received_params.get("account_id") == "ACC-007"
