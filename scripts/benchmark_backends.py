"""Repeatable movement benchmarks for available PCAP backends."""

import argparse
import csv
import math
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

from benchmark_cuda import make_config, quartiles, write_csv
from visualize import chart


COLORS = {"sequential": "#235789", "openmp": "#f18f01", "mpi": "#6f42a3",
          "cuda": "#2c9f69", "hybrid": "#bd3152"}
SUFFIXES = ("_run.csv", "_summary.csv", "_snapshots.csv", "_metrics.csv",
            "_cells.csv", "_mpi_timing.csv", "_hybrid_timing.csv")


def read_one(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError(f"expected one row in {path}")
    return rows[0]


def execute(name, executable, mpiexec, config, prefix, args):
    command = [str(executable), str(config), str(prefix)]
    if name == "openmp":
        command.append(str(args.threads))
    elif name == "cuda":
        command.extend((str(args.block), "--no-metrics"))
    elif name == "hybrid":
        command.extend((str(args.block), str(args.hybrid_threads)))
    if name in ("mpi", "hybrid"):
        command = [str(mpiexec), "-n", str(args.ranks), *command]
    try:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=300, check=True)
        run = read_one(Path(str(prefix) + "_run.csv"))
        with Path(str(prefix) + "_summary.csv").open(newline="", encoding="utf-8") as stream:
            final = list(csv.DictReader(stream))[-1]
        elapsed = float(run["total_ms"])
        if not math.isfinite(elapsed) or elapsed < 0 or run["backend"] != name:
            raise ValueError(f"invalid timing/backend from {name}: {run}")
        return run, final
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"{' '.join(command)}\n{error.stdout}\n{error.stderr}") from error
    finally:
        for suffix in SUFFIXES:
            Path(str(prefix) + suffix).unlink(missing_ok=True)


def aggregate(raw):
    grouped = defaultdict(list)
    for row in raw:
        grouped[(row["study"], int(row["pedestrians"]), float(row["exit_width"]),
                 row["backend"])].append(row)
    summary = []
    for (study, crowd, width, backend), rows in sorted(grouped.items()):
        timings = [float(row["total_ms"]) for row in rows]
        exits = {int(row["exited"]) for row in rows}
        if len(exits) != 1:
            raise ValueError(f"non-reproducible exits in {study} {crowd} {width} {backend}")
        q1, q3 = quartiles(timings)
        summary.append(dict(study=study, pedestrians=crowd, exit_width=width,
                            backend=backend, runs=len(rows),
                            total_median_ms=statistics.median(timings),
                            total_q1_ms=q1, total_q3_ms=q3, exited=next(iter(exits))))
    by_case = defaultdict(set)
    for row in summary:
        by_case[(row["study"], row["pedestrians"], row["exit_width"])].add(row["exited"])
    if any(len(exits) != 1 for exits in by_case.values()):
        raise ValueError("backends disagree on exited counts")
    return summary


def figures(summary, output):
    for study, filename, xlabel, xkey in (
            ("crowd", "runtime_vs_crowd.svg", "Pedestrians", "pedestrians"),
            ("exit", "runtime_vs_exit_width.svg", "Exit width (m)", "exit_width")):
        rows = [row for row in summary if row["study"] == study]
        if not rows:
            continue
        names = sorted({row["backend"] for row in rows})
        series = [(name, [(float(row[xkey]), float(row["total_median_ms"]))
                          for row in rows if row["backend"] == name], COLORS[name])
                  for name in names]
        chart(output / filename, "Movement runtime by " + xlabel.lower(), xlabel,
              "Median backend time (ms)", series)
    cpu = {row["pedestrians"]: float(row["total_median_ms"])
           for row in summary if row["study"] == "crowd" and row["backend"] == "sequential"}
    series = [(name, [(float(row["pedestrians"]),
                       cpu[row["pedestrians"]] / float(row["total_median_ms"]))
                      for row in summary if row["study"] == "crowd" and row["backend"] == name],
               COLORS[name]) for name in COLORS if name != "sequential" and
              any(row["backend"] == name and row["study"] == "crowd" for row in summary)]
    if series:
        chart(output / "speedup_vs_crowd.svg", "Movement speedup versus sequential",
              "Pedestrians", "Sequential / backend median", series)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in COLORS:
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--mpiexec", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/benchmarks/all_backends"))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--ranks", type=int, default=2)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--hybrid-threads", type=int, default=2)
    parser.add_argument("--block", type=int, default=256)
    parser.add_argument("--crowds", type=int, nargs="+", default=[500, 1000, 2000, 5000])
    parser.add_argument("--study", choices=["all", "crowd", "exit"], default="all")
    args = parser.parse_args()
    if args.repetitions < 2 or min(args.ranks, args.threads, args.hybrid_threads,
                                   args.block, *args.crowds) < 1:
        parser.error("positive settings and at least two measured repetitions are required")
    programs = {name: getattr(args, name).resolve(strict=True)
                for name in COLORS if getattr(args, name) is not None}
    if "sequential" not in programs:
        parser.error("--sequential is required")
    if any(name in programs for name in ("mpi", "hybrid")) and args.mpiexec is None:
        parser.error("--mpiexec is required for MPI and hybrid")
    mpiexec = args.mpiexec.resolve(strict=True) if args.mpiexec else None
    args.output.mkdir(parents=True, exist_ok=True)
    working = args.output / ".working"
    working.mkdir(exist_ok=True)
    cases = []
    if args.study in ("all", "crowd"):
        cases.extend(("crowd", crowd, 4, 100, 100, 70) for crowd in args.crowds)
    if args.study in ("all", "exit"):
        cases.extend(("exit", 100, width, 600, 20, 12) for width in (1, 2, 4))
    raw = []
    for study, crowd, width, steps, room_width, room_height in cases:
        config = working / "case.cfg"
        make_config(Path("configs/wide_exit.cfg"), config,
                    dict(pedestrians=crowd, steps=steps, snapshot_interval=steps,
                         exit_width=width, room_width=room_width,
                         room_height=room_height, exit_center_y=room_height / 2))
        for repetition in range(args.repetitions + 1):
            for name, executable in programs.items():
                print(f"{study} N={crowd} exit={width}: {name} "
                      f"{'warmup' if repetition == 0 else repetition}", flush=True)
                run, final = execute(name, executable, mpiexec, config,
                                     working / "trial", args)
                if repetition:
                    raw.append(dict(study=study, pedestrians=crowd, exit_width=width,
                                    steps=steps, backend=name, repetition=repetition,
                                    total_ms=run["total_ms"], kernel_ms=run["kernel_ms"],
                                    transfer_ms=run["transfer_ms"],
                                    metrics_ms=run["metrics_ms"], exited=final["exited"],
                                    ranks=args.ranks if name in ("mpi", "hybrid") else 1,
                                    threads=args.hybrid_threads if name == "hybrid" else
                                    args.threads if name == "openmp" else 1,
                                    block=args.block if name in ("cuda", "hybrid") else 0))
    summary = aggregate(raw)
    write_csv(args.output / "raw_runs.csv", raw, list(raw[0]))
    write_csv(args.output / "summary.csv", summary, list(summary[0]))
    figures(summary, args.output)
    print(f"Wrote {len(raw)} measured runs and {len(summary)} summary rows to {args.output}")


if __name__ == "__main__":
    main()
