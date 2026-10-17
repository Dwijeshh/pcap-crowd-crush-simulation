# Correctness checks

Cover one pedestrian, pair interaction, walls, exit crossing, empty crowd and reproducible initialization.
Compare positions/velocities after one step and short runs across backends.
Check exited counts, cell metrics, uneven MPI partitions and invalid numeric values.
Document absolute/relative tolerances and test time-step stability.

`compare_snapshots.py` compares sequential and CUDA snapshot CSVs for the same
scenario. It requires identical step, agent ID, and active state, and a maximum
absolute difference of 0.001 for each position and velocity component by
default. Run it after both executables finish; see
[`docs/cuda_validation.md`](../docs/cuda_validation.md) for the commands and
measured differences on Sammit's GPU.
