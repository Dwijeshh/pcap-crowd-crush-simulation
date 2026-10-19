# Experiment results

Commit selected reproducible CSV summaries and final plots here.
Record hardware, software versions, seed, crowd size, steps, backend, rank/thread/GPU counts and block size.
Use warm-up plus five measured repetitions; report median and variability.
Keep large temporary snapshots outside Git.

`benchmarks/all_backends/` contains the 175-run five-backend benchmark:
raw timing rows, medians/quartiles and three SVG plots. Its methodology and
timing boundaries are in `docs/hybrid_validation.md`.
