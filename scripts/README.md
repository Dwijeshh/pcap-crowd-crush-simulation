# Scripts

`visualize.py` uses only Python's standard library:

- `animate CONFIG SNAPSHOTS OUTPUT.html` makes an interactive, standalone crowd animation.
- `compare CONFIG SEQUENTIAL.csv OPENMP.csv MPI.csv CUDA.csv HYBRID.csv OUTPUT.html` makes a synchronized five-panel replay from runs with matching snapshot steps and times.
- `heatmap CONFIG SNAPSHOTS OUTPUT.svg [--step N] [--cell METRES]` makes a density heatmap.
- `timeseries CONFIG SNAPSHOTS SUMMARY OUTPUT_PREFIX [--cell METRES]` makes peak-density and exit-flow charts.
- `performance OUTPUT_PREFIX RUN.csv...` makes runtime versus crowd size and, when a sequential reference and parallel result share a crowd size, speedup charts.

The heatmap counts active pedestrian centres per cell and divides by the
actual cell area. Exit flow is the increase in cumulative exited pedestrians
divided by time between snapshots. These are descriptive simulation metrics,
not calibrated physical risk indicators. Use repeated benchmark runs and
reported medians for publication-quality performance plots; a single run is
only a smoke test.

`benchmark_cuda.py` repeats sequential/CUDA block-size runs.
`benchmark_backends.py` runs the five available backends on the crowd-size
and exit-width matrix, writes raw/summary CSVs and three SVG figures, and
checks that exited counts agree. It needs paths to the built executables and
an MPI launcher. See [hybrid validation](../docs/hybrid_validation.md) for
the recorded hardware and results.
