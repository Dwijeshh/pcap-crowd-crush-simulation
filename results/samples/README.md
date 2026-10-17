# Sammit reference outputs

Generated on 16 October 2026 on Windows with an Intel Core i5-11260H
(12 logical processors) using MSYS2 GCC 13.2.0, `-O2`, C++17. An NVIDIA
GeForce RTX 3050 Laptop GPU (4,096 MiB, driver 610.60) is present, but the
CUDA toolkit/compiler was not installed in this environment. No GPU numbers
are reported or inferred.

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

No speedup chart is included yet because it requires a parallel run with
matching parameters and timing boundaries. `scripts/visualize.py performance`
will generate one when matching CUDA/OpenMP/MPI run CSVs are available.
