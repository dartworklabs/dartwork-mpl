# dartwork-mpl Examples

Individual, focused plotting examples using dartwork-mpl — a general-purpose matplotlib design utility.

## Philosophy

- **One plot per file**: Each example script produces exactly one figure.
- **Domain-neutral**: Examples use synthetic, abstract data so that the
  technique — not the subject matter — is what is on display.
- **Reusable patterns**: Short, self-contained scripts that are easy to
  copy-paste and adapt.
- **Professional output**: Each script writes a high-resolution file to
  `examples/output/`.

## English Examples

| File | Technique |
|---|---|
| `plot_line_signals.py` | Line plot with SI-prefix axis formatting |
| `plot_bar_with_value_labels.py` | Bar chart with value labels above each bar |
| `plot_scatter_with_fit.py` | Scatter plot with linear regression overlay |
| `plot_histogram_normal_fit.py` | Density histogram with Normal-PDF overlay |
| `plot_heatmap.py` | `imshow` heatmap with a colorbar |

## Korean Examples (한글)

| 파일 | 주제 |
|---|---|
| `plot_line_signals_kr.py` | SI 단위 포매팅을 사용한 라인 플롯 |
| `plot_bar_with_value_labels_kr.py` | 값 레이블이 있는 막대 그래프 |
| `plot_scatter_with_fit_kr.py` | 회귀선이 포함된 산점도 |
| `plot_histogram_normal_fit_kr.py` | 정규분포 오버레이 히스토그램 |
| `plot_donut_composition_kr.py` | 도넛 형태의 파이 차트 |
| `plot_dual_axis_timeseries_kr.py` | 이중 축 시계열 (막대 + 라인) |

## Running

Run any script from the repo root:

```bash
uv run python examples/plot_line_signals.py
```

All plots are saved to `examples/output/`. The directory is created on
demand.
