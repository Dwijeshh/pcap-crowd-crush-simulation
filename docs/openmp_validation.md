# OpenMP validation

Validated on 18 October 2026 on a 12th Gen Intel Core i7-12650H using
WinLibs GCC 16.2, OpenMP 5.2, CMake with Ninja, and a Release build. The
OpenMP executable uses the shared `update_one` movement function, a static
parallel loop over pedestrians, immutable current state, and a distinct next
state. Metrics use per-thread cell accumulators followed by a reduction.

## Correctness

`ctest --test-dir build --output-on-failure` passed the model, metrics and
OpenMP tests (3/3). The OpenMP test compares complete states and metrics with
the sequential implementation. Separate executable runs used the committed
`wide_exit`, `narrow_exit`, and `obstacle` scenarios with 1 and 4 OpenMP
threads. `tests/compare_snapshots.py --abs-tol 0` passed each comparison:
6,100 saved pedestrian rows per pair, with exactly matching active states and
zero difference in saved position and velocity components. The metrics and
cell CSVs also matched exactly across all 44,103 compared rows for the three
scenarios at 4 threads. Exact equality is an observed result for this toolchain
and these inputs, not a general requirement for other compilers or hardware.

To reproduce on a machine with an OpenMP-capable C++ compiler:

```powershell
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
ctest --test-dir build --output-on-failure
New-Item -ItemType Directory -Force results/tmp | Out-Null
foreach ($scenario in @('wide_exit', 'narrow_exit', 'obstacle')) {
    .\build\pcap_sequential.exe "configs/$scenario.cfg" "results/tmp/${scenario}_seq"
    .\build\pcap_openmp.exe "configs/$scenario.cfg" "results/tmp/${scenario}_omp" 4
    python tests/compare_snapshots.py "results/tmp/${scenario}_seq_snapshots.csv" "results/tmp/${scenario}_omp_snapshots.csv" --abs-tol 0
}
```

## Preliminary movement benchmark

The benchmark used the wide-exit geometry and movement parameters, with
`pedestrians=500`, `steps=300`, and `snapshot_interval=300`. Each backend had
one warmup and five measured runs. Medians below are `total_ms`, which sums
movement update calls and excludes metrics, initialization, file output and
visualization. These are single-machine exploratory results, not a controlled
hardware comparison.

| Backend | Threads | Median update (ms) | Range (ms) | Speedup vs sequential | Median metrics (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sequential | 1 | 183.006 | 177.273–190.011 | 1.00× | 3.234 |
| OpenMP | 1 | 192.247 | 189.748–204.812 | 0.95× | 3.012 |
| OpenMP | 2 | 108.583 | 102.936–124.485 | 1.69× | 9.583 |
| OpenMP | 4 | 60.469 | 58.866–66.099 | 3.03× | 11.461 |
| OpenMP | 8 | 57.675 | 54.337–58.809 | 3.17× | 17.559 |

Metric collection costs increase with OpenMP thread count for this small grid
and crowd, so wall-clock performance including metrics is less favourable
than update-only speedup. Larger and repeated experiments are needed before
making a general scalability claim.
