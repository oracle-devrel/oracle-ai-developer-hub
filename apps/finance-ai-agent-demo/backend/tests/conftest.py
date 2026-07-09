"""Shared pytest fixtures for the finance-ai-agent backend test suite."""

import pytest

# ---------------------------------------------------------------------------
# Minimal portfolio rows as returned by _suggest_portfolio_hedge's SQL query
# ---------------------------------------------------------------------------


def _holding(
    holding_id,
    instrument_name,
    ticker,
    sector,
    region,
    asset_class,
    risk_rating,
    pct,
    risk_profile="moderate",
    esg_mandate=None,
    max_position="0.10",
    excluded_sectors=None,
):
    return {
        "ROW_TYPE": "HOLDING",
        "ID": holding_id,
        "LABEL": instrument_name,
        "TICKER": ticker,
        "SECTOR": sector,
        "REGION": region,
        "ASSET_CLASS": asset_class,
        "RISK_RATING": risk_rating,
        "PCT": pct,
        "RISK_PROFILE": risk_profile,
        "ESG_MANDATE": esg_mandate,
        "MAX_POSITION": max_position,
        "EXCLUDED_SECTORS": excluded_sectors or "[]",
    }


def _sector(name, pct):
    return {
        "ROW_TYPE": "SECTOR",
        "ID": name,
        "LABEL": name,
        "TICKER": None,
        "SECTOR": None,
        "REGION": None,
        "ASSET_CLASS": None,
        "RISK_RATING": None,
        "PCT": pct,
        "RISK_PROFILE": None,
        "ESG_MANDATE": None,
        "MAX_POSITION": None,
        "EXCLUDED_SECTORS": None,
    }


def _region(name, pct):
    return {
        "ROW_TYPE": "REGION",
        "ID": name,
        "LABEL": name,
        "TICKER": None,
        "SECTOR": None,
        "REGION": None,
        "ASSET_CLASS": None,
        "RISK_RATING": None,
        "PCT": pct,
        "RISK_PROFILE": None,
        "ESG_MANDATE": None,
        "MAX_POSITION": None,
        "EXCLUDED_SECTORS": None,
    }


def _asset_class(name, pct):
    return {
        "ROW_TYPE": "ASSET_CLASS",
        "ID": name,
        "LABEL": name,
        "TICKER": None,
        "SECTOR": None,
        "REGION": None,
        "ASSET_CLASS": None,
        "RISK_RATING": None,
        "PCT": pct,
        "RISK_PROFILE": None,
        "ESG_MANDATE": None,
        "MAX_POSITION": None,
        "EXCLUDED_SECTORS": None,
    }


def _high_risk(holding_id, instrument_name, ticker, sector, region, risk_rating, pct):
    return {
        "ROW_TYPE": "HIGH_RISK",
        "ID": holding_id,
        "LABEL": instrument_name,
        "TICKER": ticker,
        "SECTOR": sector,
        "REGION": region,
        "ASSET_CLASS": None,
        "RISK_RATING": risk_rating,
        "PCT": pct,
        "RISK_PROFILE": None,
        "ESG_MANDATE": None,
        "MAX_POSITION": None,
        "EXCLUDED_SECTORS": None,
    }


