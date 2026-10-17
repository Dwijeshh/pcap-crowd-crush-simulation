# Shared movement model: proposed reference contract

Sammit's sequential and CUDA implementations use the **same** `update_one` function in
`include/model.hpp`. Dwijesh and Ayush should review this proposed contract before
building their backends. It is a deliberately simplified, deterministic model
inspired by the social-force approach of [Helbing, Farkas and Vicsek (2000)](https://doi.org/10.1038/35035023).
It does **not** reproduce their full panic model or provide calibrated injury risk.

## State and units

Positions and radii are metres, velocities m/s, time seconds, mass kg, and
force newtons. IDs are stable zero-based array indices. Each state uses
`x`, `y`, `vx`, `vy`, `preferred_speed`, `radius`, and `active` arrays.
`mass`, `relaxation_time`, and the geometry are shared configuration values.
All arithmetic in the updater uses IEEE 32-bit float. Every step reads one
immutable state and writes each agent's own slot in the next state; buffers
swap only after all agents finish. Inactive agents retain their last state.

## Equations

For active pedestrian `i`, the desired direction is the unit vector from
their centre to `(room_width, clamp(y_i, exit_low+r_i, exit_high-r_i))`.
The acceleration is

```text
a_i = (preferred_speed_i * direction_i - velocity_i) / relaxation_time
      + (sum_j F_ij + sum_w F_iw + F_obstacle) / mass
```

For a pair of centres `i` and `j`, let `d` be their separation,
`q = d - r_i - r_j` their clearance, and `n = (position_i-position_j)/d`.
For `d <= interaction_cutoff`:

```text
F_ij = [interaction_strength * exp(clamp(-q/interaction_range,-20,10))
        + body_stiffness * max(-q,0)] * n
```

For the left, bottom, top, and closed part of the right wall, use the same
form with `wall_strength` and `wall_range`, using the centre-to-wall clearance
minus radius. The circular obstacle uses its surface clearance and the wall
parameters. There is no friction term. For coincident centres, `n` is a
deterministic x-axis direction based on IDs, avoiding division by zero.
All forces use the current state. Semi-implicit Euler advances velocity first,
then position, using the configured `dt`. Speed is capped at `max_speed`.

The room occupies `[0,room_width] x [0,room_height]`. The exit is an opening
in the right boundary centred at `exit_center_y` with width `exit_width`.
The exit event occurs when the centre crosses `x=room_width` with positive
x velocity and the interpolated crossing y lies between
`exit_low + radius` and `exit_high - radius`. The agent becomes inactive.
Other room boundaries are clamped at the radius. The obstacle has a hard
surface projection after Euler integration. Pedestrian contacts remain soft;
some overlap can occur under congestion, so inspect snapshots and do not
interpret overlap as a measured physical compression.

## Initialization and outputs

The sequential reference uses MT19937 with the configured seed. Initial
centres are sampled uniformly in the left 72% of the room and rejected if
they overlap any earlier pedestrian or the obstacle. Initial velocity is zero.
The configuration parser rejects duplicate/unknown keys and invalid geometry.
The snapshot CSV schema is `step,time,id,x,y,vx,vy,preferred_speed,radius,active`.
The summary CSV schema is `step,time,active,exited,simulation_ms`; its rows
match snapshot intervals and the final step. The run CSV contains backend,
configuration identifiers, and timing components. CPU `simulation_ms` sums
only update calls. CUDA `kernel_ms` uses CUDA events, `transfer_ms` times
host/device state copies, and `total_ms` includes device allocation, launches,
synchronization, and transfers but excludes CSV writing. Compare these timing
boundaries explicitly rather than treating unlike totals as a speedup.

Density, speed, congestion thresholds and exit-flow definitions remain owned
by the shared metrics specification. The visualization's 1 m heatmap grid is
descriptive only and is not a risk score. All parallel backends must adopt
the equations, guards and exit rule above before numerical comparison.
