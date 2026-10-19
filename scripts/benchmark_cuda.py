"""Repeatable CPU/CUDA comparison with warm-ups, raw data, and SVG figures."""

import argparse
import csv
import math
import statistics
import subprocess
from collections import defaultdict
from pathlib import Path

from visualize import BLUE, ORANGE, chart


def read_one(path):
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError(f"expected one metadata row in {path}")
    return rows[0]


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_config(template, path, changes):
    lines = template.read_text(encoding="utf-8").splitlines()
    seen = set()
    rewritten = []
    for line in lines:
        key = line.split("#", 1)[0].split("=", 1)[0].strip()
        if key in changes:
            rewritten.append(f"{key}={changes[key]}")
            seen.add(key)
        else:
            rewritten.append(line)
    for key, value in changes.items():
        if key not in seen:
            rewritten.append(f"{key}={value}")
    path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def run(executable, config, prefix, block=None):
    command = [str(executable), str(config), str(prefix)]
    if block is not None:
        command.append(str(block))
    try:
        subprocess.run(command, capture_output=True, text=True, timeout=180, check=True)
        metadata = read_one(Path(str(prefix) + "_run.csv"))
        with Path(str(prefix) + "_summary.csv").open(newline="", encoding="utf-8") as stream:
            summary = list(csv.DictReader(stream))[-1]
        for key in ("total_ms", "kernel_ms", "transfer_ms"):
            value = float(metadata[key])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid {key}: {value}")
        return metadata, summary
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"failed: {' '.join(command)}\n{getattr(error, 'stderr', '')}") from error
    finally:
        for suffix in ("_run.csv", "_summary.csv", "_snapshots.csv"):
            Path(str(prefix) + suffix).unlink(missing_ok=True)


