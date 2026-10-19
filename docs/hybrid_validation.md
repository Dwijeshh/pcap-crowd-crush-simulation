# Hybrid integration and five-backend validation

Validated on 19 October 2026 on one Windows laptop with an Intel Core
i7-12650H, NVIDIA GeForce RTX 3050 Laptop GPU (4 GiB), driver 592.27,
MSVC 19.44, CUDA Toolkit 13.1, Microsoft MPI 10.1, and CMake 4.4.3. The
MPI runtime and SDK were extracted into an ignored local directory because
the system installer was canceled; they are not committed to the repository.
This machine has one GPU, so multiple MPI ranks share it.

## Implementation

Each MPI rank holds the full current state and owns a contiguous pedestrian
ID range. It uploads the current state to the selected GPU, launches the shared
CUDA updater for its range, and downloads only its updated range. MPI
`Allgatherv` assembles the complete next state on every rank. After each
step, OpenMP accumulates density, speed and bottleneck counts for the rank's
range; MPI `Allreduce` combines them. The shared metrics tracker applies the
same congestion-duration and exit-flow rules as the other backends. Rank zero
writes output. The method also handles ranks with zero assigned pedestrians.

CUDA by default downloads the updated state on every step to produce the
same metric and cell CSV files as the CPU backends. Its `metrics_ms` includes
those downloads and host metric sampling. `--no-metrics` preserves the earlier
movement-only benchmark path. Hybrid metrics use MPI reductions and OpenMP,
and do not require a separate full device download.

## Correctness

The combined MSVC/CUDA/MPI build passed all six CTest cases: model, metrics,
OpenMP, and MPI at one, two and four ranks. MPI snapshots and all metric/cell
rows matched sequential exactly in all three committed scenarios. CUDA metric
summaries matched all three within 0.001, as did CUDA cell rows except for
the narrow-exit boundary crossing described below. Hybrid runs with two or four MPI
ranks and two OpenMP threads per rank matched sequential exit counts and
active states in the committed scenarios. All 6,100 saved snapshot rows per
scenario were within the established 0.001 absolute position/velocity
tolerance:

| Scenario | Exited | Maximum position difference (m) | Maximum velocity difference (m/s) |
| --- | ---: | ---: | ---: |
| Wide exit | 52 / 100 | 0.0000058 | 0.0000161 |
| Narrow exit | 26 / 100 | 0.0002651 | 0.00078011 |
| Obstacle | 40 / 100 | 0.0000572 | 0.000151217 |

All 61 summary metric rows per scenario matched category, counts and values
within 0.001. Wide-exit and obstacle cell CSVs matched in all 14,640 rows
each. In the narrow-exit case, a small CUDA/CPU position difference moved one
pedestrian across a 1 m cell edge at step 590: two cell counts differ by one,
while the summary risk category still agrees. An empty 0-pedestrian run
completed on four ranks. A 3-pedestrian, 4-rank run also passed the snapshot
comparison, exercising a rank with no assigned IDs.

Use `tests/compare_snapshots.py` and `tests/compare_metrics.py` on output
prefixes. The latter has `--summary-only` for cases where device rounding
moves an agent across a cell boundary. Exact cell equality across CPU and GPU
is not guaranteed near grid edges.

With dependencies on `PATH`, a single scenario can be reproduced with:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build build --config Release
ctest --test-dir build --output-on-failure
mkdir -p results/tmp
build/pcap_sequential configs/wide_exit.cfg results/tmp/reference
mpiexec -n 2 build/pcap_hybrid configs/wide_exit.cfg results/tmp/hybrid 256 2
python tests/compare_snapshots.py results/tmp/reference_snapshots.csv results/tmp/hybrid_snapshots.csv
python tests/compare_metrics.py results/tmp/reference results/tmp/hybrid
```

## Controlled local benchmark

`scripts/benchmark_backends.py` generated
[`raw_runs.csv`](../results/benchmarks/all_backends/raw_runs.csv),
[`summary.csv`](../results/benchmarks/all_backends/summary.csv), and three SVG
figures. Each of seven cases had one warmup and five measured repetitions for
all five backends (175 measured runs). Seed 42, `dt=0.02`, and the common force
model were used. Crowd scaling used 500/1,000/2,000/5,000 people in a
100 × 70 m room for 100 steps with a 4 m exit. The bottleneck cases used
100 people in a 20 × 12 m room for 600 steps with 1/2/4 m exits. OpenMP used
four threads; MPI used two ranks; hybrid used two ranks, two OpenMP threads
per rank and CUDA blocks of 256; CUDA used blocks of 256 and `--no-metrics`.

Median reported backend times in milliseconds:

| Pedestrians | Sequential | OpenMP | MPI | CUDA | Hybrid |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 500 | 35.60 | 16.05 | 22.37 | 62.22 | 141.99 |
| 1,000 | 134.34 | 54.43 | 72.86 | 71.36 | 157.85 |
| 2,000 | 508.92 | 166.90 | 266.89 | 85.91 | 216.46 |
| 5,000 | 2,841.54 | 938.40 | 1,436.00 | 138.34 | 284.19 |

At 5,000 people, those medians correspond to 3.03× OpenMP, 1.98× MPI,
20.54× CUDA, and 10.00× hybrid relative to sequential on this machine. The
100-person exit cases produced 26, 44 and 52 exits for 1, 2 and 4 m
openings in every backend. Hybrid took roughly 690 ms per case, compared
with roughly 20 ms sequential, because the model is small relative to its
per-step GPU transfer and MPI costs. The scaling cases ended before anyone
reached the exit, so their zero exit counts are expected.

These timings describe each backend's movement pathway and exclude metric
sampling and CSV writing. Their setup boundaries differ slightly: sequential
includes next-state allocation, CUDA includes device allocation and initial
upload, OpenMP counts updates, MPI counts updates plus communication, and
hybrid counts per-step transfers, GPU work and communication but excludes
device allocation. Treat cross-backend speedups as local indicative results,
not interchangeable end-to-end latency. The GPU paths share one physical GPU
among ranks; this is not multi-GPU scaling. Quartiles and per-run values are
in the CSV files.

To rerun the matrix, pass `--sequential`, `--openmp`, `--mpi`, `--cuda`,
`--hybrid`, and `--mpiexec` paths to `scripts/benchmark_backends.py`. Its
defaults reproduce the case sizes, rank/thread counts, block size, warmups,
and repetitions above. It validates exit-count agreement before writing
the result files.
