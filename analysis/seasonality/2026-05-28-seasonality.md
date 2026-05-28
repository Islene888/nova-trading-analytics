# Seasonality Decomposition — 2026-05-28

**Company:** Nova Trading Inc.
**Method:** Classical additive decomposition (Y = Trend + Seasonal + Residual)
**Period:** 13 weeks (quarterly cycle on weekly data)

---

## Seasonality Strength Ranking

| Keyword | Category | Strength | Peak (cycle wk) | Trough (cycle wk) |
|---------|----------|----------|-----------------|-------------------|
| `synthetic wig` | wigs | 0.399 | wk 6 | wk 2 |
| `fashion jewelry women` | jewelry | 0.297 | wk 11 | wk 3 |
| `trendy jewelry set` | jewelry | 0.282 | wk 11 | wk 3 |
| `human hair wig` | wigs | 0.269 | wk 7 | wk 3 |
| `press on nails coffin` | press_on_nails | 0.266 | wk 7 | wk 4 |
| `lace front wig` | wigs | 0.263 | wk 6 | wk 3 |
| `press on nails short` | press_on_nails | 0.257 | wk 6 | wk 4 |
| `fake nails set` | press_on_nails | 0.255 | wk 6 | wk 3 |
| `statement necklace` | jewelry | 0.247 | wk 7 | wk 3 |
| `press on nails` | press_on_nails | 0.240 | wk 7 | wk 2 |
| `stick on nails` | press_on_nails | 0.240 | wk 7 | wk 8 |
| `minimalist jewelry` | jewelry | 0.237 | wk 7 | wk 2 |
| `headband wig` | wigs | 0.237 | wk 7 | wk 3 |
| `short bob wig` | wigs | 0.234 | wk 6 | wk 3 |
| `gold chain necklace` | jewelry | 0.210 | wk 7 | wk 2 |

## Seasonal Pattern Detail (Top 3)

### `synthetic wig` (wigs)

Seasonal effect at each week of cycle (deviation from trend):

```
  Week  0:  -2.10  --
  Week  1:  -5.57  -----
  Week  2:  -6.54  ------
  Week  3:  -5.77  -----
  Week  4:  -4.05  ----
  Week  5:  +2.00  ++
  Week  6: +12.90  ++++++++++++
  Week  7:  +8.28  ++++++++
  Week  8:  +3.02  +++
  Week  9:  +2.33  ++
  Week 10:  -4.00  ----
  Week 11:  +0.43  
  Week 12:  -0.93  
```

### `fashion jewelry women` (jewelry)

Seasonal effect at each week of cycle (deviation from trend):

```
  Week  0:  +1.60  +
  Week  1:  -0.81  
  Week  2:  -1.20  -
  Week  3:  -1.25  -
  Week  4:  -0.97  
  Week  5:  -0.66  
  Week  6:  -0.51  
  Week  7:  -0.51  
  Week  8:  -1.25  -
  Week  9:  -1.25  -
  Week 10:  -0.58  
  Week 11:  +4.06  ++++
  Week 12:  +3.34  +++
```

### `trendy jewelry set` (jewelry)

Seasonal effect at each week of cycle (deviation from trend):

```
  Week  0:  +0.20  
  Week  1:  -0.16  
  Week  2:  -0.18  
  Week  3:  -0.21  
  Week  4:  -0.21  
  Week  5:  +0.13  
  Week  6:  +0.09  
  Week  7:  +0.09  
  Week  8:  -0.08  
  Week  9:  -0.08  
  Week 10:  -0.08  
  Week 11:  +0.25  
  Week 12:  +0.23  
```

## Business Implications

- **High seasonality (strength > 0.3)**: forecasting model must explicitly model seasonal component; safety stock should peak ahead of seasonal peaks
- **Low seasonality (strength < 0.1)**: simple level-based forecasting acceptable; smoother inventory cycle
- **Peak/trough timing**: informs procurement lead-time planning