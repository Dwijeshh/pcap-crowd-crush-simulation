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
    max_steps = min(12000, max(6000, math.ceil(1.5 * 20 * scale / 1.3 / 0.02)))
    settings = dict(pedestrians=pedestrians, steps=max_steps, snapshot_interval=25,
                    stop_when_empty=1,
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
        self.history = []
        self.total_ms = None
        self.metrics_ms = None
        self._stream = None
        self._pending = ""
        self._frame = []
        self._frame_step = None
        self._active = 0
        self._sample_stride = max(1, math.ceil(pedestrians / 500))
        self._rows = 0

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
                fields = line.split(",")
                step = int(fields[0])
                if self._frame_step != step:
                    self._frame_step, self._frame = step, []
                    self._active = self._rows = 0
                active = int(fields[9])
                self._active += active
                if self._rows % self._sample_stride == 0:
                    self._frame.append((float(fields[3]), float(fields[4]), active))
                self._rows += 1
                if self._rows == self.pedestrians:
                    self.latest = (step, float(fields[1]), self._frame, self._active)
                    self.history.append(self.latest)
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
    for x, y, active in people:
        if active:
            px, py = sx(x), sy(y)
            canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill=color, outline="")


def run_gui(build_dir, pedestrians):
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("PCAP live five-backend simulation")
    root.geometry("1380x980")
    outer = ttk.Frame(root, padding=14)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="Live five-backend simulation", font=("Segoe UI", 18, "bold")).pack(anchor="w")
    ttk.Label(outer, text="Each panel follows its process at actual wall-clock speed. Seek, Back and Forward inspect recorded frames while the process keeps running; Live returns to the newest frame. Concurrent runs share CPU and GPU resources; use the benchmark script for fair speed measurements.",
              wraplength=1250).pack(anchor="w", pady=(5, 12))
    controls = ttk.Frame(outer)
    controls.pack(fill="x", pady=(0, 12))
    ttk.Label(controls, text="Number of pedestrians:").pack(side="left")
    count = tk.StringVar(value=str(pedestrians))
    ttk.Spinbox(controls, from_=1, to=5000, textvariable=count, width=9).pack(side="left", padx=8)
    session = [None]
    completed = [False]
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
        seekbar = ttk.Scale(card, from_=0, to=1, orient="horizontal")
        seekbar.pack(fill="x", pady=(7, 0))
        buttons = ttk.Frame(card)
        buttons.pack(fill="x", pady=(4, 0))
        ttk.Button(buttons, text="◀ Back", command=lambda n=name: move(n, -1)).pack(side="left")
        ttk.Button(buttons, text="Forward ▶", command=lambda n=name: move(n, 1)).pack(side="left", padx=5)
        ttk.Button(buttons, text="Live", command=lambda n=name: go_live(n)).pack(side="left")
        seekbar.configure(command=lambda value, n=name: seek(n, value))
        cards[name] = dict(canvas=canvas, label=label, seekbar=seekbar,
                           follow=True, index=0, shown=None, updating=False)
    for col in range(3):
        board.columnconfigure(col, weight=1)
    for row in range(2):
        board.rowconfigure(row, weight=1)

    def seek(name, value):
        card = cards[name]
        current = session[0]
        if card["updating"] or current is None:
            return
        history = current.runs[name].history
        if history:
            card["index"] = min(len(history) - 1, max(0, round(float(value))))
            card["follow"] = False

    def move(name, direction):
        current = session[0]
        if current is None:
            return
        card = cards[name]
        history = current.runs[name].history
        if history:
            card["index"] = min(len(history) - 1, max(0, card["index"] + direction))
            card["follow"] = False

    def go_live(name):
        card = cards[name]
        card["follow"] = True

    def start():
        if session[0] is not None:
            session[0].close()
        try:
            current = LiveSession(build_dir, int(count.get()))
        except (ValueError, FileNotFoundError, OSError) as error:
            messagebox.showerror("Cannot start simulation", str(error))
            return
        session[0] = current
        completed[0] = False
        start_button.configure(state="disabled")
        for name in NAMES:
            card = cards[name]
            card.update(follow=True, index=0, shown=None)
            card["updating"] = True
            card["seekbar"].configure(to=1)
            card["seekbar"].set(0)
            card["updating"] = False
            draw_room(card["canvas"], None, current.settings, COLORS[name])
            card["label"].configure(text="Running…")

    start_button = ttk.Button(controls, text="Run all five", command=start)
    start_button.pack(side="left", padx=8)

    def refresh():
        current = session[0]
        if current is not None:
            finished = completed[0] or current.poll()
            for name, run in current.runs.items():
                card = cards[name]
                if run.history:
                    if card["follow"]:
                        card["index"] = len(run.history) - 1
                    index = card["index"]
                    frame = run.history[index]
                    if card["shown"] != index:
                        draw_room(card["canvas"], frame, current.settings, COLORS[name])
                        card["shown"] = index
                    card["updating"] = True
                    card["seekbar"].configure(to=max(1, len(run.history) - 1))
                    card["seekbar"].set(index)
                    card["updating"] = False
                    step, simulated_time, _, active = frame
                    mode = "Live" if card["follow"] else f"Reviewing frame {index + 1}/{len(run.history)}"
                    detail = (f"{mode} · step {step}/{current.settings['steps']} · "
                              f"model t={simulated_time:.1f}s · "
                              f"{active} active / {current.pedestrians-active} exited")
                else:
                    detail = "Initializing"
                if run.ended is None:
                    card["label"].configure(text=f"{detail}\nRunning {run.wall_seconds:.2f}s wall time")
                elif run.exit_code == 0:
                    final_active = run.latest[3] if run.latest else current.pedestrians
                    outcome = ("Evacuated" if final_active == 0 else
                               f"Maximum duration reached; {final_active} remain")
                    card["label"].configure(text=f"{detail}\n{outcome} · {run.wall_seconds:.3f}s wall time · "
                                            f"backend {run.total_ms:.2f}ms · metrics {run.metrics_ms:.2f}ms")
                else:
                    card["label"].configure(text=f"{detail}\nFailed: {run.message[:200]}")
            if finished and not completed[0]:
                completed[0] = True
                start_button.configure(state="normal")
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
