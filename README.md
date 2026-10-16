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

Sammit's sequential reference, shared movement kernel, scenario files, and
dependency-free visualization tools are implemented. CUDA builds automatically
when CMake detects a CUDA toolkit. OpenMP, MPI, hybrid integration, and shared
risk metrics are still team work. The CUDA path needs validation on an NVIDIA
GPU before it can be called verified.

## Build and run

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
ctest --test-dir build --output-on-failure
mkdir -p results/tmp
build/pcap_sequential configs/wide_exit.cfg results/tmp/wide
# If CUDA was detected:
build/pcap_cuda configs/wide_exit.cfg results/tmp/wide_cuda 256
python scripts/visualize.py animate configs/wide_exit.cfg results/tmp/wide_snapshots.csv results/tmp/wide.html
python scripts/visualize.py heatmap configs/wide_exit.cfg results/tmp/wide_snapshots.csv results/tmp/wide_heatmap.svg
python scripts/visualize.py timeseries configs/wide_exit.cfg results/tmp/wide_snapshots.csv results/tmp/wide_summary.csv results/tmp/wide
```

On multi-configuration generators, executables may be under `build/Release/`.
Each run writes `_snapshots.csv`, `_summary.csv` and `_run.csv` at the output
prefix. Create the parent directory first. All visualization and CSV writing
occurs outside the CPU update timer. Use identical scenario files and seeds
when comparing backends. See [the model specification](docs/model_specification.md)
for equations and timing definitions.

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
