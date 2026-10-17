# Scripts

`visualize.py` uses only Python's standard library:

- `animate CONFIG SNAPSHOTS OUTPUT.html` makes an interactive, standalone crowd animation.
- `heatmap CONFIG SNAPSHOTS OUTPUT.svg [--step N] [--cell METRES]` makes a density heatmap.
- `timeseries CONFIG SNAPSHOTS SUMMARY OUTPUT_PREFIX [--cell METRES]` makes peak-density and exit-flow charts.
- `performance OUTPUT_PREFIX RUN.csv...` makes runtime versus crowd size and, when a sequential reference and parallel result share a crowd size, speedup charts.

The heatmap counts active pedestrian centres per cell and divides by the
actual cell area. Exit flow is the increase in cumulative exited pedestrians
divided by time between snapshots. These are descriptive simulation metrics,
not calibrated physical risk indicators. Use repeated benchmark runs and
reported medians for publication-quality performance plots; a single run is
only a smoke test. Ayush owns the experiment runner.
