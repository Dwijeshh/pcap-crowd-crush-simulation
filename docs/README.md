# Documentation index

Start with the [root README](../README.md) for build, run, live UI, and report
commands. The [IEEE report guide](../report/README.md) explains the paper
source, vector figures, and separate review PDF.

| Document | What it records |
| --- | --- |
| [Model specification](model_specification.md) | Shared movement equations, state, geometry, and output timing |
| [Metrics specification](metrics_specification.md) | Density, speed, congestion, bottleneck, exit flow, and simulated risk rules |
| [Hybrid validation](hybrid_validation.md) | Five-backend correctness checks, hardware, and timing boundaries |
| [Report studies](report_studies.md) | Configuration sweep, CPU efficiency, and exit-width/risk measurements |
| [OpenMP validation](openmp_validation.md) | OpenMP correctness and preliminary performance |
| [CUDA validation](cuda_validation.md) | CUDA correctness and numerical tolerance |
| [CUDA benchmark](sammit_benchmarks.md) | Separate CPU/CUDA and block-size study |
| [Experiment protocol](experiments.md) | Benchmark design and measurement rules |
| [Implementation roadmap](implementation_plan.md) | Historical development sequence |

The committed raw data and plots are indexed in [results](../results/README.md).
Comparisons across backends use one movement model and seed; reported times
have backend-specific timing boundaries. The low/medium/high categories are
uncalibrated simulation indicators, not real-world injury predictions.
