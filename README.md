# Parallel Crowd-Crush Risk Simulation

PCAP team project comparing sequential CPU, OpenMP, MPI, CUDA, and hybrid MPI + OpenMP + CUDA execution of the same pedestrian simulation.

## Contributions

| Member | Completed work |
| --- | --- |
| Sammit Menon | Shared movement model, sequential baseline, CUDA backend, visualization, and CPU/CUDA benchmarks and figures ([#1](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/1), [#2](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/2)) |
| Dwijesh P | OpenMP backend, shared crowd metrics and risk indicators, correctness comparisons, CUDA metric collection, hybrid backend, and five-backend benchmarking ([#3](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/3), [#5](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/5)) |
| Ayush KL | MPI backend, distributed state exchange, MPI tests, and MPI build integration ([#4](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/4)) |

The parallel backends use Sammit's shared sequential movement rule.

## Project layout

| Path | Purpose |
| --- | --- |
| include/ | Shared state, configuration, movement model, metrics declarations |
| src/common/ | Shared initialization, equations, geometry, I/O, metrics |
| src/sequential/ | Sequential CPU reference |
| src/openmp/ | OpenMP implementation |
| src/mpi/ | MPI implementation |
| src/cuda/ | CUDA kernels and host code |
| src/hybrid/ | MPI + OpenMP + CUDA integration |
| configs/ | Reproducible scenario configurations |
| scripts/ | Benchmark, visualization, plotting scripts |
| tests/ | Model checks and cross-backend correctness checks |
| results/ | Selected benchmark tables and plots |
| docs/ | Model specification, implementation plan and experiments |

## Current status

Sequential, OpenMP, MPI, CUDA, and hybrid MPI + OpenMP + CUDA executables are
implemented. CMake builds OpenMP, MPI, CUDA, and hybrid targets when their
dependencies are available. All backends write the shared crowd metrics;
CUDA can disable metric collection with `--no-metrics` for movement-only
benchmarking. The metrics are configurable simulation indicators, not
calibrated physical injury predictions.

The [metrics specification](docs/metrics_specification.md),
[hybrid and five-backend validation](docs/hybrid_validation.md),
[OpenMP validation](docs/openmp_validation.md), and
[CUDA validation](docs/cuda_validation.md) record definitions and checks.
Sammit's separate CUDA block-size study is in
[the CUDA benchmark report](docs/sammit_benchmarks.md).

## Build and run

Requires CMake and a C++17 compiler. OpenMP support enables `pcap_openmp`;
an MPI runtime and development SDK enable `pcap_mpi`; a CUDA toolkit enables
`pcap_cuda`. All three are needed for `pcap_hybrid`. On Windows, Microsoft MPI
and MSVC with CUDA integration are supported. CMake skips unavailable
optional backends.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
ctest --test-dir build --output-on-failure
mkdir -p results/tmp
build/pcap_sequential configs/wide_exit.cfg results/tmp/wide
build/pcap_openmp configs/wide_exit.cfg results/tmp/wide_openmp 4
# If MPI was detected:
mpiexec -n 2 build/pcap_mpi configs/wide_exit.cfg results/tmp/wide_mpi
# If CUDA was detected:
build/pcap_cuda configs/wide_exit.cfg results/tmp/wide_cuda 256
# If MPI, OpenMP and CUDA were all detected:
mpiexec -n 2 build/pcap_hybrid configs/wide_exit.cfg results/tmp/wide_hybrid 256 2
python scripts/visualize.py animate configs/wide_exit.cfg results/tmp/wide_snapshots.csv results/tmp/wide.html
python scripts/visualize.py heatmap configs/wide_exit.cfg results/tmp/wide_snapshots.csv results/tmp/wide_heatmap.svg
python scripts/visualize.py timeseries configs/wide_exit.cfg results/tmp/wide_snapshots.csv results/tmp/wide_summary.csv results/tmp/wide
```

To watch all five completed runs side by side on one synchronized timeline,
run each backend with the same config and different output prefixes, then run:

```sh
python scripts/visualize.py compare configs/wide_exit.cfg \
  results/tmp/seq_snapshots.csv results/tmp/omp_snapshots.csv \
  results/tmp/mpi_snapshots.csv results/tmp/cuda_snapshots.csv \
  results/tmp/hybrid_snapshots.csv results/tmp/comparison.html
```

Open `results/tmp/comparison.html` in a browser. **Model time** keeps all five
panels on the same simulation step. **Compute time** advances each panel
independently using cumulative `simulation_ms` from its matching `_summary.csv`;
the page also shows `_run.csv` timing and speedup versus sequential. Playback
is stretched for viewing and replays completed runs. Single-run timing
boundaries differ by backend, so use the repeated benchmark results for
performance claims.

For a live comparison, build all five executables and run:

```powershell
python scripts\live_compare.py --build-dir build-all
```

Enter the number of pedestrians (1–5,000) and click **Run all five**. The
desktop window launches five independent processes, draws each backend's
snapshots as they arrive, and shows its actual wall-clock completion time and
reported backend time. The room and exit scale with crowd size to keep initial
density comparable. Live runs continue until everyone exits or the displayed
maximum step is reached; if anyone remains, the panel says so. Use each panel's
seek bar, **Back**, and **Forward** to inspect snapshots while that backend keeps
running, then **Live** to return to its latest frame. The default of 2,000 makes
progress easier to see. Concurrent runs share
CPU and GPU resources, so use the repeated benchmark results for fair speed
comparisons.

On multi-configuration generators, executables may be under `build/Release/`.
Each run writes `_snapshots.csv`, `_summary.csv`, `_run.csv`, `_metrics.csv`,
and `_cells.csv` at the output prefix. MPI adds `_mpi_timing.csv`; hybrid adds
`_hybrid_timing.csv`. CUDA `--no-metrics` omits metric and cell files. Create
the parent directory first. Movement and metric sampling have separate
timers; CSV writing is outside both. Use identical scenarios and seeds when
comparing backends. See [the model specification](docs/model_specification.md)
for equations and timing definitions.

For the CPU/CUDA benchmark, run `scripts/benchmark_cuda.py` with `--cpu` and
`--cuda` pointing to Release executables. It performs a warm-up and five
measured repetitions per case, then writes raw runs, summary statistics and
SVG plots.
For the five-backend comparison, run `scripts/benchmark_backends.py` with
paths to the available executables and `--mpiexec`. The committed
[raw runs, medians, and plots](results/benchmarks/all_backends/summary.csv)
cover four crowd sizes and three exit widths. The hybrid report explains
the timing boundaries and one-GPU limitation.

## Development order

1. Agree on equations, parameters, configuration and output formats.
2. Sammit implements one pedestrian exiting a room, then 100 interacting pedestrians.
3. Verify boundaries, exit counts and current/next state buffers.
4. Dwijesh, Ayush and Sammit implement OpenMP, MPI and CUDA respectively.
5. Integrate the hybrid and validate all versions against the reference.
6. Run controlled performance and bottleneck experiments.

Use identical initial conditions, seeds, precision and update rules across backends.
Exclude visualization and file writing from simulation timing.
Risk categories are simulation indicators, with documented thresholds.

## Collaboration

Create a feature branch for each task, then open a pull request into main.
Do not independently change shared model equations; agree on the change as a team.
Keep generated binaries, secrets and temporary outputs out of Git.
