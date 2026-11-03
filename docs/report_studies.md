# Report studies: configuration, efficiency, and simulated risk

Run on 1 November 2026 on a Windows 11 laptop with an Intel Core i7-12650H
(10 physical cores, 16 logical processors), approximately 16 GiB RAM, and one
NVIDIA GeForce RTX 3050 Laptop GPU (4 GiB). The local build uses CUDA Toolkit
13.1, Microsoft MPI, and MSVC. The GPU is shared when hybrid uses multiple MPI
ranks. These are local measurements, not multi-node or multi-GPU results.

Both studies use the shared movement model, seed 42, and a 0.02 s time step.
Raw data and generated figures are committed under `results/`. Run the commands
below from the repository root after building all five backends.

## Parallel-configuration sweep

The fixed workload has 2,000 pedestrians in a 100 x 70 m room, a 4 m exit,
and 100 steps (2 s of simulated time). It isolates compute costs; no pedestrian
reaches the exit within this short run. Every configuration receives one warmup
and five measured repetitions. The 29 configurations are:

- Sequential reference: one process.
- OpenMP: 1, 2, 4, and 8 threads.
- MPI: 1, 2, and 4 ranks.
- CUDA: blocks of 128, 256, and 512 threads.
- Hybrid: 1, 2, and 4 MPI ranks x 1 and 2 OpenMP threads per rank x CUDA blocks
  of 128, 256, and 512 threads.

The [145 measured runs](../results/benchmarks/configuration_study/raw_runs.csv),
[29 median/quartile rows](../results/benchmarks/configuration_study/summary.csv),
and SVG figures are in `results/benchmarks/configuration_study/`. The figures
cover [OpenMP threads](../results/benchmarks/configuration_study/openmp_threads.svg),
[MPI ranks](../results/benchmarks/configuration_study/mpi_ranks.svg),
[CUDA blocks](../results/benchmarks/configuration_study/cuda_blocks.svg),
[hybrid combinations](../results/benchmarks/configuration_study/hybrid_configurations.svg),
and [CPU parallel efficiency](../results/benchmarks/configuration_study/cpu_parallel_efficiency.svg).

For OpenMP and MPI, `cpu_update_speedup` is the sequential median update time
divided by the backend median update time from the final summary row.
`cpu_parallel_efficiency` divides that speedup by the OpenMP thread count or
MPI rank count. The MPI update includes communication. These efficiency
figures describe this fixed workload and this machine. CUDA and hybrid have
blank CPU-efficiency cells because a CUDA thread, an MPI rank, and a CPU core
are not interchangeable processing units. `total_speedup_vs_sequential` is
provided for all backends as an indicative reported-time ratio; the backend
timing scopes differ as described in [hybrid validation](hybrid_validation.md).

| CPU configuration | Median update (ms) | Update speedup | Parallel efficiency |
| --- | ---: | ---: | ---: |
| Sequential | 491.04 | 1.00 | 1.00 |
| OpenMP, 2 threads | 246.86 | 1.99 | 0.99 |
| OpenMP, 4 threads | 130.14 | 3.77 | 0.94 |
| OpenMP, 8 threads | 146.88 | 3.34 | 0.42 |
| MPI, 2 ranks | 247.27 | 1.99 | 0.99 |
| MPI, 4 ranks | 150.23 | 3.27 | 0.82 |

On this workload, OpenMP improves through four threads, while eight threads
have lower measured efficiency. CUDA's block-size medians were 75.10, 76.99,
and 81.57 ms for blocks 128, 256, and 512; their quartile ranges overlap, so
this is not evidence of a universal best block size. Within the hybrid backend,
the 256-block, two-thread-per-rank median rose from 55.02 ms at one rank to
166.84 ms at two ranks and 342.09 ms at four ranks. All ranks share one GPU,
and per-step transfer and MPI communication costs dominate this case.

Reproduce the study with:

```powershell
python scripts\report_studies.py parallelism --build-dir build-all
```

## Exit-width and simulated-risk study

The risk study uses 100 and 200 pedestrians in the same 20 x 12 m room, with
exit widths of 1, 2, and 4 m, 600 steps (12 s), and a saved metric row every
10 steps (0.2 s). All five backends run each of the six scenarios with metric
collection enabled. The 30 backend/scenario summaries are in
[summary.csv](../results/risk_study/summary.csv); all 1,830 recorded metric
rows are in [timeseries.csv](../results/risk_study/timeseries.csv). For each
scenario, the five backends agreed on the recorded categories and integer
counts, and floating summary metrics differed from sequential by at most
0.001. The [figures](../results/risk_study/) show exit counts, recorded peak
density, cumulative cell congestion, average room speed, and density over time.

Selected sequential results (all backends agree within the comparison rules):

| People | Exit (m) | Exited at 12 s | Recorded peak density (people/m2) | Max cell cumulative congestion (s) | Highest recorded category |
| ---: | ---: | ---: | ---: | ---: | --- |
| 100 | 1 | 26 | 6 | 6.34 | high |
| 100 | 2 | 44 | 4 | 2.58 | high |
| 100 | 4 | 52 | 3 | 2.06 | medium |
| 200 | 1 | 46 | 7 | 6.92 | high |
| 200 | 2 | 76 | 6 | 6.10 | high |
| 200 | 4 | 97 | 5 | 5.34 | high |

Within these scenarios, narrower exits coincide with fewer exits, greater
recorded peak density, and longer cumulative cell congestion. The mean room
speed also rises with exit width in both crowd sizes; its exact values are in
the summary CSV. This is an observation from the configured model and seed,
not a calibrated injury or real-world crush-risk estimate. The thresholds and
category rules are defined in [metrics specification](metrics_specification.md).
`recorded_peak_density` is the maximum among the 0.2 s saved samples, whereas
cell congestion duration accumulates at every 0.02 s simulation step.

The [risk/performance join](../results/risk_study/risk_performance.csv) pairs
the 100-person cases with the matching exit-width cases from the earlier
five-backend benchmark. It puts risk indicators and five-run median backend
times in one table for report analysis. The timing measurements were made on
19 October 2026, while the risk metrics were regenerated on 1 November 2026.
CUDA's benchmark path disabled metric sampling; the risk runs enabled it.
Use the join to discuss matching scenarios, not as evidence that risk metrics
change execution speed or that all timing scopes are identical.

Reproduce the study with:

```powershell
python scripts\report_studies.py risk --build-dir build-all
```

## Use in the IEEE report

The [IEEEtran manuscript](../report/ieee/main.tex) discusses this sweep
alongside the earlier five-backend benchmark in
[hybrid validation](hybrid_validation.md). Its vector architecture and runtime
figures are generated by `python report/ieee/build_figures.py`. The
[report guide](../report/README.md) explains the editable source, compiled
preview, and separate review PDF.

Numerical agreement with the sequential backend checks implementation
consistency; it is not accuracy against recorded pedestrian trajectories.
The 100-step scaling cases are too short for evacuation outcomes, while the
12-second exit-width cases are suitable for the reported congestion and exit
observations. Peak memory and user satisfaction were not measured. A future
study would need measured trajectories, repeated seeds, consistent end-to-end
timing boundaries, and memory profiling before making broader claims.
