"""Reproducible parallel-configuration and simulated-risk studies for the report."""

import argparse
import csv
import statistics
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from benchmark_backends import execute
from benchmark_cuda import make_config, quartiles, write_csv
from visualize import chart


REPO = Path(__file__).resolve().parents[1]
COLORS = {"sequential": "#235789", "openmp": "#f18f01", "mpi": "#6f42a3",
          "cuda": "#2c9f69", "hybrid": "#bd3152"}
BACKENDS = tuple(COLORS)
RISK_FLOATS = ("time", "peak_density", "average_speed", "max_consecutive_seconds",
               "max_cumulative_seconds", "exit_flow_per_second")
RISK_EXACT = ("step", "active", "exited", "bottleneck_occupancy",
              "congested_cells", "risk_category")
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def programs(build_dir):
    suffix = ".exe" if sys.platform == "win32" else ""
    paths = {name: (build_dir / ("pcap_" + name + suffix)).resolve()
             for name in BACKENDS}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("build all five backends first: " + ", ".join(missing))
    return paths


def variants():
    result = [("sequential", 1, 1, 0)]
    result += [("openmp", 1, threads, 0) for threads in (1, 2, 4, 8)]
    result += [("mpi", ranks, 1, 0) for ranks in (1, 2, 4)]
    result += [("cuda", 1, 1, block) for block in (128, 256, 512)]
    result += [("hybrid", ranks, threads, block)
               for ranks in (1, 2, 4) for threads in (1, 2)
               for block in (128, 256, 512)]
    return result


def summarize_parallelism(raw):
    groups = defaultdict(list)
    for row in raw:
        groups[(row["backend"], row["ranks"], row["threads"], row["block"])].append(row)
    baseline = groups[("sequential", 1, 1, 0)]
    serial_update = statistics.median(row["update_ms"] for row in baseline)
    serial_total = statistics.median(row["total_ms"] for row in baseline)
    summaries = []
    for (backend, ranks, threads, block), rows in sorted(groups.items()):
        updates = [row["update_ms"] for row in rows]
        totals = [row["total_ms"] for row in rows]
        if len({row["exited"] for row in rows}) != 1:
            raise ValueError(f"exit counts changed for {backend}/{ranks}/{threads}/{block}")
        q1, q3 = quartiles(totals)
        update_median = statistics.median(updates)
        total_median = statistics.median(totals)
        cpu_speedup = (serial_update / update_median
                       if backend in ("sequential", "openmp", "mpi") else None)
        workers = threads if backend == "openmp" else ranks
        summaries.append(dict(backend=backend, ranks=ranks, threads=threads,
                              block=block, runs=len(rows), exited=rows[0]["exited"],
                              update_median_ms=update_median,
                              total_median_ms=total_median,
                              total_q1_ms=q1, total_q3_ms=q3,
                              total_speedup_vs_sequential=serial_total / total_median,
                              cpu_update_speedup=cpu_speedup if cpu_speedup is not None else "",
                              cpu_parallel_efficiency=cpu_speedup / workers
                              if cpu_speedup is not None else ""))
    if len({row["exited"] for row in summaries}) != 1:
        raise ValueError("backends disagree on exit count")
    return summaries


def parallelism_figures(rows, output):
    by_backend = defaultdict(list)
    for row in rows:
        by_backend[row["backend"]].append(row)
    for backend, xkey, filename, xlabel, ylabel, field in (
            ("openmp", "threads", "openmp_threads.svg", "OpenMP threads",
             "Median update time (ms)", "update_median_ms"),
            ("mpi", "ranks", "mpi_ranks.svg", "MPI ranks",
             "Median update + communication (ms)", "update_median_ms"),
            ("cuda", "block", "cuda_blocks.svg", "CUDA block size",
             "Median reported total (ms)", "total_median_ms")):
        chart(output / filename, f"{backend.upper()} configuration sweep", xlabel, ylabel,
              [(backend, [(row[xkey], row[field]) for row in by_backend[backend]],
                COLORS[backend])])
    chart(output / "cpu_parallel_efficiency.svg", "CPU parallel efficiency",
          "Threads or MPI ranks", "Sequential update / parallel update / workers",
          [(name, [(row["threads" if name == "openmp" else "ranks"],
                    row["cpu_parallel_efficiency"]) for row in by_backend[name]],
            COLORS[name]) for name in ("openmp", "mpi")], y_domain=(0, 1.2))
    hybrid = by_backend["hybrid"]
    palette = ("#235789", "#f18f01", "#6f42a3", "#2c9f69", "#bd3152", "#78909c")
    combos = [(r, t) for r in (1, 2, 4) for t in (1, 2)]
    chart(output / "hybrid_configurations.svg", "Hybrid MPI/OpenMP/CUDA sweep",
          "CUDA block size", "Median reported total (ms)",
          [(f"{r} rank(s), {t} thread(s)",
            [(row["block"], row["total_median_ms"]) for row in hybrid
             if row["ranks"] == r and row["threads"] == t], palette[i])
           for i, (r, t) in enumerate(combos)])


