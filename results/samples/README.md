# Sammit reference outputs

Generated on 16 October 2026 on Windows with an Intel Core i5-11260H
(12 logical processors) using MSYS2 GCC 13.2.0, `-O2`, C++17. These files
predate installation of the CUDA toolkit. Later measured GPU results are in
`docs/sammit_benchmarks.md` and `results/benchmarks/sammit_cuda/`.

The locally generated wide, narrow and obstacle snapshots use the committed scenario files.
After 600 steps (12 s), 52, 26 and 40 of 100 pedestrians had exited,
respectively. The animation, heatmap, and time-series plots are generated
from those CSVs. The large snapshot CSVs are omitted from Git but can be
recreated with the commands in the root README. The SVGs and HTML are
illustrative simulation outputs, not
validated physical crowd-risk estimates.

`sequential_scaling.csv` contains five measured repetitions for each of
25, 50, 100 and 200 pedestrians after one warm-up per size. The room,
forces, seed, 300 steps, and final-only snapshot interval were held fixed.
The median update times were 0.8101, 2.5296, 9.4107 and 35.8195 ms.
Only update calls were timed; initialization, CSV writing and plotting were
excluded. The plot uses those medians. These short runs are a local
reference, not a cross-machine benchmark.

These legacy sample timings cover update calls only. The later CPU/CUDA
comparison uses run-level compute totals with aligned exclusions, so do not
combine the two datasets into one speedup calculation.
