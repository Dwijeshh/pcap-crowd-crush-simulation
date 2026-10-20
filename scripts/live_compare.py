"""Run five backends concurrently and display their actual live progress."""

import argparse
import csv
import math
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from benchmark_cuda import make_config


NAMES = ("sequential", "openmp", "mpi", "cuda", "hybrid")
COLORS = {"sequential": "#235789", "openmp": "#f18f01", "mpi": "#6f42a3",
          "cuda": "#2c9f69", "hybrid": "#bd3152"}
REPO = Path(__file__).resolve().parents[1]


def scenario(pedestrians, destination):
    if not 1 <= pedestrians <= 5000:
        raise ValueError("pedestrians must be between 1 and 5000")
    scale = max(1.0, math.sqrt(pedestrians / 100))
    settings = dict(pedestrians=pedestrians, steps=600, snapshot_interval=10,
                    room_width=round(20 * scale, 4), room_height=round(12 * scale, 4),
                    exit_center_y=round(6 * scale, 4), exit_width=round(4 * scale, 4))
    make_config(REPO / "configs" / "wide_exit.cfg", destination, settings)
    return settings


class LiveRun:
    def __init__(self, name, command, prefix, pedestrians):
        self.name, self.prefix, self.pedestrians = name, prefix, pedestrians
        self.started = time.perf_counter()
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.process = subprocess.Popen(command, cwd=REPO, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True,
                                        creationflags=flags)
        self.ended = None
        self.exit_code = None
        self.message = "Starting"
        self.latest = None
        self.total_ms = None
        self.metrics_ms = None
        self._stream = None
        self._pending = ""
        self._frame = []
        self._frame_step = None

    def poll(self):
        path = Path(str(self.prefix) + "_snapshots.csv")
        if self._stream is None and path.exists():
            self._stream = path.open(encoding="utf-8", newline="")
        if self._stream is not None:
            self._pending += self._stream.read()
            lines = self._pending.split("\n")
            self._pending = lines.pop()
            for line in lines:
                if not line or line.startswith("step,"):
                    continue
                fields = next(csv.reader([line]))
                step = int(fields[0])
                if self._frame_step != step:
                    self._frame_step, self._frame = step, []
                self._frame.append((float(fields[3]), float(fields[4]),
                                    int(fields[9])))
                if len(self._frame) == self.pedestrians:
                    self.latest = (step, float(fields[1]), self._frame)
                    self._frame = []
        if self.ended is None and self.process.poll() is not None:
            self.ended = time.perf_counter()
            self.exit_code = self.process.returncode
            stdout, stderr = self.process.communicate()
            self.message = (stdout.strip() if self.exit_code == 0 else
                            stderr.strip() or stdout.strip() or "Process failed")
            run_csv = Path(str(self.prefix) + "_run.csv")
            if self.exit_code == 0 and run_csv.exists():
                with run_csv.open(newline="", encoding="utf-8") as stream:
                    row = next(csv.DictReader(stream))
                self.total_ms = float(row["total_ms"])
                self.metrics_ms = float(row["metrics_ms"])
        return self.latest

    @property
    def wall_seconds(self):
        return (self.ended or time.perf_counter()) - self.started

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self._stream is not None:
            self._stream.close()


class LiveSession:
    def __init__(self, build_dir, pedestrians):
        self.pedestrians = pedestrians
        self.build_dir = build_dir.resolve()
        suffix = ".exe" if sys.platform == "win32" else ""
        programs = {name: self.build_dir / ("pcap_" + name + suffix)
                    for name in NAMES}
        missing = [str(path) for path in programs.values() if not path.is_file()]
        if missing:
            raise FileNotFoundError("Build all five backends first; missing: " + ", ".join(missing))
        mpi = (Path("C:/Program Files/Microsoft MPI/Bin/mpiexec.exe")
               if sys.platform == "win32" else None)
        if mpi is None or not mpi.is_file():
            import shutil
            found = shutil.which("mpiexec") or shutil.which("mpirun")
            if not found:
                raise FileNotFoundError("MPI launcher not found")
            mpi = Path(found)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.directory = REPO / "results" / "tmp" / ("live_" + stamp)
        self.directory.mkdir(parents=True)
        self.config = self.directory / "scenario.cfg"
        self.settings = scenario(pedestrians, self.config)
        self.runs = {}
        for name in NAMES:
            prefix = self.directory / name
            command = [str(programs[name]), str(self.config), str(prefix)]
            if name == "openmp":
                command.append("4")
            elif name == "cuda":
                command.append("256")
            elif name == "hybrid":
                command.extend(("256", "2"))
            if name in ("mpi", "hybrid"):
                command = [str(mpi), "-n", "2", *command]
            try:
                self.runs[name] = LiveRun(name, command, prefix, pedestrians)
            except Exception:
                self.close()
                raise

    def poll(self):
        for run in self.runs.values():
            run.poll()
        return all(run.ended is not None for run in self.runs.values())

    def close(self):
        for run in self.runs.values():
            run.close()


