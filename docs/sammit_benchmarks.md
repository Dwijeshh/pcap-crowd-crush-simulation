# Sammit's CPU/CUDA benchmark and final figures

Measured 18 October 2026 on a Windows laptop with Intel Core i5-11260H
(12 logical processors), NVIDIA GeForce RTX 3050 Laptop GPU (4 GiB), driver
610.60, CUDA Toolkit 13.4.3, Visual Studio Community 2026 (MSVC 19.51),
and CMake 4.4.4. Release binaries targeted CUDA architecture 86.

## Method

The benchmark script runs one warm-up followed by five measured repetitions
for each case. It uses seed 42, `dt=0.02`, the common model and force settings,
and saves only the initial and final snapshot. Scaling uses 500, 1,000, 2,000,
and 5,000 pedestrians in the same 100 × 70 m room for 100 steps; the exit is
4 m wide. The separate bottleneck study uses 100 pedestrians in a 20 × 12 m
room for 600 steps with 1, 2, and 4 m exits. The latter changes only the exit
width. CUDA block sizes 128, 256, and 512 are measured for every case.

The run-level CPU total includes the next-state allocation and timed update
calls. The run-level CUDA total includes device allocation, upload, kernel
launch and synchronization, and final download. Both exclude initialization,
configuration parsing, CSV writing, and visualization. CUDA event kernel time
and host-measured transfer time are reported separately in the data. These
totals reflect the work needed by each backend after an identical initial state
has been generated. Timings are local to this machine; do not compare them to
the older GCC sample timings in `results/samples/`.

For every case, the five measured repetitions within each backend agreed on
the number exited. CPU and all CUDA block sizes also agreed: 0 exits in the
short scaling runs, and 26, 44, and 52 exits for widths 1, 2, and 4 m. The
zero exits in scaling runs reflect the large fixed room and short 2 s simulated
duration; that study measures compute scaling, while the exit-width study
measures the bottleneck scenarios. Detailed snapshot comparisons for the
100-person scenarios and a 5,000-person pilot are in `cuda_validation.md`.

## Scaling results

Medians of five measured runs; brackets contain first and third quartiles
(ms). Speedup is CPU median divided by CUDA median at block size 256.

| Pedestrians | CPU total ms | CUDA 256 total ms | Speedup |
| ---: | ---: | ---: | ---: |
| 500 | 58.66 [53.67, 68.79] | 83.60 [76.99, 88.54] | 0.70× |
| 1,000 | 215.86 [202.53, 234.20] | 74.58 [71.78, 90.22] | 2.89× |
| 2,000 | 581.67 [579.65, 605.80] | 88.72 [88.30, 97.70] | 6.56× |
| 5,000 | 3,515.48 [3,461.77, 3,651.97] | 132.56 [128.77, 136.80] | 26.52× |

The CUDA total at 500 pedestrians is slower because setup and launch overhead
outweigh the parallel update. At 5,000, the CPU interaction work dominates,
and the GPU is substantially faster. This is a measured local result for this
model and hardware, not a physical crowd-safety prediction.

At 5,000 pedestrians, median CUDA totals for blocks 128/256/512 were
129.83/132.56/130.05 ms. The difference is small relative to run variability;
the graph shows all sizes rather than claiming one universally optimal block.
The 256-block kernel median was 75.30 ms and transfer median was 0.45 ms.
CUDA total includes launch, synchronization, and allocation
overhead in addition to kernel and transfer time.

## Exit-width results

For widths 1, 2, and 4 m respectively, CPU median totals were 23.53, 27.06,
and 19.62 ms; CUDA 256 median totals were 89.37, 90.81, and 82.72 ms. The
100-person case remains CPU-faster. Exit counts increased from 26 to 44 to
52 over the fixed 12 s simulated duration. Runtime need not vary monotonically
with exit width because the number of active interactions changes over time.

## Artifacts and reproduction

The measured [raw runs](../results/benchmarks/sammit_cuda/raw_runs.csv) contain
140 observations (7 cases × 4 backend/block configurations × 5 runs). The
[summary](../results/benchmarks/sammit_cuda/summary.csv) contains medians,
quartiles, minima, maxima, kernel and transfer medians, and exit counts.

Figures: [runtime vs crowd](../results/benchmarks/sammit_cuda/runtime_vs_crowd.svg),
[speedup](../results/benchmarks/sammit_cuda/speedup_vs_crowd.svg),
[CUDA block tuning](../results/benchmarks/sammit_cuda/cuda_block_tuning.svg),
and [runtime vs exit width](../results/benchmarks/sammit_cuda/runtime_vs_exit_width.svg).
The existing [reference visuals](../results/samples/) include the animation,
density heatmap, and density/exit-flow plots.

From the repository root after a CUDA-enabled Release build:

```powershell
python scripts/benchmark_cuda.py --cpu build-gpu/Release/pcap_sequential.exe --cuda build-gpu/Release/pcap_cuda.exe
```

The script checks process success, timing values, exit count stability, and
CPU/CUDA exit count agreement. To redraw figures from committed summaries:

```powershell
python scripts/benchmark_cuda.py --plots-only
```

OpenMP, MPI, and hybrid results require the other team members' completed
backends. These figures make no speedup or correctness claim for those paths.