def parallelism(args, paths):
    output = args.output or REPO / "results" / "benchmarks" / "configuration_study"
    output.mkdir(parents=True, exist_ok=True)
    working = output / ".working"
    working.mkdir(exist_ok=True)
    config = working / "case.cfg"
    make_config(REPO / "configs" / "wide_exit.cfg", config,
                dict(pedestrians=args.pedestrians, steps=args.steps,
                     snapshot_interval=args.steps, room_width=100, room_height=70,
                     exit_center_y=35, exit_width=4))
    rows = []
    for repetition in range(args.repetitions + 1):
        for backend, ranks, threads, block in variants():
            print(f"{backend} ranks={ranks} threads={threads} block={block} "
                  f"{'warmup' if repetition == 0 else repetition}", flush=True)
            settings = SimpleNamespace(ranks=ranks, threads=threads,
                                       hybrid_threads=threads, block=block)
            run, final = execute(backend, paths[backend], args.mpiexec,
                                 config, working / "trial", settings)
            if repetition:
                rows.append(dict(backend=backend, ranks=ranks, threads=threads,
                                 block=block, repetition=repetition,
                                 pedestrians=args.pedestrians, steps=args.steps,
                                 update_ms=float(final["simulation_ms"]),
                                 total_ms=float(run["total_ms"]),
                                 kernel_ms=float(run["kernel_ms"]),
                                 transfer_ms=float(run["transfer_ms"]),
                                 metrics_ms=float(run["metrics_ms"]),
                                 exited=int(final["exited"])))
    summaries = summarize_parallelism(rows)
    write_csv(output / "raw_runs.csv", rows, list(rows[0]))
    write_csv(output / "summary.csv", summaries, list(summaries[0]))
    parallelism_figures(summaries, output)
    config.unlink()
    working.rmdir()
    print(f"Saved {len(rows)} measured runs and {len(summaries)} configurations to {output}")


def compare_risk(reference, candidate, backend, tolerance=0.001):
    if len(reference) != len(candidate):
        raise ValueError(f"{backend}: risk row count differs")
    for a, b in zip(reference, candidate):
        if any(a[key] != b[key] for key in RISK_EXACT):
            raise ValueError(f"{backend}: risk/category/count differs at step {a['step']}")
        for key in RISK_FLOATS:
            if abs(float(a[key]) - float(b[key])) > tolerance:
                raise ValueError(f"{backend}: {key} differs at step {a['step']}")


def risk_summary(crowd, width, backend, rows):
    ordered = sorted(rows, key=lambda row: int(row["step"]))
    peak = max(float(row["peak_density"]) for row in ordered)
    return dict(pedestrians=crowd, exit_width=width, backend=backend,
                recorded_steps=len(ordered), final_exited=int(ordered[-1]["exited"]),
                recorded_peak_density=peak,
                recorded_mean_speed=statistics.mean(float(row["average_speed"])
                                                    for row in ordered[1:]),
                max_congested_cells=max(int(row["congested_cells"]) for row in ordered),
                max_bottleneck_occupancy=max(int(row["bottleneck_occupancy"])
                                         for row in ordered),
                max_cell_cumulative_congestion_seconds=max(
                    float(row["max_cumulative_seconds"]) for row in ordered),
                max_cell_consecutive_congestion_seconds=max(
                    float(row["max_consecutive_seconds"]) for row in ordered),
                recorded_peak_exit_flow_per_second=max(
                    float(row["exit_flow_per_second"]) for row in ordered),
                highest_recorded_risk=max((row["risk_category"] for row in ordered),
                                          key=RISK_ORDER.get))


def risk_figures(summaries, timeseries, output):
    sequential = [row for row in summaries if row["backend"] == "sequential"]
    palette = ("#235789", "#bd3152", "#f18f01", "#2c9f69", "#6f42a3")
    crowds = sorted({row["pedestrians"] for row in sequential})
    crowd_colors = {crowd: palette[i % len(palette)] for i, crowd in enumerate(crowds)}
    for field, filename, ylabel in (
            ("final_exited", "exited_vs_exit_width.svg", "Exited pedestrians after 12 s"),
            ("recorded_peak_density", "density_vs_exit_width.svg", "Recorded peak density (people/m²)"),
            ("max_cell_cumulative_congestion_seconds", "congestion_vs_exit_width.svg",
             "Maximum cumulative cell congestion (s)"),
            ("recorded_mean_speed", "speed_vs_exit_width.svg", "Mean room speed (m/s)")):
        chart(output / filename, ylabel + " by exit width", "Exit width (m)", ylabel,
              [(f"{crowd} pedestrians",
                [(row["exit_width"], row[field]) for row in sequential
                 if row["pedestrians"] == crowd], crowd_colors[crowd])
               for crowd in crowds])
    for crowd in crowds:
        chart(output / f"density_over_time_{crowd}.svg", f"Density over time: {crowd} pedestrians",
              "Simulated time (s)", "Peak cell density (people/m²)",
              [(f"{width} m exit",
                [(float(row["time"]), float(row["peak_density"])) for row in timeseries
                 if row["pedestrians"] == crowd and row["exit_width"] == width
                 and row["backend"] == "sequential"], color)
               for width, color in ((1, "#bd3152"), (2, "#f18f01"), (4, "#235789"))])


