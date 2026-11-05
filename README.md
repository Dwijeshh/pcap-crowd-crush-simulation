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

### Requirements and installation

The commands below use **Windows PowerShell** and the Visual Studio 2022 generator. Install these tools, then open a new PowerShell window so updated paths are available:

| Tool | Needed for | Install source |
| --- | --- | --- |
| Git | Cloning the repository | [Git for Windows](https://git-scm.com/download/win) |
| CMake 3.18+ | Configuring and building every backend | [CMake downloads](https://cmake.org/download/) |
| Visual Studio 2022 or Build Tools with **Desktop development with C++** | C++17 compiler, Windows SDK, OpenMP, and CUDA host compiler | [Microsoft C++ setup guide](https://learn.microsoft.com/en-us/cpp/build/vscpp-step-0-installation) |
| Python 3 with Tkinter | Live desktop comparison and visualization scripts | [Python for Windows](https://www.python.org/downloads/windows/) |
| Microsoft MPI **Runtime and SDK** | MPI and hybrid builds; `mpiexec` runs them | [MS-MPI downloads](https://learn.microsoft.com/en-us/message-passing-interface/microsoft-mpi) |
| NVIDIA driver, CUDA-capable GPU, and CUDA Toolkit | CUDA and hybrid builds | [CUDA installation guide](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/) |

The **sequential** executable needs only CMake and the C++ tools. **OpenMP** uses the C++ tools' OpenMP support. **MPI** adds Microsoft MPI; **CUDA** adds the GPU, driver, and toolkit; **hybrid** needs all of them. CMake omits optional executables when it cannot find their dependencies. No `pip install` is needed to run the simulator or live viewer. Generating the separate review PDF additionally requires ReportLab.

Check that the command-line tools you installed are available:

```powershell
cmake --version
python --version
Get-Command git, cmake, python, mpiexec, nvcc -ErrorAction SilentlyContinue |
    Select-Object Name, Source
```

`mpiexec` and `nvcc` appear only after installing their optional components. CUDA users can also run `nvidia-smi` to check that Windows sees the GPU. `cl.exe` may be absent from an ordinary PowerShell session even when Visual Studio is installed; CMake's Visual Studio generator locates the compiler. NVIDIA's driver and CUDA toolkit must both be installed for current Windows CUDA releases.

### Clone the repository

```powershell
git clone https://github.com/Dwijeshh/pcap-crowd-crush-simulation.git
cd pcap-crowd-crush-simulation
Test-Path .\CMakeLists.txt  # must print True
```

### Build and test on Windows (PowerShell)

Run these commands **from the repository root**:

```powershell
cmake -S . -B build-all -G 'Visual Studio 17 2022' -A x64
cmake --build build-all --config Release
ctest --test-dir build-all -C Release --output-on-failure
Get-ChildItem .\build-all\Release\pcap_*.exe | Select-Object -ExpandProperty Name
```

The last command lists the backends that CMake actually built. If an executable is missing, check its requirement in the table above and rerun the configure and build commands.

### Run a scenario

```powershell
New-Item -ItemType Directory -Force results\tmp | Out-Null
.\build-all\Release\pcap_sequential.exe configs\wide_exit.cfg results\tmp\seq
.\build-all\Release\pcap_openmp.exe configs\wide_exit.cfg results\tmp\omp 4
```

To view the sequential run in a browser:

```powershell
python scripts\visualize.py animate configs\wide_exit.cfg results\tmp\seq_snapshots.csv results\tmp\seq.html
Start-Process .\results\tmp\seq.html
```

If the matching executables were built, run the other backends with separate output prefixes:

```powershell
mpiexec -n 2 .\build-all\Release\pcap_mpi.exe configs\wide_exit.cfg results\tmp\mpi
.\build-all\Release\pcap_cuda.exe configs\wide_exit.cfg results\tmp\cuda 256
mpiexec -n 2 .\build-all\Release\pcap_hybrid.exe configs\wide_exit.cfg results\tmp\hybrid 256 2
```

On Linux or macOS with a suitable compiler, use `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release`, then `cmake --build build` and `ctest --test-dir build --output-on-failure`. Executables are under `build/`; optional MPI and CUDA targets still depend on detected toolchains and hardware. The validated full five-backend setup was on Windows.

### Watch all five runs live

After building all five backends and making `mpiexec` available, run:

```powershell
python scripts\live_compare.py --build-dir build-all
```

Choose a pedestrian count and exit width, then select **Run all five**. Each backend runs as an independent process. Its panel shows live crowd metrics and real elapsed time; Pause, seek, Back, Forward, and Live control the displayed frames without stopping the process. A combined chart tracks exits as results arrive. Simultaneous runs share the laptop's CPU and GPU, so use the repeated benchmarks for performance claims. For a non-graphical run, add `--headless`.

Each output prefix produces snapshots, summaries, run timing, metrics, and per-cell CSV files. The [scripts guide](scripts/README.md) covers replay, visualization, and benchmark commands.

If configuration says the source directory has no `CMakeLists.txt`, run `cd pcap-crowd-crush-simulation` first. If `mpiexec` or `nvcc` is unavailable, install the corresponding requirement and restart PowerShell. If `build-all\Release` lacks an optional executable, rerun CMake after installing that dependency.

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

## Feedback and copyright

See [CONTRIBUTING.md](CONTRIBUTING.md) for reproducibility feedback and team development guidance, [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations, and [SECURITY.md](SECURITY.md) for private vulnerability reporting. External code contributions are paused while the research is being prepared for publication.

The root [LICENSE](LICENSE) file is an **all rights reserved notice**, not an open-source license. The authors retain their rights; please do not copy, modify, redistribute, or use the code, manuscript, or figures without permission. Public visibility on GitHub still permits viewing and forking under GitHub's terms. Earlier repository revisions were published with an MIT license, and this notice does not withdraw permissions already granted for those revisions.
