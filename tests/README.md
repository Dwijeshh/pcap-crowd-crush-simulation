# Correctness checks

Cover one pedestrian, pair interaction, walls, exit crossing, empty crowd and reproducible initialization.
Compare positions/velocities after one step and short runs across backends.
Check exited counts, cell metrics, uneven MPI partitions and invalid numeric values.
Document absolute/relative tolerances and test time-step stability.

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
