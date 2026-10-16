# CUDA validation on Sammit's RTX 3050

Validated on 16 October 2026 with an NVIDIA GeForce RTX 3050 Laptop GPU,
driver 610.60, CUDA Toolkit 13.4.3 (`nvcc` 13.4.92), Visual Studio Community
2026 (MSVC 19.51), and CMake 4.4.4. The GPU build targeted architecture 86.
CUDA's Visual Studio integration was installed with the toolkit.

On Windows, configure with an explicit toolkit path. A shell opened before
CUDA installation may not inherit the new `CUDA_PATH` environment variable;
open a new terminal or load the machine value as shown below. `cmake` must be
on `PATH` (or replaced with its full executable path).

```powershell
$env:CUDA_PATH = [Environment]::GetEnvironmentVariable('CUDA_PATH', 'Machine')
cmake -S . -B build-gpu -G 'Visual Studio 18 2026' -A x64 -T "cuda=$env:CUDA_PATH" -DCMAKE_CUDA_ARCHITECTURES=86
cmake --build build-gpu --config Release --parallel 4
ctest --test-dir build-gpu -C Release --output-on-failure
New-Item -ItemType Directory -Force results/tmp | Out-Null
foreach ($scenario in @('wide_exit', 'narrow_exit', 'obstacle')) {
    .\build-gpu\Release\pcap_sequential.exe "configs/$scenario.cfg" "results/tmp/${scenario}_cpu"
    .\build-gpu\Release\pcap_cuda.exe "configs/$scenario.cfg" "results/tmp/${scenario}_gpu" 256
    python tests/compare_snapshots.py "results/tmp/${scenario}_cpu_snapshots.csv" "results/tmp/${scenario}_gpu_snapshots.csv"
}
```

The model test passed. Each scenario produced 6,100 snapshot rows per backend,
including the initial state and 60 later snapshots of 100 pedestrians.
The comparison checks every saved agent's active state exactly and requires
each position and velocity component to differ by at most 0.001 in its native
unit (metres or metres per second). No rows exceeded the limit.

| Scenario | Exited, CPU and CUDA | Maximum position difference (m) | Maximum velocity difference (m/s) |
| --- | ---: | ---: | ---: |
| Wide exit | 52 / 100 | 0.0000058 | 0.0000161 |
| Narrow exit | 26 / 100 | 0.0002651 | 0.00078011 |
| Obstacle | 40 / 100 | 0.0000572 | 0.000151217 |

The wide-exit CUDA run also passed at block sizes 128, 256, and 512, with
identical saved GPU states and the same 52 exited agents. The comparator was
checked against mismatched scenario files and returned a failure.

These are correctness checks, not a performance benchmark. The 100-agent
scenarios are too small to establish a GPU speedup, and the CPU and CUDA timing
fields cover different work. See `model_specification.md` for timing boundaries.