def link_risk_to_benchmarks(summaries, output):
    """Match the 100-person risk scenarios to the existing repeated timing cases."""
    benchmark_path = REPO / "results" / "benchmarks" / "all_backends" / "summary.csv"
    measured = {(row["backend"], float(row["exit_width"])): row
                for row in read_csv(benchmark_path)
                if row["study"] == "exit" and int(row["pedestrians"]) == 100}
    linked = []
    for risk_row in summaries:
        if int(risk_row["pedestrians"]) != 100:
            continue
        key = (risk_row["backend"], float(risk_row["exit_width"]))
        if key not in measured:
            raise ValueError(f"missing repeated timing case for {key}")
        timing = measured[key]
        linked.append(dict(pedestrians=100, exit_width=risk_row["exit_width"],
                           backend=risk_row["backend"],
                           benchmark_runs=int(timing["runs"]),
                           benchmark_total_median_ms=float(timing["total_median_ms"]),
                           benchmark_total_q1_ms=float(timing["total_q1_ms"]),
                           benchmark_total_q3_ms=float(timing["total_q3_ms"]),
                           final_exited=risk_row["final_exited"],
                           recorded_peak_density=risk_row["recorded_peak_density"],
                           recorded_mean_speed=risk_row["recorded_mean_speed"],
                           max_cell_cumulative_congestion_seconds=risk_row[
                               "max_cell_cumulative_congestion_seconds"],
                           highest_recorded_risk=risk_row["highest_recorded_risk"]))
    write_csv(output / "risk_performance.csv", linked, list(linked[0]))
    return linked


def risk(args, paths):
    output = args.output or REPO / "results" / "risk_study"
    output.mkdir(parents=True, exist_ok=True)
    working = output / ".working"
    working.mkdir(exist_ok=True)
    summaries, timeseries = [], []
    for crowd in args.crowds:
        for width in (1, 2, 4):
            config = working / "case.cfg"
            make_config(REPO / "configs" / "wide_exit.cfg", config,
                        dict(pedestrians=crowd, exit_width=width, steps=600,
                             snapshot_interval=10, room_width=20, room_height=12,
                             exit_center_y=6))
            reference = None
            for backend in BACKENDS:
                prefix = working / backend
                command = [str(paths[backend]), str(config), str(prefix)]
                if backend == "openmp":
                    command.append("4")
                elif backend == "cuda":
                    command.append("256")
                elif backend == "hybrid":
                    command.extend(("256", "2"))
                if backend in ("mpi", "hybrid"):
                    command = [str(args.mpiexec), "-n", "2", *command]
                print(f"risk N={crowd} width={width}: {backend}", flush=True)
                completed = subprocess.run(command, cwd=REPO, capture_output=True,
                                           text=True, timeout=180)
                if completed.returncode:
                    raise RuntimeError(f"{backend}: {completed.stderr or completed.stdout}")
                rows = read_csv(Path(str(prefix) + "_metrics.csv"))
                if reference is None:
                    reference = rows
                else:
                    compare_risk(reference, rows, backend)
                summaries.append(risk_summary(crowd, width, backend, rows))
                timeseries.extend(dict(pedestrians=crowd, exit_width=width,
                                       backend=backend, **row) for row in rows)
                for suffix in ("_run.csv", "_summary.csv", "_snapshots.csv",
                               "_metrics.csv", "_cells.csv", "_mpi_timing.csv",
                               "_hybrid_timing.csv"):
                    Path(str(prefix) + suffix).unlink(missing_ok=True)
            config.unlink()
    write_csv(output / "summary.csv", summaries, list(summaries[0]))
    write_csv(output / "timeseries.csv", timeseries, list(timeseries[0]))
    if 100 in args.crowds:
        link_risk_to_benchmarks(summaries, output)
    risk_figures(summaries, timeseries, output)
    working.rmdir()
    print(f"Saved {len(summaries)} backend/scenario summaries and "
          f"{len(timeseries)} time-series rows to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("study", choices=("parallelism", "risk"))
    parser.add_argument("--build-dir", type=Path, default=REPO / "build-all")
    parser.add_argument("--mpiexec", type=Path,
                        default=Path("C:/Program Files/Microsoft MPI/Bin/mpiexec.exe"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--pedestrians", type=int, default=2000)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--crowds", type=int, nargs="+", default=(100, 200))
    args = parser.parse_args()
    if args.repetitions < 2 or args.pedestrians < 1 or args.steps < 1 or \
            not args.crowds or any(crowd < 1 for crowd in args.crowds):
        parser.error("positive counts and at least two measured repetitions are required")
    args.mpiexec = args.mpiexec.resolve(strict=True)
    paths = programs(args.build_dir)
    if args.study == "parallelism":
        parallelism(args, paths)
    else:
        risk(args, paths)


if __name__ == "__main__":
    main()
