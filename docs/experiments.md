# Benchmark protocol

Use identical equations, initial conditions and step counts across backends.
Run a warm-up and five measured repetitions; report median and variability.
Exclude animation and file writing. Use completed GPU work for timing and CUDA events for kernels.
For MPI total elapsed time, report the slowest process.
Separate simulation time, device transfers and communication where meaningful.

Speedup = sequential time / parallel time.
For homogeneous CPU efficiency, define the processor count explicitly.
For CUDA/hybrid, report CPU/GPU resources; CUDA threads are not equivalent CPU cores.

Initial matrix: crowds 500/1000/2000/5000 if practical; exits 1/2/4 m;
OpenMP threads 1/2/4/8; MPI ranks 1/2/4; CUDA blocks 128/256/512 where supported.

The completed five-backend local benchmark and its timing limits are in
[`hybrid_validation.md`](hybrid_validation.md). Raw runs, summaries and plots
are in `results/benchmarks/all_backends/`. The separate CUDA block-size study
is in `sammit_benchmarks.md`.

The later [report studies](report_studies.md) add measured rank/thread/block
configuration sweeps, CPU parallel efficiency, and a cross-backend simulated
risk study with matched exit-width timing cases.
