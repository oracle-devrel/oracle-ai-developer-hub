"""Unit tests for the hedge recommendation engine (_build_hedge_recommendations).

All tests run without a database connection — they call the pure-Python
recommendation logic directly with pre-built row fixtures.
"""

import json
import os
import sys

# Ensure the backend package root is on the path so imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.tools import _build_hedge_recommendations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def tickers(recommendations):
    return [r["ticker"] for r in recommendations]


def dimensions(recommendations):
    return {r["hedge_dimension"] for r in recommendations}


# ---------------------------------------------------------------------------
# Output structure
# ---------------------------------------------------------------------------


class TestOutputStructure:
    def test_returns_dict_with_required_keys(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        for key in (
            "account_id",
            "risk_profile",
            "esg_mandate",
            "risk_focus",
            "portfolio_summary",
            "risk_factors_identified",
            "hedge_recommendations",
            "disclaimer",
        ):
            assert key in result, f"Missing key: {key}"

    def test_account_id_preserved(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-042", "all")
        assert result["account_id"] == "ACC-042"

    def test_risk_focus_preserved(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "sector")
        assert result["risk_focus"] == "sector"

    def test_portfolio_summary_contains_breakdowns(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        summary = result["portfolio_summary"]
        assert isinstance(summary["sector_breakdown"], list)
        assert isinstance(summary["region_breakdown"], list)
        assert isinstance(summary["asset_class_breakdown"], list)
        assert summary["total_holdings"] == 6
        assert summary["high_risk_positions"] == 2

    def test_disclaimer_present_and_non_empty(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        assert len(result["disclaimer"]) > 20

    def test_recommendations_are_list(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        assert isinstance(result["hedge_recommendations"], list)

    def test_each_recommendation_has_required_fields(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        for rec in result["hedge_recommendations"]:
            for field in (
                "ticker",
                "name",
                "type",
                "rationale",
                "risk_level",
                "hedge_dimension",
                "trigger",
            ):
                assert field in rec, f"Recommendation missing field: {field}"

    def test_no_duplicate_tickers(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        seen = [r["ticker"] for r in result["hedge_recommendations"]]
        assert len(seen) == len(set(seen)), f"Duplicate tickers found: {seen}"

    def test_json_serialisable(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        # Should not raise
        json.dumps(result)


# ---------------------------------------------------------------------------
# Market risk detection
# ---------------------------------------------------------------------------


class TestMarketRiskDetection:
    def test_equity_heavy_triggers_market_risk_factor(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "market")
        assert any("equity" in f.lower() for f in result["risk_factors_identified"])

    def test_market_hedge_instruments_included_for_equity_heavy(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "market")
        t = tickers(result["hedge_recommendations"])
        # At least one of the core market hedges must appear
        assert any(tk in t for tk in ("SH", "GLD", "TLT")), f"No market hedge found: {t}"

    def test_high_risk_positions_trigger_market_risk_factor(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "market")
        assert any("high-risk" in f.lower() for f in result["risk_factors_identified"])

    def test_high_risk_positions_trigger_gold_recommendation(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "market")
        assert "GLD" in tickers(result["hedge_recommendations"])

    def test_balanced_portfolio_no_market_risk_factor(self, balanced_rows):
        result = _build_hedge_recommendations(balanced_rows, "ACC-001", "market")
        # Equity is only 60% — below the 60% threshold, no market risk factor
        assert not any("equity" in f.lower() for f in result["risk_factors_identified"])

    def test_market_focus_only_returns_market_dimension(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "market")
        dims = dimensions(result["hedge_recommendations"])
        assert dims <= {"market"}, f"Unexpected dimensions: {dims}"


# ---------------------------------------------------------------------------
# Sector risk detection
# ---------------------------------------------------------------------------


class TestSectorRiskDetection:
    def test_tech_overweight_triggers_sector_risk_factor(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "sector")
        assert any("technology" in f.lower() for f in result["risk_factors_identified"])

    def test_tech_overweight_triggers_tech_hedges(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "sector")
        # Tech hedges include PUT (QQQ puts) or REK
        t = tickers(result["hedge_recommendations"])
        assert any(tk in t for tk in ("PUT", "REK", "VXUS")), f"No sector hedge found: {t}"

    def test_balanced_portfolio_no_sector_risk_factor(self, balanced_rows):
        result = _build_hedge_recommendations(balanced_rows, "ACC-001", "sector")
        # No sector > 30%, so no sector risk factor expected
        assert not any("sector" in f.lower() or "%" in f for f in result["risk_factors_identified"])

    def test_sector_focus_only_returns_sector_dimension(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "sector")
        dims = dimensions(result["hedge_recommendations"])
        assert dims <= {"sector"}, f"Unexpected dimensions: {dims}"


# ---------------------------------------------------------------------------
# Regional risk detection
# ---------------------------------------------------------------------------


class TestRegionalRiskDetection:
    def test_na_heavy_triggers_regional_risk_factor(self, tech_heavy_rows):
        # North America is 65% — above the 50% threshold
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "regional")
        assert any("north america" in f.lower() for f in result["risk_factors_identified"])

    def test_na_heavy_triggers_geographic_diversification_hedge(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "regional")
        t = tickers(result["hedge_recommendations"])
        assert any(tk in t for tk in ("EFA", "ACWX")), f"No regional hedge found: {t}"

    def test_balanced_no_regional_risk_factor(self, balanced_rows):
        result = _build_hedge_recommendations(balanced_rows, "ACC-001", "regional")
        # No region > 50% in balanced_rows
        assert not result["risk_factors_identified"]

    def test_regional_focus_only_returns_regional_dimension(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "regional")
        dims = dimensions(result["hedge_recommendations"])
        assert dims <= {"regional"}, f"Unexpected dimensions: {dims}"


# ---------------------------------------------------------------------------
# Currency risk detection
# ---------------------------------------------------------------------------


class TestCurrencyRiskDetection:
    def test_intl_heavy_triggers_currency_risk_factor(self, intl_heavy_rows):
        result = _build_hedge_recommendations(intl_heavy_rows, "ACC-001", "currency")
        assert any(
            "fx" in f.lower() or "international" in f.lower()
            for f in result["risk_factors_identified"]
        )

    def test_intl_heavy_includes_currency_hedge_instruments(self, intl_heavy_rows):
        result = _build_hedge_recommendations(intl_heavy_rows, "ACC-001", "currency")
        t = tickers(result["hedge_recommendations"])
        assert any(tk in t for tk in ("UUP", "FXE")), f"No currency hedge found: {t}"

    def test_na_only_no_currency_risk(self, esg_rows):
        # esg_rows is 100% North America
        result = _build_hedge_recommendations(esg_rows, "ACC-001", "currency")
        assert not result["risk_factors_identified"]

    def test_currency_focus_only_returns_currency_dimension(self, intl_heavy_rows):
        result = _build_hedge_recommendations(intl_heavy_rows, "ACC-001", "currency")
        dims = dimensions(result["hedge_recommendations"])
        assert dims <= {"currency"}, f"Unexpected dimensions: {dims}"


# ---------------------------------------------------------------------------
# ESG mandate filtering
# ---------------------------------------------------------------------------


class TestEsgMandateFiltering:
    def test_esg_mandate_detected_from_rows(self, esg_rows):
        result = _build_hedge_recommendations(esg_rows, "ACC-001", "all")
        assert result["esg_mandate"] is True

    def test_no_esg_mandate_when_field_absent(self, tech_heavy_rows):
        # tech_heavy_rows have esg_mandate=None
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        assert result["esg_mandate"] is False

    def test_esg_filters_out_sqqq(self, esg_rows):
        # Energy is 70% — triggers market risk; SQQQ should be absent for ESG accounts
        result = _build_hedge_recommendations(esg_rows, "ACC-001", "market")
        assert "SQQQ" not in tickers(result["hedge_recommendations"])

    def test_esg_filters_high_risk_level_sector_hedges(self, esg_rows):
        # Sector hedges with risk_level='high' should be excluded for ESG accounts
        result = _build_hedge_recommendations(esg_rows, "ACC-001", "sector")
        for rec in result["hedge_recommendations"]:
            assert rec["risk_level"] != "high", (
                f"High-risk instrument {rec['ticker']} slipped through ESG filter"
            )


# ---------------------------------------------------------------------------
# risk_focus scoping
# ---------------------------------------------------------------------------


class TestRiskFocusScoping:
    def test_all_can_return_multiple_dimensions(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "all")
        dims = dimensions(result["hedge_recommendations"])
        # With tech_heavy_rows, at minimum market + sector + regional should fire
        assert len(dims) >= 2, f"Expected multiple dimensions, got: {dims}"

    def test_market_focus_excludes_sector_dimension(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "market")
        assert "sector" not in dimensions(result["hedge_recommendations"])

    def test_sector_focus_excludes_market_dimension(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "sector")
        assert "market" not in dimensions(result["hedge_recommendations"])

    def test_regional_focus_excludes_market_dimension(self, tech_heavy_rows):
        result = _build_hedge_recommendations(tech_heavy_rows, "ACC-001", "regional")
        assert "market" not in dimensions(result["hedge_recommendations"])

    def test_currency_focus_excludes_sector_dimension(self, intl_heavy_rows):
        result = _build_hedge_recommendations(intl_heavy_rows, "ACC-001", "currency")
        assert "sector" not in dimensions(result["hedge_recommendations"])


# ---------------------------------------------------------------------------
# Empty / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_rows_returns_no_risk_factors_or_recommendations(self):
        # No holdings at all — _suggest_portfolio_hedge would catch this upstream,
        # but _build_hedge_recommendations should handle gracefully
        result = _build_hedge_recommendations([], "ACC-999", "all")
        assert result["risk_factors_identified"] == []
        assert result["hedge_recommendations"] == []

    def test_none_pct_values_do_not_crash(self):
        rows = [
            {
                "ROW_TYPE": "HOLDING",
                "ID": "H001",
                "LABEL": "Foo",
                "TICKER": "FOO",
                "SECTOR": "Technology",
                "REGION": "North America",
                "ASSET_CLASS": "Equity",
                "RISK_RATING": 5,
                "PCT": None,
                "RISK_PROFILE": "moderate",
                "ESG_MANDATE": None,
                "MAX_POSITION": "0.10",
                "EXCLUDED_SECTORS": "[]",
            },
            {
                "ROW_TYPE": "ASSET_CLASS",
                "ID": "Equity",
                "LABEL": "Equity",
                "TICKER": None,
                "SECTOR": None,
                "REGION": None,
                "ASSET_CLASS": None,
                "RISK_RATING": None,
                "PCT": None,
                "RISK_PROFILE": None,
                "ESG_MANDATE": None,
                "MAX_POSITION": None,
                "EXCLUDED_SECTORS": None,
            },
        ]
        # Should not raise even with None PCT values
        result = _build_hedge_recommendations(rows, "ACC-999", "all")
        assert isinstance(result, dict)

    def test_malformed_excluded_sectors_does_not_crash(self):
        rows = [
            {
                "ROW_TYPE": "HOLDING",
                "ID": "H001",
                "LABEL": "Foo",
                "TICKER": "FOO",
                "SECTOR": "Technology",
                "REGION": "North America",
                "ASSET_CLASS": "Equity",
                "RISK_RATING": 5,
                "PCT": 50.0,
                "RISK_PROFILE": "moderate",
                "ESG_MANDATE": None,
                "MAX_POSITION": "0.10",
                "EXCLUDED_SECTORS": "NOT_VALID_JSON",
            },
            {
                "ROW_TYPE": "SECTOR",
                "ID": "Technology",
                "LABEL": "Technology",
                "TICKER": None,
                "SECTOR": None,
                "REGION": None,
                "ASSET_CLASS": None,
                "RISK_RATING": None,
                "PCT": 50.0,
                "RISK_PROFILE": None,
                "ESG_MANDATE": None,
                "MAX_POSITION": None,
                "EXCLUDED_SECTORS": None,
            },
            {
                "ROW_TYPE": "REGION",
                "ID": "North America",
                "LABEL": "North America",
                "TICKER": None,
                "SECTOR": None,
                "REGION": None,
                "ASSET_CLASS": None,
                "RISK_RATING": None,
                "PCT": 100.0,
                "RISK_PROFILE": None,
                "ESG_MANDATE": None,
                "MAX_POSITION": None,
                "EXCLUDED_SECTORS": None,
            },
            {
                "ROW_TYPE": "ASSET_CLASS",
                "ID": "Equity",
                "LABEL": "Equity",
                "TICKER": None,
                "SECTOR": None,
                "REGION": None,
                "ASSET_CLASS": None,
                "RISK_RATING": None,
                "PCT": 100.0,
                "RISK_PROFILE": None,
                "ESG_MANDATE": None,
                "MAX_POSITION": None,
                "EXCLUDED_SECTORS": None,
            },
        ]
        result = _build_hedge_recommendations(rows, "ACC-999", "all")
        assert isinstance(result, dict)
