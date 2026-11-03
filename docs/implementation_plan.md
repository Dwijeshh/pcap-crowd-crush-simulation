# Implementation roadmap (historical)

This was the team's original four-week plan. The sequential, OpenMP, MPI,
CUDA, and hybrid implementations, live comparison UI, validation, and
benchmark/risk studies are now implemented. See the [root README](../README.md)
for how to run them, [hybrid validation](hybrid_validation.md) for backend
agreement, [report studies](report_studies.md) for measured results, and the
[IEEE report guide](../report/README.md) for the paper artifacts. The items
below describe development order rather than outstanding tasks.

## Week 1: verified reference

Sammit builds sequential movement and snapshot output.
Dwijesh specifies metrics. Ayush prepares configuration and build infrastructure.
Verify one pedestrian first, then a small crowd.

## Week 2: parallel backends

Dwijesh implements OpenMP; Ayush implements MPI; Sammit implements CUDA.
Start MPI with replicated current state and pedestrian-ID partitions.
Keep standalone CUDA state resident on the GPU between steps.
Compare all versions to the sequential reference.

## Week 3: hybrid

MPI partitions agents and exchanges state. CUDA updates local agents.
OpenMP computes local statistics. MPI combines global statistics.
Measure transfer/communication costs before optimizing.
Test one GPU honestly; multi-GPU scaling requires those resources.

## Week 4: experiments and demonstration

Vary crowd size, exit width, OpenMP threads, MPI ranks and CUDA blocks.
Use fixed steps for timing; measure evacuation completion separately.
Collect density, speed, congestion and exit counts.
Prepare graphs, report and a wide/narrow-exit demonstration.
