# Scripts

`visualize.py` uses only Python's standard library:

- `animate CONFIG SNAPSHOTS OUTPUT.html` makes an interactive, standalone crowd animation.
- `compare CONFIG SEQUENTIAL_snapshots.csv OPENMP_snapshots.csv MPI_snapshots.csv CUDA_snapshots.csv HYBRID_snapshots.csv OUTPUT.html` makes a five-panel replay with model-time and independent compute-time views. Each input needs matching `_summary.csv` and `_run.csv` files with the same prefix.
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

`live_compare.py` opens a Tkinter window with a pedestrian-count input and
runs all five built executables concurrently. It reads snapshots while each
process is running, with no playback clock. Its wall times include launch and
output overhead; the executables' reported times use their own timing scopes.
The live scenario runs until evacuation or a stated maximum step. The window
scrolls to keep metrics and controls accessible. Each panel has Pause, seek,
Back, Forward, and Live controls; these change only the viewed snapshot and do
not affect the backend process. A shared live chart overlays the five exit
curves against observed wall time as snapshots arrive.
Run `python scripts/live_compare.py --build-dir build-all` from the repo root.
Use `--headless --pedestrians 1000` to run the same comparison without a window.
