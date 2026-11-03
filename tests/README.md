# Correctness checks

`model_tests.cpp` covers empty and single-pedestrian runs, exit crossing,
pair interaction, wall handling, seeded initialization, finite states, and a
time-step refinement comparison. `metrics_tests.cpp` covers clipped grid
areas, density, speed, congestion duration, risk category, exit flow, and an
empty crowd. OpenMP and MPI tests compare movement with the sequential
reference; MPI tests run with one, two, and four ranks when MPI is available.

From a Visual Studio multi-configuration build, run
`ctest --test-dir build-all -C Release --output-on-failure`. The full build
registers six CTest cases. Missing optional dependencies mean fewer targets
and tests are registered.

`compare_snapshots.py` compares snapshot CSVs from two backends for the same
scenario. It requires identical step, agent ID, and active state, and a maximum
absolute difference of 0.001 for each position and velocity component by
default. Use `--abs-tol 0` for exact comparison where appropriate. See
[OpenMP validation](../docs/openmp_validation.md) and
[CUDA validation](../docs/cuda_validation.md) for commands and results.

`metrics_tests.cpp` checks grid area, cell density and speed, congestion
durations, exit flow and empty crowds. `openmp_tests.cpp` checks movement and
metrics against the sequential backend.
`mpi_tests.cpp` checks 1, 2 and 4 ranks, including uneven and empty rank
partitions. `compare_metrics.py` compares metric summary and cell CSVs; use
`--summary-only` when small CPU/GPU position differences cross a cell edge.
See [hybrid validation](../docs/hybrid_validation.md) for the five-backend
correctness results.
