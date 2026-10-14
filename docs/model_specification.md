# Shared model specification

Status: to be agreed before implementation.

## Decisions to document

- Exact pedestrian and wall forces, constants and units
- Preferred speed, radius, mass and relaxation time
- Time step and integration rule
- Room, obstacle and exit geometry
- Exit crossing and inactive-agent rules
- Interaction cutoff and zero-distance safeguards
- Current/next state buffer semantics
- Density grid, empty-cell behavior and congestion thresholds
- Random seed, initialization and numeric precision

All five backends must use the same documented decisions.
