"""Dependency-free PCAP animation and SVG charts from simulator CSV output."""

import argparse
import csv
import html
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


INK = "#18324b"
BLUE = "#147d9d"
ORANGE = "#ed8b36"
PALE = "#edf5f8"


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def config(path):
    values = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            key, value = line.split("=", 1)
            values[key.strip()] = float(value.strip())
    return values


def snapshots(path):
    frames = defaultdict(list)
    for row in read_rows(path):
        frames[int(row["step"])].append({key: float(row[key]) for key in
                                         ("time", "x", "y", "vx", "vy", "radius", "active")})
    return dict(sorted(frames.items()))


def svg(path, width, height, body):
    Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img"><rect width="100%" height="100%" fill="white"/>'
        f'<g font-family="Arial,sans-serif" fill="{INK}">{body}</g></svg>',
        encoding="utf-8")


def text(x, y, label, size=14, anchor="start", color=INK, weight="normal"):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(label))}</text>')


def chart(path, title, x_label, y_label, series, x_domain=None, y_domain=None):
    width, height = 900, 550
    left, right, top, bottom = 90, 35, 70, 80
    xs = [x for _, points, _ in series for x, _ in points]
    ys = [y for _, points, _ in series for _, y in points]
    if not xs or not ys:
        raise ValueError("chart has no data")
    xmin, xmax = x_domain or (min(xs), max(xs))
    ymin, ymax = y_domain or (0, max(ys) * 1.1 if max(ys) > 0 else 1)
    if xmax <= xmin:
        xmax = xmin + 1
    if ymax <= ymin:
        ymax = ymin + 1
    px = lambda x: left + (x - xmin) / (xmax - xmin) * (width - left - right)
    py = lambda y: height - bottom - (y - ymin) / (ymax - ymin) * (height - top - bottom)
    parts = [text(left, 37, title, 24, weight="bold")]
    for tick in range(6):
        value = ymin + (ymax - ymin) * tick / 5
        yy = py(value)
        parts.append(f'<line x1="{left}" y1="{yy}" x2="{width-right}" y2="{yy}" stroke="{PALE}"/>')
        parts.append(text(left - 10, yy + 5, f"{value:.2g}", 12, "end"))
        xv = xmin + (xmax - xmin) * tick / 5
        parts.append(text(px(xv), height - bottom + 23, f"{xv:.2g}", 12, "middle"))
    parts.append(f'<path d="M{left},{top}V{height-bottom}H{width-right}" fill="none" stroke="{INK}"/>')
    parts.append(text(width / 2, height - 24, x_label, 15, "middle"))
    parts.append(f'<text x="22" y="{height/2}" transform="rotate(-90 22 {height/2})" '
                 f'font-size="15" text-anchor="middle">{html.escape(y_label)}</text>')
    for index, (name, points, color) in enumerate(series):
        points = sorted(points)
        polyline = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in points)
        parts.append(f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y in points:
            parts.append(f'<circle cx="{px(x):.2f}" cy="{py(y):.2f}" r="3" fill="{color}"/>')
        parts.append(f'<line x1="{width-190}" y1="{top+index*24}" x2="{width-164}" '
                     f'y2="{top+index*24}" stroke="{color}" stroke-width="3"/>')
        parts.append(text(width - 154, top + index * 24 + 5, name, 13))
    svg(path, width, height, "".join(parts))


def cell_densities(frame, cfg, cell):
    nx = math.ceil(cfg.get("room_width", 20) / cell)
    ny = math.ceil(cfg.get("room_height", 12) / cell)
    counts = [[0 for _ in range(nx)] for _ in range(ny)]
    for person in frame:
        if not person["active"]:
            continue
        ix = min(nx - 1, max(0, int(person["x"] / cell)))
        iy = min(ny - 1, max(0, int(person["y"] / cell)))
        counts[iy][ix] += 1
    densities = []
    for iy, row in enumerate(counts):
        values = []
        for ix, count in enumerate(row):
            area = (min(cell, cfg["room_width"] - ix * cell) *
                    min(cell, cfg["room_height"] - iy * cell))
            values.append(count / area)
        densities.append(values)
    return densities


def heatmap(args):
    cfg = config(args.config)
    frames = snapshots(args.snapshots)
    step = args.step if args.step is not None else max(frames)
    if step not in frames:
        raise ValueError(f"step {step} is absent; available: {list(frames)}")
    grid = cell_densities(frames[step], cfg, args.cell)
    peak = max((value for row in grid for value in row), default=0)
    width, height = 930, 650
    left, top, plot_w, plot_h = 82, 75, 760, 490
    cw, ch = plot_w / len(grid[0]), plot_h / len(grid)
    parts = [text(left, 37, f"Pedestrian density at t={frames[step][0]['time']:.2f} s", 24, weight="bold")]
    for iy, row in enumerate(grid):
        for ix, value in enumerate(row):
            mix = 0 if peak == 0 else value / peak
            red = round(237 + (212 - 237) * mix)
            green = round(245 + (75 - 245) * mix)
            blue = round(248 + (51 - 248) * mix)
            parts.append(f'<rect x="{left+ix*cw:.2f}" y="{top+(len(grid)-iy-1)*ch:.2f}" '
                         f'width="{cw:.2f}" height="{ch:.2f}" fill="rgb({red},{green},{blue})" '
                         f'stroke="white" stroke-width="0.5"/>')
    parts.append(f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" '
                 f'fill="none" stroke="{INK}"/>')
    parts.append(text(left + plot_w / 2, 604, "Room x (metres)", 15, "middle"))
    parts.append(text(left, 590, "0", 12))
    parts.append(text(left + plot_w, 590, f"{cfg['room_width']:g}", 12, "end"))
    parts.append(text(20, top + plot_h / 2, "Room y (metres)", 15))
    parts.append(text(left + plot_w + 12, top + 18, f"Peak {peak:.2f} people/m²", 13))
    parts.append(text(left + plot_w + 12, top + 39, f"Cell {args.cell:g} m", 13))
    svg(args.output, width, height, "".join(parts))


def timeseries(args):
    cfg = config(args.config)
    frames = snapshots(args.snapshots)
    summary = {int(row["step"]): row for row in read_rows(args.summary)}
    density, flow = [], []
    previous = None
    for step, frame in frames.items():
        time = frame[0]["time"] if frame else step * cfg.get("dt", 0.02)
        peak = max((v for row in cell_densities(frame, cfg, args.cell) for v in row), default=0)
        density.append((time, peak))
        exited = int(summary[step]["exited"])
        if previous is not None:
            old_t, old_e = previous
            flow.append((time, (exited - old_e) / (time - old_t)))
        previous = time, exited
    chart(args.output_prefix + "_density.svg", "Peak cell density over time", "Time (s)",
          "People / m²", [("Peak density", density, BLUE)])
    if flow:
        chart(args.output_prefix + "_flow.svg", "Exit flow over each snapshot interval", "Time (s)",
              "People / s", [("Exit flow", flow, ORANGE)])


def performance(args):
    groups = defaultdict(lambda: defaultdict(list))
    scenario = None
    for path in args.runs:
        for row in read_rows(path):
            identity = tuple((key, value) for key, value in row.items()
                             if key not in ("backend", "pedestrians", "hardware_threads", "device_name",
                                            "total_ms", "kernel_ms", "transfer_ms",
                                            "worker_threads", "metrics_ms"))
            if scenario is None:
                scenario = identity
            elif scenario != identity:
                raise ValueError("performance inputs differ in scenario/model settings")
            groups[row["backend"]][int(row["pedestrians"])].append(float(row["total_ms"]))
    colors = [BLUE, ORANGE, "#7d5ba6", "#3a916a", "#c74c65"]
    series = [(name, [(n, statistics.median(times)) for n, times in sorted(counts.items())],
               colors[i % len(colors)])
              for i, (name, counts) in enumerate(sorted(groups.items()))]
    chart(args.output_prefix + "_runtime.svg", "Runtime versus crowd size", "Pedestrians",
          "Simulation time (ms)", series)
    baseline = {n: statistics.median(times) for n, times in groups.get("sequential", {}).items()}
    speedups = [(name, [(n, baseline[n] / time) for n, time in points if n in baseline and time > 0], color)
                for name, points, color in series if name != "sequential"]
    speedups = [series for series in speedups if series[1]]
    if speedups:
        chart(args.output_prefix + "_speedup.svg", "Speedup against sequential", "Pedestrians",
              "Speedup (×)", speedups)


def animate(args):
    cfg = config(args.config)
    frames = snapshots(args.snapshots)
    compact = [{"step": step, "time": frame[0]["time"] if frame else step * cfg.get("dt", 0.02),
                "people": [[round(p["x"], 4), round(p["y"], 4), int(p["active"])] for p in frame]}
               for step, frame in frames.items()]
    data = json.dumps({"config": cfg, "frames": compact}, separators=(",", ":"))
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PCAP crowd simulation</title><style>body{margin:0;background:#eef5f8;color:#18324b;font:16px Arial,sans-serif}
main{max-width:1050px;margin:28px auto;padding:20px;background:white;border-radius:14px;box-shadow:0 8px 30px #16324b20}
h1{margin:0 0 8px}p{margin:0 0 18px;color:#486276}canvas{width:100%;border:1px solid #b6cdd9;border-radius:8px}
.controls{display:flex;gap:14px;align-items:center;margin:15px 0}.controls input{flex:1}button{background:#147d9d;color:white;border:0;border-radius:6px;padding:9px 18px;cursor:pointer}</style>
<main><h1>Crowd movement</h1><p>Fixed-seed simulation · active pedestrians in blue · exited pedestrians are omitted</p>
<canvas id="scene" width="1000" height="620"></canvas><div class="controls"><button id="play">Pause</button>
<input id="frame" type="range" min="0" value="0"><span id="status"></span></div></main>
<script>const data=__DATA__;const c=document.getElementById('scene'),ctx=c.getContext('2d'),slider=document.getElementById('frame');
slider.max=data.frames.length-1;let index=0,playing=true;const cfg=data.config,W=cfg.room_width,H=cfg.room_height;
const sx=x=>50+x/W*880,sy=y=>570-y/H*520;
function draw(){const f=data.frames[index];ctx.clearRect(0,0,1000,620);ctx.fillStyle='#edf5f8';ctx.fillRect(sx(0),sy(H),880,520);
ctx.strokeStyle='#18324b';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(sx(0),sy(0));ctx.lineTo(sx(0),sy(H));ctx.lineTo(sx(W),sy(H));
const lo=cfg.exit_center_y-cfg.exit_width/2,hi=cfg.exit_center_y+cfg.exit_width/2;
ctx.moveTo(sx(W),sy(H));ctx.lineTo(sx(W),sy(hi));ctx.moveTo(sx(W),sy(lo));ctx.lineTo(sx(W),sy(0));ctx.lineTo(sx(0),sy(0));ctx.stroke();
ctx.strokeStyle='#ed8b36';ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(sx(W),sy(hi));ctx.lineTo(sx(W),sy(lo));ctx.stroke();
if(cfg.obstacle_radius>0){ctx.fillStyle='#667c8e';ctx.beginPath();ctx.arc(sx(cfg.obstacle_x),sy(cfg.obstacle_y),cfg.obstacle_radius/W*880,0,2*Math.PI);ctx.fill()}
ctx.fillStyle='#147d9d';for(const p of f.people){if(!p[2])continue;ctx.beginPath();ctx.arc(sx(p[0]),sy(p[1]),Math.max(3,cfg.radius/W*880),0,2*Math.PI);ctx.fill()}
document.getElementById('status').textContent=`t=${f.time.toFixed(2)} s · ${f.people.filter(p=>p[2]).length} active · ${f.people.filter(p=>!p[2]).length} exited`;
slider.value=index}
slider.addEventListener('input',()=>{index=Number(slider.value);draw()});document.getElementById('play').onclick=()=>{playing=!playing;document.getElementById('play').textContent=playing?'Pause':'Play'};
setInterval(()=>{if(playing){index=(index+1)%data.frames.length;draw()}},90);draw();</script></html>"""
    Path(args.output).write_text(page.replace("__DATA__", data), encoding="utf-8")


def compare(args):
    cfg = config(args.config)
    paths = (
        ("Sequential", args.sequential), ("OpenMP", args.openmp),
        ("MPI", args.mpi), ("CUDA", args.cuda), ("Hybrid", args.hybrid))
    runs = [(name, snapshots(path)) for name, path in paths]
    steps = list(runs[0][1])
    if not steps:
        raise ValueError("snapshot files contain no frames")
    for name, frames in runs[1:]:
        if list(frames) != steps:
            raise ValueError(f"{name} snapshot steps do not match the sequential run")
    timings = []
    for name, path in paths:
        if not path.endswith("_snapshots.csv"):
            raise ValueError(f"{name} input must end in _snapshots.csv")
        prefix = path[:-len("_snapshots.csv")]
        summary = {int(row["step"]): row for row in read_rows(prefix + "_summary.csv")}
        run_rows = read_rows(prefix + "_run.csv")
        if len(run_rows) != 1 or run_rows[0]["backend"] != name.lower():
            raise ValueError(f"{name} run CSV does not match its snapshot input")
        elapsed = [float(summary[step]["simulation_ms"]) for step in steps]
        if (not all(math.isfinite(value) and value >= 0 for value in elapsed)
                or any(b < a for a, b in zip(elapsed, elapsed[1:]))
                or elapsed[-1] <= 0):
            raise ValueError(f"{name} cumulative simulation times are invalid")
        run = run_rows[0]
        total_ms = float(run["total_ms"])
        metrics_ms = float(run["metrics_ms"])
        if not all(math.isfinite(value) and value >= 0 for value in (total_ms, metrics_ms)):
            raise ValueError(f"{name} run timings are invalid")
        timings.append({"elapsed": elapsed, "movement_ms": elapsed[-1],
                        "total_ms": total_ms, "metrics_ms": metrics_ms})
    compact = []
    for step in steps:
        time = runs[0][1][step][0]["time"]
        panels = []
        for name, frames in runs:
            frame = frames[step]
            if not frame or abs(frame[0]["time"] - time) > 1e-6:
                raise ValueError(f"{name} snapshot time differs at step {step}")
            panels.append([[round(p["x"], 4), round(p["y"], 4), int(p["active"])]
                           for p in frame])
        compact.append({"step": step, "time": time, "panels": panels})
    data = json.dumps({"config": cfg, "names": [name for name, _ in runs],
                       "frames": compact, "timings": timings}, separators=(",", ":"))
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PCAP five-backend comparison</title><style>
body{margin:0;background:#eef5f8;color:#18324b;font:16px Arial,sans-serif}
main{max-width:1450px;margin:22px auto;padding:20px}h1{margin:0 0 6px}
p{margin:0 0 18px;color:#486276}.controls{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:18px}
.controls input{flex:1;min-width:180px}button{background:#147d9d;color:white;border:0;border-radius:6px;padding:9px 18px;cursor:pointer}
select{padding:7px;border:1px solid #b6cdd9;border-radius:6px;background:white;color:#18324b}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
.card{background:white;padding:12px;border-radius:10px;box-shadow:0 5px 18px #16324b20}
.card h2{font-size:18px;margin:0 0 8px}.card canvas{display:block;width:100%;height:auto}
.count,.metric{color:#486276;font-size:14px;margin-top:7px}.track{height:7px;background:#edf5f8;border-radius:5px;margin-top:9px}
.fill{height:100%;background:#147d9d;border-radius:5px;width:0}</style>
<main><h1>Five-backend crowd comparison</h1>
<p>Model time compares positions at the same simulation step. Compute time advances each panel using its recorded cumulative simulation time, stretched for viewing. Timing boundaries differ by backend; these single-run numbers are indicative. Both modes replay completed runs.</p>
<div class="controls"><label>View <select id="mode"><option value="model">Model time</option><option value="compute">Compute time</option></select></label>
<label>Replay duration <select id="duration"><option value="10000">10 s</option><option value="20000" selected>20 s</option><option value="40000">40 s</option></select></label>
<button id="play">Play</button><input id="frame" type="range" min="0" max="1000" value="0" aria-label="Playback progress"><span id="status"></span></div>
<div id="grid" class="grid"></div></main>
<script>const data=__DATA__,cfg=data.config,frames=data.frames,grid=document.getElementById('grid'),
slider=document.getElementById('frame'),status=document.getElementById('status'),button=document.getElementById('play'),
mode=document.getElementById('mode'),duration=document.getElementById('duration');
const maxMs=Math.max(...data.timings.map(t=>t.movement_ms)),baseline=data.timings[0].total_ms;
let position=0,playing=false,lastTick=null;
const cards=data.names.map((name,i)=>{const card=document.createElement('section');card.className='card';
const heading=document.createElement('h2');heading.textContent=name;const canvas=document.createElement('canvas');
canvas.width=500;canvas.height=320;const count=document.createElement('div');count.className='count';
const metric=document.createElement('div');metric.className='metric';const timing=data.timings[i];
metric.textContent=`Recorded simulation ${timing.movement_ms.toFixed(2)} ms · reported total ${timing.total_ms.toFixed(2)} ms · ${(baseline/timing.total_ms).toFixed(2)}× sequential · metrics ${timing.metrics_ms.toFixed(2)} ms`;
const track=document.createElement('div');track.className='track';const fill=document.createElement('div');fill.className='fill';track.append(fill);
card.append(heading,canvas,count,metric,track);grid.append(card);return {ctx:canvas.getContext('2d'),count,fill}});
const W=cfg.room_width,H=cfg.room_height,sx=x=>30+x/W*440,sy=y=>285-y/H*255;
function scene(ctx,people){ctx.clearRect(0,0,500,320);ctx.fillStyle='#edf5f8';ctx.fillRect(sx(0),sy(H),440,255);
ctx.strokeStyle='#18324b';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(sx(0),sy(0));ctx.lineTo(sx(0),sy(H));ctx.lineTo(sx(W),sy(H));
const lo=cfg.exit_center_y-cfg.exit_width/2,hi=cfg.exit_center_y+cfg.exit_width/2;
ctx.moveTo(sx(W),sy(H));ctx.lineTo(sx(W),sy(hi));ctx.moveTo(sx(W),sy(lo));ctx.lineTo(sx(W),sy(0));ctx.lineTo(sx(0),sy(0));ctx.stroke();
ctx.strokeStyle='#ed8b36';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(sx(W),sy(hi));ctx.lineTo(sx(W),sy(lo));ctx.stroke();
if(cfg.obstacle_radius>0){ctx.fillStyle='#667c8e';ctx.beginPath();ctx.arc(sx(cfg.obstacle_x),sy(cfg.obstacle_y),cfg.obstacle_radius/W*440,0,2*Math.PI);ctx.fill()}
ctx.fillStyle='#147d9d';let active=0;for(const p of people){if(!p[2])continue;active++;ctx.beginPath();ctx.arc(sx(p[0]),sy(p[1]),Math.max(2,cfg.radius/W*440),0,2*Math.PI);ctx.fill()}
return active}
function frameAtElapsed(times,elapsed){let lo=0,hi=times.length-1;while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(times[mid]<=elapsed)lo=mid;else hi=mid-1}return lo}
function draw(){const modelIndex=Math.round(position*(frames.length-1)),elapsed=position*maxMs;
cards.forEach((card,i)=>{const timing=data.timings[i],index=mode.value==='model'?modelIndex:frameAtElapsed(timing.elapsed,elapsed),f=frames[index];
const active=scene(card.ctx,f.panels[i]);card.count.textContent=`step ${f.step} · t=${f.time.toFixed(2)} s · ${active} active · ${f.panels[i].length-active} exited`;
card.fill.style.width=`${100*index/(frames.length-1)}%`});
status.textContent=mode.value==='model'?`step ${frames[modelIndex].step} · t=${frames[modelIndex].time.toFixed(2)} s`:
`compute clock ${elapsed.toFixed(1)} / ${maxMs.toFixed(1)} ms`;slider.value=Math.round(position*1000)}
function reset(){position=0;playing=false;lastTick=null;button.textContent='Play';draw()}
slider.addEventListener('input',()=>{position=Number(slider.value)/1000;draw()});mode.addEventListener('change',reset);
button.onclick=()=>{if(position>=1)position=0;playing=!playing;lastTick=null;button.textContent=playing?'Pause':'Play';draw()};
function tick(now){if(playing){if(lastTick!==null){position=Math.min(1,position+(now-lastTick)/Number(duration.value));
if(position===1){playing=false;button.textContent='Play'}draw()}lastTick=now}requestAnimationFrame(tick)}
requestAnimationFrame(tick);draw();</script></html>"""
    Path(args.output).write_text(page.replace("__DATA__", data), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    animation = sub.add_parser("animate")
    animation.add_argument("config"); animation.add_argument("snapshots"); animation.add_argument("output")
    animation.set_defaults(func=animate)
    comparison = sub.add_parser("compare", help="synchronized replay of all five backends")
    comparison.add_argument("config")
    for name in ("sequential", "openmp", "mpi", "cuda", "hybrid", "output"):
        comparison.add_argument(name)
    comparison.set_defaults(func=compare)
    heat = sub.add_parser("heatmap")
    heat.add_argument("config"); heat.add_argument("snapshots"); heat.add_argument("output")
    heat.add_argument("--step", type=int); heat.add_argument("--cell", type=float, default=1.0)
    heat.set_defaults(func=heatmap)
    series = sub.add_parser("timeseries")
    series.add_argument("config"); series.add_argument("snapshots"); series.add_argument("summary")
    series.add_argument("output_prefix"); series.add_argument("--cell", type=float, default=1.0)
    series.set_defaults(func=timeseries)
    perf = sub.add_parser("performance")
    perf.add_argument("output_prefix"); perf.add_argument("runs", nargs="+")
    perf.set_defaults(func=performance)
    args = parser.parse_args()
    if hasattr(args, "cell") and args.cell <= 0:
        parser.error("--cell must be positive")
    args.func(args)


if __name__ == "__main__":
    main()