@pytest.fixture
def tech_heavy_rows():
    """Portfolio that is tech-heavy (40% sector) and equity-heavy (80% equities),
    located primarily in North America (70%), with two high-risk positions."""
    return [
        _holding(
            "H001",
            "Apple Inc",
            "AAPL",
            "Technology",
            "North America",
            "Equity",
            6,
            25.0,
            risk_profile="aggressive",
        ),
        _holding(
            "H002",
            "Microsoft Corp",
            "MSFT",
            "Technology",
            "North America",
            "Equity",
            5,
            15.0,
            risk_profile="aggressive",
        ),
        _holding(
            "H003",
            "ExxonMobil",
            "XOM",
            "Energy",
            "North America",
            "Equity",
            4,
            20.0,
            risk_profile="aggressive",
        ),
        _holding(
            "H004",
            "Riskco Ltd",
            "RSK",
            "Technology",
            "Europe",
            "Equity",
            8,
            10.0,
            risk_profile="aggressive",
        ),
        _holding(
            "H005",
            "DangerFund",
            "DNG",
            "Financials",
            "Asia",
            "Equity",
            9,
            10.0,
            risk_profile="aggressive",
        ),
        _holding(
            "H006",
            "Safe Bond A",
            "SBA",
            "Government",
            "North America",
            "Bond",
            2,
            20.0,
            risk_profile="aggressive",
        ),
        _sector("Technology", 40.0),
        _sector("Energy", 20.0),
        _sector("Government", 20.0),
        _sector("Financials", 10.0),
        _region("North America", 65.0),
        _region("Europe", 20.0),
        _region("Asia", 15.0),
        _asset_class("Equity", 80.0),
        _asset_class("Bond", 20.0),
        _high_risk("H004", "Riskco Ltd", "RSK", "Technology", "Europe", 8, 10.0),
        _high_risk("H005", "DangerFund", "DNG", "Financials", "Asia", 9, 10.0),
    ]


@pytest.fixture
def esg_rows():
    """Portfolio with ESG mandate set — leveraged/high-risk instruments should be filtered."""
    return [
        _holding(
            "H001",
            "Green Energy ETF",
            "GRN",
            "Energy",
            "North America",
            "Equity",
            3,
            70.0,
            risk_profile="conservative",
            esg_mandate="yes",
        ),
        _holding(
            "H002",
            "Clean Tech Fund",
            "CLT",
            "Technology",
            "North America",
            "Equity",
            4,
            30.0,
            risk_profile="conservative",
            esg_mandate="yes",
        ),
        _sector("Energy", 70.0),
        _sector("Technology", 30.0),
        _region("North America", 100.0),
        _asset_class("Equity", 100.0),
    ]


@pytest.fixture
def balanced_rows():
    """Well-diversified portfolio — should trigger few or no risk factors."""
    return [
        _holding("H001", "US Equity Fund", "USQ", "Financials", "North America", "Equity", 3, 20.0),
        _holding("H002", "EU Bond Fund", "EUB", "Government", "Europe", "Bond", 2, 20.0),
        _holding("H003", "Asia Growth", "ASG", "Technology", "Asia", "Equity", 4, 20.0),
        _holding("H004", "Gold ETF", "GLD", "Commodities", "North America", "Commodity", 2, 20.0),
        _holding("H005", "EM Equity", "EMQ", "Financials", "Asia", "Equity", 5, 20.0),
        _sector("Financials", 25.0),
        _sector("Government", 20.0),
        _sector("Technology", 20.0),
        _sector("Commodities", 20.0),
        _region("North America", 40.0),
        _region("Europe", 20.0),
        _region("Asia", 40.0),
        _asset_class("Equity", 60.0),
        _asset_class("Bond", 20.0),
        _asset_class("Commodity", 20.0),
    ]


@pytest.fixture
def intl_heavy_rows():
    """Portfolio with 60% outside North America — should trigger currency hedge."""
    return [
        _holding("H001", "EU Stocks", "EUS", "Financials", "Europe", "Equity", 4, 35.0),
        _holding("H002", "Japan Growth", "JPG", "Technology", "Asia", "Equity", 5, 25.0),
        _holding("H003", "US Bonds", "USB", "Government", "North America", "Bond", 2, 40.0),
        _sector("Financials", 35.0),
        _sector("Technology", 25.0),
        _sector("Government", 40.0),
        _region("Europe", 35.0),
        _region("Asia", 25.0),
        _region("North America", 40.0),
        _asset_class("Equity", 60.0),
        _asset_class("Bond", 40.0),
    ]
