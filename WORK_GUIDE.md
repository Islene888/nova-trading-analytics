# Nova Trading Inc. — E-Commerce Operations Research Analyst
# Work Guide & Daily Task Reference

**Role:** E-Commerce Operations Research Analyst (SOC 15-2031)
**Schedule:** Part-time, 24 hours/week
**Compliance Note:** All tasks must reflect specialty occupation duties as defined in the H-1B LCA and I-129 petition. The majority of working hours must be spent on quantitative analysis, modeling, and data engineering — not on general business operations or physical fulfillment work.

---

## Weekly Time Allocation

| Duty Area | % of Time | Weekly Hours |
|-----------|-----------|-------------|
| Demand Forecasting & Inventory Optimization | 30% | ~7 hrs |
| Pricing Strategy & Revenue Optimization | 25% | ~6 hrs |
| Customer Behavior Modeling & Cohort Analysis | 20% | ~5 hrs |
| A/B Testing & Causal Inference | 15% | ~3.5 hrs |
| Business Intelligence, Reporting & Data Engineering | 10% | ~2.5 hrs |
| **Total** | **100%** | **24 hrs** |

---

## Daily Work Structure

Each workday should include:
1. **One primary analytical task** (from the duty areas above)
2. **A GitHub commit** with meaningful code or analysis output
3. **A work log entry** in `logs/YYYY-MM-DD.md`

---

## Task Bank by Duty Area

Use this as a menu — pick tasks that match the current stage of business operations.

### A. Demand Forecasting & Inventory Optimization

**Platform Setup Phase (before sales data exists):**
- Research and document demand signal sources (TikTok engagement metrics, Amazon BSR trends, Google Trends)
- Build synthetic demand simulation model to test forecasting pipeline before live data is available
- Design database schema for unified multi-channel sales data (Shopify + Amazon + TikTok)
- Implement Shopify Admin API data ingestion script (`data_pipeline/shopify_ingest.py`)
- Implement Amazon SP-API authentication and order data pull
- Write unit tests for data ingestion pipeline

**Ongoing Operations Phase:**
- Run weekly demand forecast for top 10 SKUs; document forecast vs. actual
- Update safety stock levels based on latest lead time data from supplier
- Analyze stockout incidents: root cause (forecast error vs. supply delay), update model
- Backtest forecasting models on historical data; compute MAE, RMSE, MAPE
- Evaluate seasonal decomposition for upcoming holiday/event demand spikes

### B. Pricing Strategy & Revenue Optimization

**Platform Setup Phase:**
- Scrape and analyze competitor pricing on Amazon for target product categories (Python + BeautifulSoup/Selenium)
- Build price elasticity estimation framework (`analysis/pricing_optimization/price_elasticity.py`)
- Design pricing experiment: define control/treatment groups, primary metric (conversion rate), guardrail metrics
- Document pricing strategy rationale: competitive positioning, margin targets, channel-specific pricing rules

**Ongoing Operations Phase:**
- Run weekly price elasticity re-estimation as new sales data accumulates
- Analyze Amazon Buy Box win rate vs. price position; model optimal price point
- Evaluate promotional pricing scenarios: discount depth vs. revenue impact simulation
- Compute contribution margin by SKU and channel; flag underperforming products
- Build dynamic pricing decision dashboard (price recommendation + expected revenue impact)

### C. Customer Behavior Modeling & Cohort Analysis

**Platform Setup Phase:**
- Implement Shopify customer event tracking (pixel setup, custom event schema)
- Design customer data model: unified identity across Shopify, Amazon, TikTok
- Build cohort analysis framework: define cohort periods, retention metrics, revenue per cohort
- Research CLV modeling approaches applicable to early-stage e-commerce (BG/NBD, Pareto/NBD)

**Ongoing Operations Phase:**
- Run monthly cohort retention analysis; produce retention curve visualization
- Build customer segmentation model (RFM: Recency, Frequency, Monetary) once 30+ orders exist
- Estimate customer acquisition cost (CAC) by channel; compare to CLV estimate
- Analyze repeat purchase rate by product category and acquisition channel
- Identify high-LTV customer segments for targeted retention campaigns

