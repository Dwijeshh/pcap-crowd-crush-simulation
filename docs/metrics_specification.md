# Shared simulation metrics

All five backends calculate these metrics from their post-update state at
every time step, including step zero. They write a summary
at step zero, each snapshot interval, and the final step. These values are
simulation indicators, not calibrated predictions of injury or crush risk.

## Grid and crowd values

The room is divided into square cells of `metric_cell_size` metres. The final
column and row are clipped to the room boundary, so their actual area is used
for density. Cell `(column,row)` contains centres in its half-open coordinate
interval; a centre exactly on the room's top or right boundary belongs to the
last cell. Inactive pedestrians are excluded.

For each cell, `count` is the number of active pedestrian centres, `density`
is `count / cell_area` in pedestrians per square metre, and `average_speed` is
the arithmetic mean of `sqrt(vx² + vy²)` in metres per second. Empty cells have
zero average speed and are never congested. Room `average_speed` is the mean
over all active pedestrians; `peak_density` is the maximum cell density. If the
crowd is empty, both are zero.

## Congestion and bottleneck

A nonempty cell is congested when its density is at least
`congestion_density_threshold` **and** its average speed is at most
`congestion_speed_threshold`. The defaults are 2 pedestrians/m² and 0.5 m/s.
`consecutive_seconds` accumulates `dt` while a cell remains congested and
resets to zero when it is not. `cumulative_seconds` accumulates all congested
steps. Step zero observes the initial state but adds zero elapsed time.
`congested_cells` counts currently congested cells. The summary's maximum
consecutive and cumulative durations are maxima across all cells.

The bottleneck zone is the part of the room satisfying
`x >= room_width - bottleneck_depth` and
`exit_center_y - exit_width/2 - bottleneck_margin <= y <=
exit_center_y + exit_width/2 + bottleneck_margin`. Its occupancy counts active
pedestrian centres in that zone. The defaults are 2 m depth and 0.5 m margin.
It is a geometric count, not a density or a count of exited pedestrians.

The risk proxy is `low` if no cell is currently congested, `medium` if at
least one cell is congested, and `high` if any currently congested cell has
been continuously congested for at least `high_congestion_seconds` (default
2 s). It does not account for contact force, pressure, or empirical injury
thresholds. Thresholds are configurable experiment parameters and must be
reported with results.

## Exit flow and files

`exited` is the number of inactive pedestrians. `exit_flow_per_second` is
`(exited_now - exited_at_previous_output) / (time_now - time_previous_output)`.
It is zero at step zero. It therefore describes the interval between recorded
rows, not the most recent single update. Values are pedestrians per second.

For output prefix `P`, `P_metrics.csv` has one row per recorded step with the
crowd values, bottleneck occupancy, exit flow, risk category and all six metric
parameters. `P_cells.csv` has one row per grid cell at each recorded step with
count, actual area, density, mean speed, congestion flag and durations. The
usual `P_snapshots.csv` and `P_summary.csv` keep their existing formats.
`P_run.csv` adds the metric parameters, `worker_threads`, and `metrics_ms`.
The latter measures metric sampling separately from movement. CUDA's
`metrics_ms` also includes the state downloads needed for host metric
sampling. Its optional `--no-metrics` mode omits metric and cell CSVs for
movement-only benchmarking. Hybrid computes range-local values with OpenMP
and combines them across ranks with MPI. CSV writing is outside both timers.
CPU and GPU positions can differ slightly; a pedestrian near a cell edge can
therefore land in adjacent cells even when the snapshot comparison passes.
