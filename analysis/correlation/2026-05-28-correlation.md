# Cross-Keyword Correlation Analysis — 2026-05-28

**Company:** Nova Trading Inc.
**Method:** Pearson correlation on 12-month weekly Google Trends data
**Sample size per pair:** ~52 weeks

---

## Strongest Positive Correlations (co-trending keywords)

| r | Keyword A | Category A | Keyword B | Category B |
|---|-----------|------------|-----------|------------|
| +0.987 | `fake nails set` | press_on_nails | `lace front wig` | wigs |
| +0.983 | `lace front wig` | wigs | `human hair wig` | wigs |
| +0.982 | `gold chain necklace` | jewelry | `lace front wig` | wigs |
| +0.982 | `gold chain necklace` | jewelry | `fake nails set` | press_on_nails |
| +0.979 | `fake nails set` | press_on_nails | `human hair wig` | wigs |
| +0.977 | `press on nails short` | press_on_nails | `human hair wig` | wigs |
| +0.973 | `statement necklace` | jewelry | `human hair wig` | wigs |
| +0.970 | `statement necklace` | jewelry | `gold chain necklace` | jewelry |
| +0.968 | `statement necklace` | jewelry | `fake nails set` | press_on_nails |
| +0.965 | `gold chain necklace` | jewelry | `human hair wig` | wigs |
| +0.965 | `statement necklace` | jewelry | `lace front wig` | wigs |
| +0.965 | `minimalist jewelry` | jewelry | `human hair wig` | wigs |
| +0.964 | `statement necklace` | jewelry | `minimalist jewelry` | jewelry |
| +0.959 | `press on nails short` | press_on_nails | `lace front wig` | wigs |
| +0.954 | `fake nails set` | press_on_nails | `press on nails short` | press_on_nails |

## Strongest Negative Correlations (substitution patterns)

| r | Keyword A | Category A | Keyword B | Category B |
|---|-----------|------------|-----------|------------|

## Within vs Cross-Category Correlation

| Category | Within-category avg r | # pairs |
|----------|----------------------|---------|
| wigs | +0.889 | 10 |
| jewelry | +0.718 | 10 |
| press_on_nails | +0.861 | 10 |
| **Cross-category** | +0.804 | 75 |

## Interpretation

- **High within-category r**: keywords share a common demand driver (e.g., seasonality, fashion cycle)
- **High cross-category r**: broader consumer-spending or platform-traffic effect; useful for multi-category demand forecasting
- **Negative r**: potential substitution; one keyword's demand grows at the other's expense