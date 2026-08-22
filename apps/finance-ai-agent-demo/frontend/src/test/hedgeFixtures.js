/**
 * Shared test fixtures for suggest_portfolio_hedge frontend tests.
 */

export const hedgeOutput = {
  account_id: "ACC-001",
  risk_profile: "aggressive",
  esg_mandate: false,
  risk_focus: "all",
  portfolio_summary: {
    total_holdings: 6,
    high_risk_positions: 2,
    sector_breakdown: [
      { sector: "Technology", pct: 40.0 },
      { sector: "Energy", pct: 20.0 },
    ],
    region_breakdown: [
      { region: "North America", pct: 65.0 },
      { region: "Europe", pct: 20.0 },
    ],
    asset_class_breakdown: [
      { asset_class: "Equity", pct: 80.0 },
      { asset_class: "Bond", pct: 20.0 },
    ],
  },
  risk_factors_identified: [
    "High equity concentration: 80.0% of portfolio is in equities.",
    "2 high-risk positions (risk_rating ≥ 7) totalling 20.0% of portfolio.",
    "Sector concentration: Technology represents 40.0% of portfolio.",
    "Regional concentration: North America represents 65.0% of portfolio.",
  ],
  hedge_recommendations: [
    {
      ticker: "SH",
      name: "ProShares Short S&P500 ETF",
      type: "Inverse ETF",
      rationale: "Broad market hedge; gains when S&P 500 declines.",
      risk_level: "medium",
      hedge_dimension: "market",
      trigger: "equity_pct=80.0%",
    },
    {
      ticker: "GLD",
      name: "SPDR Gold Shares",
      type: "Safe Haven",
      rationale: "Gold allocation offsets tail risk from 2 high-rated positions.",
      risk_level: "low",
      hedge_dimension: "market",
      trigger: "high_risk_positions=2",
    },
    {
      ticker: "PUT",
      name: "Put options on QQQ",
      type: "Options Strategy",
      rationale: "Buy QQQ put options as targeted downside protection for tech-heavy portfolios.",
      risk_level: "medium",
      hedge_dimension: "sector",
      trigger: "Technology=40.0%",
    },
    {
      ticker: "EFA",
      name: "iShares MSCI EAFE ETF",
      type: "Geographic Diversification",
      rationale: "Developed-market international exposure offsets US-heavy concentration.",
      risk_level: "low",
      hedge_dimension: "regional",
      trigger: "North America=65.0%",
    },
  ],
  disclaimer:
    "These recommendations are generated algorithmically for illustrative purposes only. " +
    "All hedging decisions should be reviewed by a qualified financial advisor.",
};

export function makeToolCall({
  id = "tc-hedge-001",
  name = "suggest_portfolio_hedge",
  args = { account_id: "ACC-001", risk_focus: "all" },
  status = "success",
  output = JSON.stringify(hedgeOutput),
  elapsed_ms = 142,
} = {}) {
  return { id, name, args, status, output, elapsed_ms };
}

export function makeRunningToolCall(overrides = {}) {
  return makeToolCall({ status: "running", output: null, elapsed_ms: null, ...overrides });
}

export function makeErrorToolCall(overrides = {}) {
  return makeToolCall({
    status: "error",
    output: "Database connection failed",
    elapsed_ms: 55,
    ...overrides,
  });
}
