# Experiment results

Commit selected reproducible CSV summaries and final plots here.
Record hardware, software versions, seed, crowd size, steps, backend, rank/thread/GPU counts and block size.
Use warm-up plus five measured repetitions; report median and variability.
Keep large temporary snapshots outside Git.

`benchmarks/all_backends/` contains the 175-run five-backend benchmark:
raw timing rows, medians/quartiles and three SVG plots. Its methodology and
timing boundaries are in `docs/hybrid_validation.md`.

`benchmarks/configuration_study/` contains 145 measured runs across 29
OpenMP, MPI, CUDA, and hybrid configurations, including CPU efficiency and
five SVG figures. `risk_study/` contains 30 backend/scenario summaries,
1,830 metric time-series rows, six SVG figures, and a join to the matching
100-person five-backend timing cases. Methods and limits are in
`docs/report_studies.md`.

The [IEEE report](../report/README.md) uses these committed summaries and
figures. Its numeric agreement values describe backend consistency, not
accuracy against observed pedestrian behavior. Do not use the risk labels as
calibrated injury probabilities.