def draw_room(canvas, frame, settings, color):
    canvas.delete("all")
    width, height = 420, 260
    left, top, room_w, room_h = 20, 20, 380, 220
    sx = lambda x: left + x / settings["room_width"] * room_w
    sy = lambda y: top + room_h - y / settings["room_height"] * room_h
    canvas.create_rectangle(left, top, left + room_w, top + room_h,
                            fill="#edf5f8", outline="")
    lo = settings["exit_center_y"] - settings["exit_width"] / 2
    hi = settings["exit_center_y"] + settings["exit_width"] / 2
    canvas.create_line(left, top, left + room_w, top, fill="#18324b", width=2)
    canvas.create_line(left, top, left, top + room_h, fill="#18324b", width=2)
    canvas.create_line(left, top + room_h, left + room_w, top + room_h,
                       fill="#18324b", width=2)
    canvas.create_line(left + room_w, top, left + room_w, sy(hi), fill="#18324b", width=2)
    canvas.create_line(left + room_w, sy(lo), left + room_w, top + room_h,
                       fill="#18324b", width=2)
    canvas.create_line(left + room_w, sy(hi), left + room_w, sy(lo),
                       fill="#ed8b36", width=5)
    if frame is None:
        return
    people = frame[2]
    stride = max(1, math.ceil(len(people) / 500))
    for x, y, active in people[::stride]:
        if active:
            px, py = sx(x), sy(y)
            canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill=color, outline="")


def run_gui(build_dir, pedestrians):
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("PCAP live five-backend simulation")
    root.geometry("1360x920")
    outer = ttk.Frame(root, padding=14)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="Live five-backend simulation", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(outer, text="Each panel follows a running process at its actual wall-clock speed. Fast runs may finish before the first screen refresh. Concurrent runs share CPU and GPU resources; use the benchmark script for fair speed measurements.",
              wraplength=1250).pack(anchor="w", pady=(5, 12))
    controls = ttk.Frame(outer)
    controls.pack(fill="x", pady=(0, 12))
    ttk.Label(controls, text="Number of pedestrians:").pack(side="left")
    count = tk.StringVar(value=str(pedestrians))
    ttk.Spinbox(controls, from_=1, to=5000, textvariable=count, width=9).pack(side="left", padx=8)
    session = [None]
    cards = {}
    board = ttk.Frame(outer)
    board.pack(fill="both", expand=True)
    for i, name in enumerate(NAMES):
        card = ttk.LabelFrame(board, text=name.upper(), padding=8)
        card.grid(row=i // 3, column=i % 3, sticky="nsew", padx=6, pady=6)
        canvas = tk.Canvas(card, width=420, height=260, background="white", highlightthickness=0)
        canvas.pack()
        label = ttk.Label(card, text="Waiting", wraplength=410)
        label.pack(anchor="w", pady=(6, 0))
        cards[name] = (canvas, label)
    for col in range(3):
        board.columnconfigure(col, weight=1)
    for row in range(2):
        board.rowconfigure(row, weight=1)

    def start():
        if session[0] is not None:
            session[0].close()
        try:
            current = LiveSession(build_dir, int(count.get()))
        except (ValueError, FileNotFoundError, OSError) as error:
            messagebox.showerror("Cannot start simulation", str(error))
            return
        session[0] = current
        start_button.configure(state="disabled")
        for name in NAMES:
            canvas, label = cards[name]
            draw_room(canvas, None, current.settings, COLORS[name])
            label.configure(text="Running…")

    start_button = ttk.Button(controls, text="Run all five", command=start)
    start_button.pack(side="left", padx=8)

    def refresh():
        current = session[0]
        if current is not None:
            finished = current.poll()
            for name, run in current.runs.items():
                canvas, label = cards[name]
                if run.latest is not None:
                    draw_room(canvas, run.latest, current.settings, COLORS[name])
                    step, simulated_time, people = run.latest
                    active = sum(person[2] for person in people)
                    detail = (f"Step {step}/600 · model t={simulated_time:.1f}s · "
                              f"{active} active / {len(people)-active} exited")
                else:
                    detail = "Initializing"
                if run.ended is None:
                    label.configure(text=f"{detail}\nRunning {run.wall_seconds:.2f}s wall time")
                elif run.exit_code == 0:
                    label.configure(text=f"{detail}\nFinished in {run.wall_seconds:.3f}s wall time · "
                                         f"backend {run.total_ms:.2f}ms · metrics {run.metrics_ms:.2f}ms")
                else:
                    label.configure(text=f"{detail}\nFailed: {run.message[:200]}")
            if finished:
                start_button.configure(state="normal")
                session[0] = None
                current.close()
        root.after(80, refresh)

    def close():
        if session[0] is not None:
            session[0].close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    refresh()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-dir", type=Path, default=REPO / "build-all")
    parser.add_argument("--pedestrians", type=int, default=2000)
    parser.add_argument("--headless", action="store_true", help="run and report without opening the GUI")
    args = parser.parse_args()
    if args.headless:
        session = LiveSession(args.build_dir, args.pedestrians)
        try:
            while not session.poll():
                time.sleep(0.08)
            for name, run in session.runs.items():
                step = run.latest[0] if run.latest else "none"
                print(f"{name}: exit={run.exit_code}, step={step}, "
                      f"wall={run.wall_seconds:.3f}s, backend={run.total_ms}ms")
                if run.exit_code != 0:
                    print(run.message, file=sys.stderr)
        finally:
            session.close()
    else:
        run_gui(args.build_dir, args.pedestrians)


if __name__ == "__main__":
    main()
