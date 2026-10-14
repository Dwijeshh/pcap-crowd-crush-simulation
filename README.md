# Parallel Crowd-Crush Risk Simulation

PCAP team project comparing sequential CPU, OpenMP, MPI, CUDA, and hybrid MPI + OpenMP + CUDA execution of the same pedestrian simulation.

## Team responsibilities

| Member | Responsibility |
| --- | --- |
| Sammit Menon | Shared movement model, sequential baseline, CUDA, visualization |
| Dwijesh P | OpenMP, risk indicators, correctness comparisons |
| Ayush KL | MPI, build setup, hybrid integration, benchmark runner |

Sammit starts with a verified sequential model. Parallel implementations follow that reference.

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

Repository scaffold only. Simulation executables and model equations have not been implemented.
CMake currently configures the project but has no executable targets.

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
