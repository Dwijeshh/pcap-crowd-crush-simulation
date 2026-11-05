# Parallel Crowd-Crush Risk Simulation

A reproducible pedestrian simulation implemented in five computing backends: sequential CPU, OpenMP, MPI, CUDA, and MPI + CUDA + OpenMP hybrid. The project compares computing performance and simulated congestion near an exit using one shared movement model and common output formats.

> **Research scope:** Density, congestion, and low/medium/high labels are model indicators. They have not been calibrated against real pedestrian trajectories or injury outcomes.

## Results at a glance

| Experiment | Recorded result |
| --- | --- |
| Implementation checks | Six CTest cases passed in the complete local build; tested backends agreed on exit counts and recorded risk categories. |
| 5,000 pedestrians, 100 steps | Median movement time: sequential 2,841.54 ms; OpenMP 938.40 ms; MPI 1,436.00 ms; CUDA 138.34 ms; hybrid 284.19 ms. CUDA was 20.54× faster than sequential by this timing measure. |
| 100 pedestrians, 12 simulated seconds | With 1 m, 2 m, and 4 m exits, 26, 44, and 52 people exited, respectively. Recorded peak density decreased from 6 to 4 to 3 people/m². |

These results come from one Windows laptop with one RTX 3050 GPU. Each benchmark setting had one warm-up and five measured runs. Timing scopes differ among backends, so the speed ratios describe this local benchmark rather than identical end-to-end run time. See the [validation record](docs/hybrid_validation.md), [experiment protocol](docs/experiments.md), and [raw results](results/README.md).

## Quick start

### Requirements

- CMake 3.18 or newer and a C++17 compiler for the sequential backend.
- OpenMP support for `pcap_openmp`.
- An MPI runtime and development SDK for `pcap_mpi`.
- An NVIDIA GPU and CUDA toolkit for `pcap_cuda`.
- MPI, OpenMP, and CUDA together for `pcap_hybrid`.
- Python 3 with Tkinter for the live desktop comparison. The simulation and visualization scripts use the Python standard library; generating the separate review PDF also requires ReportLab.

CMake skips optional backends whose dependencies are unavailable. On Windows, the full build uses Visual Studio, Microsoft MPI, and CUDA integration.

### Build and test on Windows (PowerShell)

Run these commands **from the repository root**:

```powershell
cmake -S . -B build-all -G 'Visual Studio 17 2022' -A x64
cmake --build build-all --config Release
ctest --test-dir build-all -C Release --output-on-failure
```

### Run a scenario

```powershell
New-Item -ItemType Directory -Force results\tmp | Out-Null
.\build-all\Release\pcap_sequential.exe configs\wide_exit.cfg results\tmp\seq
.\build-all\Release\pcap_openmp.exe configs\wide_exit.cfg results\tmp\omp 4
```

If the matching executables were built, run the other backends with separate output prefixes:

```powershell
mpiexec -n 2 .\build-all\Release\pcap_mpi.exe configs\wide_exit.cfg results\tmp\mpi
.\build-all\Release\pcap_cuda.exe configs\wide_exit.cfg results\tmp\cuda 256
mpiexec -n 2 .\build-all\Release\pcap_hybrid.exe configs\wide_exit.cfg results\tmp\hybrid 256 2
```

For a single-configuration generator on Linux or macOS, use `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release`, build with `cmake --build build`, and run executables directly from `build/`. CUDA requires supported NVIDIA hardware.

### Watch all five runs live

After building all five backends and making `mpiexec` available, run:

```powershell
python scripts\live_compare.py --build-dir build-all
```

Choose a pedestrian count and exit width, then select **Run all five**. Each backend runs as an independent process. Its panel shows live crowd metrics and real elapsed time; Pause, seek, Back, Forward, and Live control the displayed frames without stopping the process. A combined chart tracks exits as results arrive. Simultaneous runs share the laptop's CPU and GPU, so use the repeated benchmarks for performance claims. For a non-graphical run, add `--headless`.

Each output prefix produces snapshots, summaries, run timing, metrics, and per-cell CSV files. The [scripts guide](scripts/README.md) covers replay, visualization, and benchmark commands.

## Reproduce the research

| Resource | Contents |
| --- | --- |
| [Model specification](docs/model_specification.md) | Movement equations, room geometry, state, and timing definitions |
| [Metrics specification](docs/metrics_specification.md) | Density, speed, congestion, bottleneck, exit flow, and risk-label rules |
| [Validation record](docs/hybrid_validation.md) | Cross-backend checks, hardware, numerical tolerances, and timing limits |
| [Report studies](docs/report_studies.md) | Parallel configuration sweep and exit-width study |
| [Raw data and plots](results/README.md) | Benchmark runs, summary tables, and SVG figures |
| [Paper source and build guide](report/README.md) | IEEEtran manuscript, figure source, and separate review PDF |

Use the same configuration and seed when comparing backends. The [experiment protocol](docs/experiments.md) describes warm-ups, repetition counts, medians, and timing boundaries. The manuscript is a research draft; the checked-in review PDF is a separate render, so compile and inspect the IEEEtran source before any formal submission.

If you use this project in research before a paper is published, cite the repository URL and the commit you used. Add the paper citation after publication.

## Contributors

| Contributor | Main contributions |
| --- | --- |
| Sammit Menon | Movement model, sequential reference, CUDA backend, initial visualization, and CPU/CUDA benchmarks ([PR #1](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/1), [PR #2](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/2)) |
| Ayush KL | MPI backend, state exchange, MPI tests, and build integration ([PR #4](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/4)) |
| Dwijesh P | OpenMP backend, shared metrics, CUDA metric collection, hybrid integration, live UI, benchmarks, and report studies ([PR #3](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/3), [PR #5](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/5), [PR #7](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/7), [PR #8](https://github.com/Dwijeshh/pcap-crowd-crush-simulation/pull/8)) |

The parallel backends retain the shared movement rule established by the sequential reference.

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md) for build, validation, and pull request guidance, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations, and [SECURITY.md](SECURITY.md) for private vulnerability reporting. The software and its code documentation are released under the [MIT License](LICENSE). The manuscript and research figures are scholarly works outside that software license; cite them normally and check their publication terms before reuse.
