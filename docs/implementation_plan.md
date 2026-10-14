# Implementation roadmap

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