### D. A/B Testing & Causal Inference

**Platform Setup Phase:**
- Document A/B testing methodology: MDE, sample size calculation, significance threshold, runtime rules
- Set up Amazon Experiments (Seller Central built-in A/B testing) for product listing optimization
- Design first Shopify A/B test: product page layout or pricing display
- Build statistical testing module (`analysis/ab_testing/significance_test.py`)

**Ongoing Operations Phase:**
- Pre-register each experiment: hypothesis, metrics, sample size, runtime
- Run power analysis before launching any test; document assumptions
- Analyze completed experiments: compute p-value, confidence intervals, practical significance
- Write experiment postmortem: result, business decision made, follow-up questions
- Apply multiple comparisons correction (Bonferroni/BH) when running simultaneous tests

### E. Business Intelligence, Reporting & Data Engineering

**Platform Setup Phase:**
- Build unified ETL pipeline: pull data from Shopify API, Amazon SP-API, TikTok Shop API
- Design analytical data model: normalize orders, products, customers across three schemas
- Create weekly KPI dashboard: GMV by channel, conversion rate, AOV, inventory turnover
- Set up automated data quality checks: completeness, consistency, freshness

**Ongoing Operations Phase:**
- Maintain weekly analytics report: channel performance, top/bottom SKUs, forecast accuracy
- Debug and maintain data pipelines; document incidents and fixes
- Optimize SQL query performance as data volume grows
- Add new metrics as business questions arise; document metric definitions

---

## Monthly Milestones

| Month | Focus | Key Deliverables |
|-------|-------|-----------------|
| Jun 2026 | Infrastructure | Shopify + Amazon API pipelines live; database schema finalized; demand forecasting model coded |
| Jul 2026 | Baseline Analytics | First demand forecasts; price elasticity estimates; cohort analysis framework running |
| Aug 2026 | Optimization | First pricing experiment results; inventory model validated; CLV model draft |
| Sep 2026 | Scale | Cross-channel attribution model live; automated weekly reporting; A/B test cadence established |

---

## Work Log Requirements (Daily)

Each work log (`logs/YYYY-MM-DD.md`) must include:

1. **Date and hours worked**
2. **Tasks completed** — describe what was done, what tools/methods were used, what decisions were made
3. **Outputs** — file names of code committed, analysis completed, or documents written
4. **Findings or next steps** — what was learned, what follows

A good work log entry looks like:
> "Implemented log-log OLS regression for price elasticity estimation on simulated product data. Estimated elasticity of -1.8 for Category A, consistent with literature on fashion accessories. Committed `price_elasticity.py`. Next: validate on real sales data once first 30 days of Shopify data are available."

A bad work log entry (avoid):
> "Worked on the business today."

---

## Compliance Rules

These rules ensure the work record supports specialty occupation status.

**Do:**
- Spend the majority of hours on the analytical/engineering tasks listed above
- Write detailed work logs with method names, tool names, and analytical decisions
- Commit code to GitHub with descriptive commit messages referencing the business problem being solved
- Document the "why" behind analytical decisions (why this model, why this metric)

**Do not log as work hours:**
- Packing, shipping, or physically handling inventory (hire part-time contractors for this)
- General customer service or order processing
- Social media posting without an analytical component
- Administrative tasks unrelated to quantitative analysis

**Gray area — log carefully:**
- Vendor/supplier research: log only if it involved quantitative analysis (price comparison model, demand feasibility)
- Platform setup (Shopify theme, Amazon listing): log only the analytical/technical components (A/B test design, conversion tracking setup), not routine configuration

---

## GitHub Commit Standards

Commit messages should describe the analytical work, not just the code change:

| Good | Bad |
|------|-----|
| `Add price elasticity OLS estimator with R² diagnostic` | `update file` |
| `Implement safety stock formula with configurable service level` | `fix bug` |
| `Add Shopify order pagination and rate limit handling` | `add code` |
| `Draft demand forecasting model spec for SKU-level ARIMA` | `new file` |

---

*This guide is maintained by the E-Commerce Operations Research Analyst and reflects the actual duties performed in the role.*