def quartiles(values):
    ordered = sorted(values)
    return (statistics.median(ordered[:len(ordered)//2]),
            statistics.median(ordered[(len(ordered)+1)//2:]))


def aggregate(raw):
    groups = defaultdict(list)
    for row in raw:
        groups[(row["experiment"], row["pedestrians"], row["exit_width"],
                row["backend"], row["block_size"])].append(row)
    result = []
    for (experiment, crowd, width, backend, block), rows in sorted(groups.items()):
        totals = [float(row["total_ms"]) for row in rows]
        q1, q3 = quartiles(totals)
        result.append(dict(experiment=experiment, pedestrians=crowd, exit_width=width,
                           backend=backend, block_size=block, repetitions=len(rows),
                           total_median_ms=statistics.median(totals), total_q1_ms=q1,
                           total_q3_ms=q3, total_min_ms=min(totals), total_max_ms=max(totals),
                           kernel_median_ms=statistics.median(float(row["kernel_ms"]) for row in rows),
                           transfer_median_ms=statistics.median(float(row["transfer_ms"]) for row in rows),
                           exited_min=min(int(row["exited"]) for row in rows),
                           exited_max=max(int(row["exited"]) for row in rows)))
    return result


def figures(summary, output):
    scaling = [row for row in summary if row["experiment"] == "scaling"]
    cpu = {int(row["pedestrians"]): row for row in scaling if row["backend"] == "sequential"}
    gpu = {int(row["pedestrians"]): row for row in scaling
           if row["backend"] == "cuda" and int(row["block_size"]) == 256}
    sizes = sorted(cpu)
    if sizes != sorted(gpu):
        raise ValueError("CPU and CUDA sizes do not match")
    chart(output / "runtime_vs_crowd.svg", "CPU and CUDA runtime (median of 5)",
          "Pedestrians", "Total compute time (ms)",
          [("CPU", [(n, float(cpu[n]["total_median_ms"])) for n in sizes], BLUE),
           ("CUDA 256", [(n, float(gpu[n]["total_median_ms"])) for n in sizes], ORANGE)])
    chart(output / "speedup_vs_crowd.svg", "CUDA speedup vs sequential CPU", "Pedestrians",
          "CPU total / CUDA total",
          [("CUDA 256", [(n, float(cpu[n]["total_median_ms"]) /
                           float(gpu[n]["total_median_ms"])) for n in sizes], ORANGE)])
    colors = {128: BLUE, 256: ORANGE, 512: "#7d5ba6"}
    chart(output / "cuda_block_tuning.svg", "CUDA block size comparison", "Pedestrians",
          "Total compute time (ms)",
          [(str(block), [(int(row["pedestrians"]), float(row["total_median_ms"]))
                         for row in scaling if row["backend"] == "cuda" and
                         int(row["block_size"]) == block], color)
           for block, color in colors.items()])
    widths = [row for row in summary if row["experiment"] == "exit_width" and
              (row["backend"] == "sequential" or int(row["block_size"]) == 256)]
    chart(output / "runtime_vs_exit_width.svg", "Runtime by exit width (median of 5)",
          "Exit width (m)", "Total compute time (ms)",
          [(backend, [(float(row["exit_width"]), float(row["total_median_ms"]))
                      for row in widths if row["backend"] == backend], color)
           for backend, color in (("sequential", BLUE), ("cuda", ORANGE))])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu", type=Path)
    parser.add_argument("--cuda", type=Path)
    parser.add_argument("--output", type=Path, default=Path("results/benchmarks/sammit_cuda"))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--plots-only", action="store_true", help="recreate plots from summary.csv")
    args = parser.parse_args()
    if args.repetitions < 2:
        parser.error("at least two measured repetitions are required")
    args.output.mkdir(parents=True, exist_ok=True)
    if args.plots_only:
        with (args.output / "summary.csv").open(newline="", encoding="utf-8") as stream:
            figures(list(csv.DictReader(stream)), args.output)
        return
    if args.cpu is None or args.cuda is None:
        parser.error("--cpu and --cuda are required for benchmark runs")
    args.cpu = args.cpu.resolve(strict=True)
    args.cuda = args.cuda.resolve(strict=True)
    working = args.output / ".working"
    working.mkdir(exist_ok=True)
    rows = []
    try:
        cases = [("scaling", n, 4, 100, 100, 70) for n in (500, 1000, 2000, 5000)]
        cases += [("exit_width", 100, width, 600, 20, 12) for width in (1, 2, 4)]
        for experiment, crowd, width, steps, room_w, room_h in cases:
            config = working / f"{experiment}_{crowd}_{width}.cfg"
            make_config(Path("configs/wide_exit.cfg"), config,
                        dict(pedestrians=crowd, steps=steps, snapshot_interval=steps,
                             exit_width=width, room_width=room_w, room_height=room_h,
                             exit_center_y=room_h / 2))
            for backend, executable, block in [("sequential", args.cpu, 0)] + [
                    ("cuda", args.cuda, size) for size in (128, 256, 512)]:
                print(f"{experiment}: N={crowd}, width={width}, {backend} {block or ''}", flush=True)
                for repetition in range(args.repetitions + 1):
                    prefix = working / "trial"
                    metadata, summary = run(executable, config, prefix, block or None)
                    if metadata["backend"] != backend or int(metadata["pedestrians"]) != crowd:
                        raise ValueError("backend or crowd size mismatch")
                    if repetition == 0:
                        continue  # warm-up
                    rows.append(dict(experiment=experiment, pedestrians=crowd, exit_width=width,
                                     steps=steps, backend=backend, block_size=block,
                                     repetition=repetition, total_ms=metadata["total_ms"],
                                     kernel_ms=metadata["kernel_ms"],
                                     transfer_ms=metadata["transfer_ms"],
                                     exited=summary["exited"], device_name=metadata["device_name"]))
            config.unlink()
        summary = aggregate(rows)
        exits = defaultdict(set)
        for row in summary:
            if row["exited_min"] != row["exited_max"]:
                raise ValueError("exit count changed between measured repetitions")
            exits[(row["experiment"], row["pedestrians"], row["exit_width"])].add(row["exited_min"])
        if any(len(counts) != 1 for counts in exits.values()):
            raise ValueError("CPU and CUDA exit counts disagree")
        write_csv(args.output / "raw_runs.csv", rows, list(rows[0]))
        write_csv(args.output / "summary.csv", summary, list(summary[0]))
        figures(summary, args.output)
    finally:
        for path in working.iterdir():
            if path.is_file():
                path.unlink()
        working.rmdir()


if __name__ == "__main__":
    main()
