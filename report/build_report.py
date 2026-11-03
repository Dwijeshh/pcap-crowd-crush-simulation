"""Build the evidence-based two-column IEEE conference report PDF.

Run from the repository root with the bundled or any Python containing
reportlab: python report/build_report.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Flowable, Frame, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "report" / "PCAP_IEEE_Final_Report.pdf"
PAGE_W, PAGE_H = 612, 792
MARGIN = 45
GUTTER = 18
COL_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2

body = ParagraphStyle("Body", fontName="Times-Roman", fontSize=9.1,
    leading=10.8, alignment=TA_JUSTIFY, spaceAfter=4)
head = ParagraphStyle("Head", fontName="Times-Bold", fontSize=10,
    leading=11.5, spaceBefore=8, spaceAfter=4, keepWithNext=True)
subhead = ParagraphStyle("Subhead", parent=head, fontSize=9.1,
    spaceBefore=5, spaceAfter=2)
small = ParagraphStyle("Small", parent=body, fontSize=8, leading=9.3,
    spaceAfter=3)
caption = ParagraphStyle("Caption", parent=small, alignment=TA_CENTER,
    spaceBefore=2, spaceAfter=7)
refstyle = ParagraphStyle("Ref", parent=small, leftIndent=15, firstLineIndent=-15,
    spaceAfter=2)


def P(s: str, style=body):
    return Paragraph(s, style)


def H(n: str, title: str):
    return P(f"{n}. {title}" if n else title, head)


def SH(title: str):
    return P(title, subhead)


def make_table(headers: list[str], rows: list[list[str]], widths=None):
    cell = ParagraphStyle("Cell", parent=small, fontSize=7.1, leading=8,
        alignment=TA_CENTER, spaceAfter=0)
    data = [[P(x, cell) for x in headers]] + [[P(str(x), cell) for x in row] for row in rows]
    t = Table(data, colWidths=widths, hAlign="CENTER", repeatRows=1)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.7, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


class RuntimeChart(Flowable):
    def __init__(self, rows):
        super().__init__()
        self.width, self.height = COL_W, 156
        self.rows = rows

    def draw(self):
        c = self.canv
        left, bottom, right, top = 34, 28, self.width - 7, self.height - 22
        palette = {"sequential": colors.HexColor("#222222"),
            "openmp": colors.HexColor("#1f77b4"), "mpi": colors.HexColor("#9467bd"),
            "cuda": colors.HexColor("#2ca02c"), "hybrid": colors.HexColor("#d95f02")}
        c.setFont("Times-Roman", 7)
        import math
        for yval in (10, 100, 1000):
            y = bottom + (math.log10(yval) - 1) / 3.5 * (top - bottom)
            c.setStrokeColor(colors.HexColor("#dddddd"))
            c.line(left, y, right, y)
            c.setFillColor(colors.black)
            c.drawRightString(left - 4, y - 2, str(yval))
        c.setStrokeColor(colors.black)
        c.line(left, bottom, right, bottom)
        c.line(left, bottom, left, top)
        xs = [500, 1000, 2000, 5000]
        def xpos(n): return left + (xs.index(n) / 3) * (right - left)
        def ypos(ms): return bottom + ((math.log10(ms) - 1) / 3.5) * (top - bottom)
        for n in xs:
            c.drawCentredString(xpos(n), bottom - 11, str(n))
        for backend, color in palette.items():
            pts = [(xpos(n), ypos(self.rows[(n, backend)])) for n in xs]
            c.setStrokeColor(color)
            c.setFillColor(color)
            c.setLineWidth(1.4)
            path = c.beginPath()
            path.moveTo(*pts[0])
            for pt in pts[1:]: path.lineTo(*pt)
            c.drawPath(path)
            for x, y in pts: c.circle(x, y, 2.2, stroke=0, fill=1)
        legend_y = self.height - 8
        c.setFont("Times-Roman", 7)
        x = 3
        for backend, color in palette.items():
            c.setStrokeColor(color); c.setLineWidth(2); c.line(x, legend_y, x + 10, legend_y)
            c.setFillColor(colors.black); c.drawString(x + 13, legend_y - 2, backend)
            x += 50 if backend != "sequential" else 62
        c.setFont("Times-Roman", 7)
        c.drawCentredString((left + right)/2, 2, "Pedestrians (100 steps)")


class ArchitectureDiagram(Flowable):
    """Vector component and data-flow diagram for the implemented system."""
    def __init__(self):
        super().__init__()
        self.width, self.height = COL_W, 155

    def draw(self):
        c = self.canv
        c.setFont("Helvetica", 7)
        blue = colors.HexColor("#dcecf5")
        line = colors.HexColor("#24506e")
        def box(x, y, w, h, label, fill=blue):
            c.setFillColor(fill); c.setStrokeColor(line)
            c.roundRect(x, y, w, h, 3, stroke=1, fill=1)
            c.setFillColor(colors.black)
            c.drawCentredString(x+w/2, y+h/2-2.5, label)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(line); c.setLineWidth(0.8)
            c.line(x1,y1,x2,y2)
            import math
            a=math.atan2(y2-y1,x2-x1)
            for offset in (-0.55,0.55):
                c.line(x2,y2,x2-4*math.cos(a+offset),y2-4*math.sin(a+offset))
        box(70,130,114,19,"Config + seed")
        box(70,102,114,19,"Shared initial state")
        arrow(127,130,127,121)
        labels=["Sequential","OpenMP","MPI","CUDA","Hybrid"]
        w=43; gap=6; x0=2
        for i,label in enumerate(labels):
            box(x0+i*(w+gap),65,w,23,label,colors.HexColor("#e6f2e6"))
            arrow(127,102,x0+i*(w+gap)+w/2,88)
            arrow(x0+i*(w+gap)+w/2,65,127,52)
        box(70,33,114,19,"Metrics + CSV outputs")
        box(70,5,114,19,"Live comparison UI")
        arrow(127,33,127,24)


def page(canvas, doc):
    canvas.saveState()
    if doc.page == 1:
        canvas.setFont("Times-Bold", 17)
        canvas.drawCentredString(PAGE_W / 2, 751, "Parallel Crowd-Crush Risk Simulation")
        canvas.drawCentredString(PAGE_W / 2, 731, "Using MPI, OpenMP, and CUDA")
        canvas.setFont("Times-Roman", 10)
        canvas.drawCentredString(PAGE_W / 2, 705, "Dwijesh P, Ayush KL, Sammit Menon")
        canvas.setFont("Times-Italic", 9)
        canvas.drawCentredString(PAGE_W / 2, 689,
            "Manipal Institute of Technology, Manipal Academy of Higher Education")
    canvas.setFont("Times-Roman", 8)
    canvas.drawCentredString(PAGE_W / 2, 27, str(doc.page))
    canvas.restoreState()


def build():
    with (ROOT / "results/benchmarks/all_backends/summary.csv").open(newline="") as f:
        bench = list(csv.DictReader(f))
    with (ROOT / "results/benchmarks/configuration_study/summary.csv").open(newline="") as f:
        config = list(csv.DictReader(f))
    with (ROOT / "results/risk_study/summary.csv").open(newline="") as f:
        risk = list(csv.DictReader(f))
    runtime = {(int(r["pedestrians"]), r["backend"]): float(r["total_median_ms"])
        for r in bench if r["study"] == "crowd"}
    assert len(config) == 29 and len(risk) == 30
    risk_reference = sorted((r for r in risk if r["backend"] == "sequential"),
        key=lambda r: (int(r["pedestrians"]), float(r["exit_width"])))

    doc = BaseDocTemplate(str(OUT), pagesize=(PAGE_W, PAGE_H),
        leftMargin=MARGIN, rightMargin=MARGIN, topMargin=40, bottomMargin=43)
    first = [Frame(MARGIN, 43, COL_W, 631, leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0, id="first-left"),
             Frame(MARGIN + COL_W + GUTTER, 43, COL_W, 631,
                   leftPadding=0, rightPadding=0, topPadding=0,
                   bottomPadding=0, id="first-right")]
    later = [Frame(MARGIN, 43, COL_W, 704, leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0, id="left"),
             Frame(MARGIN + COL_W + GUTTER, 43, COL_W, 704,
                   leftPadding=0, rightPadding=0, topPadding=0,
                   bottomPadding=0, id="right")]
    doc.addPageTemplates([PageTemplate(id="First", frames=first, onPage=page,
                                       autoNextPageTemplate="Later"),
                          PageTemplate(id="Later", frames=later, onPage=page)])

    story = []
    def add(*items): story.extend(items)
    add(P("<b>Abstract—</b>We implement one deterministic, social-force-inspired "
          "pedestrian model in five execution backends: sequential CPU, OpenMP, "
          "MPI, CUDA, and MPI+OpenMP+CUDA hybrid. We compare numerical agreement, "
          "runtime scaling, parallel configuration, and simulated bottleneck "
          "indicators on a single laptop with one GPU. In a 5,000-pedestrian, "
          "100-step case, reported median movement times were 2,841.54 ms "
          "(sequential), 938.40 ms (OpenMP), 1,436.00 ms (MPI), 138.34 ms "
          "(CUDA), and 284.19 ms (hybrid). On a separate 2,000-pedestrian "
          "configuration sweep, four OpenMP threads achieved 3.77× CPU update "
          "speedup and 0.94 parallel efficiency. In 12 s exit experiments, "
          "wider openings increased exits and reduced recorded peak density. "
          "The density and congestion labels are simulation proxies, not "
          "validated estimates of injury or real-world crowd danger."),
        P("<b>Index Terms—</b>pedestrian simulation, parallel computing, OpenMP, "
          "MPI, CUDA, congestion."),
        H("I", "INTRODUCTION"),
        P("Crowd movement near an exit combines local interactions with a "
          "global bottleneck. Social-force models represent desired motion and "
          "repulsion through continuous dynamics [1], [2]. This project asks "
          "how one shared movement rule behaves across CPU, process, GPU, and "
          "hybrid implementations, and whether its descriptive congestion "
          "measures remain consistent. The contribution is a reproducible "
          "five-backend implementation with numerical checks and local "
          "performance and exit-width studies. It is not an empirically "
          "calibrated safety predictor."),
        SH("A. Problem, beneficiaries, and prior work"),
        P("A single-backend simulator makes it difficult to separate model "
          "behavior from execution effects when varying crowd size or exit "
          "geometry. The practical problem is to obtain reproducible "
          "bottleneck traces while understanding the cost of several "
          "parallel execution choices. Students and researchers benefit "
          "from a shared reference implementation and comparable outputs; "
          "event planners may use the visualizations for exploratory "
          "questions only, after domain validation."),
        P("Helbing and Molnár introduced the social-force framework [1]; "
          "Helbing et al. examined escape dynamics [2]. Later empirical "
          "work showed that extreme crowd behavior challenges simple "
          "models [3]. Grandison et al. studied domain decomposition "
          "for large evacuation simulation [7]. Recent systems instead "
          "emphasize interactive density visualization [8] or calibrating "
          "agent parameters against observations [9]. Those studies "
          "motivate this work but use different models, hardware, and "
          "evaluation targets, so their runtimes cannot be compared "
          "numerically with ours. Table I summarizes the scope differences."),
        make_table(["Work", "Main focus", "Relation to this work"], [
            ["Grandison et al. [7]", "Domain decomposition", "Our MPI splits IDs"],
            ["Choi et al. [8]", "Unity density display", "Our emphasis is backend agreement"],
            ["Shigenaka et al. [9]", "Parameter calibration", "Our model is uncalibrated"],
            ["This work", "Five backend comparison", "One model and common outputs"],
        ], [72,81,100]),
        P("TABLE I. Scope comparison with published systems; no cross-study "
          "performance ranking is implied.", caption),
        P("The local contribution is a common state update and output "
          "contract across five backends, explicit CPU/GPU numerical "
          "tolerances, and a combined performance and congestion study "
          "on one machine. The novelty is engineering integration and "
          "controlled comparison, not a new physical crowd theory."),
        H("II", "MODEL AND INDICATORS"),
        SH("A. Movement and exit rule"),
        P("Each pedestrian has position <i>p</i>, velocity <i>v</i>, radius, "
          "preferred speed, and active status. At each step, its acceleration "
          "is (<i>v</i><sub>desired</sub> − <i>v</i>)/τ plus the sum of "
          "pedestrian, wall, and optional circular-obstacle forces divided "
          "by mass. Pair repulsion combines an exponential term in surface "
          "clearance with a linear overlap term. The direction points toward "
          "the right-wall exit. Semi-implicit Euler integration updates "
          "velocity before position, with Δ<i>t</i> = 0.02 s and a speed cap. "
          "An agent exits only when its center crosses the opening with "
          "positive horizontal velocity and adequate radius clearance. "
          "The updater reads an immutable current state and writes a separate "
          "next state, preventing update-order dependence."),
        SH("B. Congestion and risk proxy"),
        P("A 1 m grid records active center count divided by each cell's "
          "actual area. A nonempty cell is congested when density is at least "
          "2 people/m² and mean speed at most 0.5 m/s. Consecutive duration "
          "resets when that condition ends; cumulative duration sums all "
          "congested steps. The category is low with no congested cell, "
          "medium with any congested cell, and high when a currently "
          "congested cell has persisted for at least 2 s. Bottleneck "
          "occupancy and interval exit flow are also recorded. These "
          "configurable rules do not measure pressure or injury [3]."),
        H("III", "PARALLEL IMPLEMENTATIONS"),
        P("The sequential implementation is the reference. OpenMP divides "
          "pedestrian updates over threads. MPI assigns contiguous pedestrian "
          "ID ranges to ranks; each rank holds the full current state and "
          "Allgatherv assembles the next state every step. This is ID "
          "partitioning, not spatial decomposition. CUDA launches a "
          "pedestrian-parallel kernel with configurable block size. The "
          "hybrid assigns ID ranges to MPI ranks, runs the CUDA updater "
          "for each range, and uses OpenMP plus MPI reduction for metrics. "
          "All ranks share one physical GPU, so the hybrid is a single-GPU "
          "experiment. These programming mechanisms follow [4]–[6]."),
        P("Fig. 1 shows the data flow. A seeded state and the same "
          "configuration feed each backend. Each writes snapshots and "
          "summary metrics that the live interface can compare. The "
          "project writes CSV files and uses no relational database; an "
          "entity–relationship diagram would misrepresent its storage."),
        CondPageBreak(210),
        ArchitectureDiagram(),
        P("Fig. 1. Implemented component and output workflow; arrows show "
          "state or result flow. The live UI reads produced output.", caption),
        H("IV", "EXPERIMENTAL METHOD"),
        P("Measurements used a Windows 11 laptop with Intel Core i7-12650H "
          "(10 physical cores, 16 logical processors), approximately 16 GiB "
          "RAM, one GeForce RTX 3050 Laptop GPU (4 GiB), CUDA Toolkit 13.1, "
          "Microsoft MPI, and MSVC. Seed 42 initialized all cases. The "
          "crowd-scaling matrix tested 500, 1,000, 2,000, and 5,000 agents "
          "for 100 steps in a 100 × 70 m room; three 100-agent, 600-step "
          "exit cases used a 20 × 12 m room and 1, 2, or 4 m openings. "
          "Each of the 35 backend/case combinations had one warmup and five "
          "measured runs (175 measured runs). OpenMP used four threads, MPI "
          "two ranks, CUDA blocks of 256, and hybrid two ranks with two "
          "OpenMP threads per rank and blocks of 256."),
        P("A second fixed 2,000-agent, 100-step sweep tested 29 configurations "
          "with one warmup and five measured runs each. Its CPU efficiency "
          "is sequential median update time divided by backend median "
          "update time and CPU worker count. CUDA and hybrid are excluded "
          "from that efficiency definition. Timed movement scopes differ: "
          "sequential includes next-buffer allocation; MPI includes "
          "communication; CUDA includes device allocation and initial "
          "upload; hybrid includes per-step transfer and communication "
          "but excludes device allocation. CSV writing and risk metric "
          "sampling are excluded from the movement benchmark. Therefore "
          "cross-backend ratios are indicative local comparisons, not "
          "equivalent end-to-end latencies."),
        P("Evaluation uses numerical agreement with the sequential state "
          "as implementation correctness, median movement time as response "
          "time, 100 steps divided by median seconds as movement-pathway "
          "throughput, and CPU update speedup/efficiency. This numerical "
          "agreement is not accuracy against observed human trajectories. "
          "Peak RAM/VRAM and user satisfaction were not instrumented, "
          "so no values are claimed for them."),
        H("V", "VALIDATION AND PERFORMANCE"),
        SH("A. Numerical agreement"),
        P("All six CTest cases passed. In the wide-exit, narrow-exit, and "
          "obstacle scenarios, parallel exit counts and active states "
          "agreed with sequential. Hybrid position and velocity values "
          "were within 0.001 absolute tolerance across 6,100 saved "
          "snapshot rows per scenario; its maximum position difference "
          "was 0.0002651 m in the narrow-exit case. Summary metric "
          "categories and counts agreed; floating values differed by "
          "at most 0.001. Near a grid boundary, small CPU/GPU rounding "
          "differences can move one pedestrian into an adjacent cell, "
          "so cell-by-cell equality is not guaranteed."),
        SH("B. Crowd scaling"),
        P("Fig. 2 and Table II show that the GPU setup cost dominates "
          "small cases while the GPU kernel pathway benefits from larger "
          "agent populations."),
        RuntimeChart(runtime),
        P("Fig. 2. Median reported movement time for the 100-step crowd "
          "scaling cases (logarithmic vertical axis); five runs per point.", caption),
        make_table(["Agents", "Seq.", "OMP", "MPI", "CUDA", "Hybrid"], [
            [str(n)] + [f"{runtime[(n,b)]:.1f}" for b in
                ("sequential", "openmp", "mpi", "cuda", "hybrid")]
            for n in (500,1000,2000,5000)], [36,43,40,40,44,50]),
        P("TABLE II. Median reported movement time (ms), five runs.", caption),
        P("At 5,000 agents, the corresponding ratios to sequential are "
          "3.03× (OpenMP), 1.98× (MPI), 20.54× (CUDA), and 10.00× "
          "(hybrid). The indicative movement throughput at that size is "
          "35.2 steps/s sequential and 722.9 steps/s CUDA. In the "
          "500-agent case, sequential is faster than "
          "both GPU pathways; fixed setup and communication costs are "
          "visible at small workloads. The 100-step scaling cases "
          "finished before any agent exited."),
        SH("C. Configuration sweep"),
        P("Table III reports CPU update speedup and efficiency relative "
          "to the sequential median; the different GPU workers do not "
          "enter this efficiency definition."),
        make_table(["CPU path", "Workers", "Update ms", "Speedup", "Eff."], [
            ["Sequential", "1", "491.04", "1.00", "1.00"],
            ["OpenMP", "2", "246.86", "1.99", "0.99"],
            ["OpenMP", "4", "130.14", "3.77", "0.94"],
            ["OpenMP", "8", "146.88", "3.34", "0.42"],
            ["MPI", "2", "247.27", "1.99", "0.99"],
            ["MPI", "4", "150.23", "3.27", "0.82"],
        ], [57,35,52,45,44]),
        P("TABLE III. Fixed 2,000-agent CPU sweep; medians of five runs.", caption),
        P("OpenMP improved through four threads, whereas eight threads "
          "increased update time to 146.88 ms. CUDA block medians at "
          "128, 256, and 512 threads were 75.10, 76.99, and 81.57 ms; "
          "their interquartile ranges overlap. For hybrid with blocks "
          "of 256 and two OpenMP threads per rank, one, two, and four "
          "ranks took 55.02, 166.84, and 342.09 ms. Sharing one GPU "
          "across ranks added transfer and communication overhead."),
        H("VI", "EXIT-WIDTH AND RISK RESULTS"),
        P("The risk study ran 100 and 200 pedestrians in the 20 × 12 m "
          "room for 600 steps (12 s), at exit widths 1, 2, and 4 m. "
          "It saved metric rows every 10 steps (0.2 s), while cell "
          "congestion duration accumulated every simulation step. "
          "All five backends agreed on recorded risk categories and "
          "integer counts in the 30 scenario/backend summaries; floating "
          "summary metrics differed from sequential by at most 0.001. "
          "Table IV presents the sequential values."),
        CondPageBreak(170),
        make_table(["People", "Exit m", "Exited", "Peak density", "Congest. s", "Risk"], [
            [r["pedestrians"], f'{float(r["exit_width"]):g}',
             r["final_exited"], f'{float(r["recorded_peak_density"]):g}',
             f'{float(r["max_cell_cumulative_congestion_seconds"]):.2f}',
             r["highest_recorded_risk"]]
            for r in risk_reference
        ], [35,35,37,55,49,42]),
        P("TABLE IV. Sequential 12 s exit results; other backends agree "
          "within the stated comparison rules. Peak density is the maximum "
          "of recorded samples (people/m²); congestion is maximum cell "
          "cumulative duration.", caption),
        P("For both crowd sizes, widening the opening increased exits and "
          "reduced recorded peak density and maximum cumulative cell "
          "congestion. At 100 agents, the 4 m case reached medium as "
          "its highest recorded category, versus high for 1 and 2 m. "
          "At 200 agents all three widths reached high under these "
          "chosen thresholds. These are observations for one seed and "
          "set of configurations, not estimates of real evacuation "
          "probability or safety."),
        H("VII", "LIMITATIONS AND SECURITY"),
        P("The force model omits contact friction, behavior changes, "
          "heterogeneous route choice, and empirical calibration. It uses "
          "soft pedestrian contact and a fixed population; no measured "
          "pressure or injury outcome validates the risk labels. "
          "The MPI decomposition is by ID rather than space, and "
          "the hybrid study has one GPU and one machine. Wider generality "
          "requires repeated seeds, independent hardware, measured "
          "trajectory data, and end-to-end timing with uniform boundaries. "
          "The current implementation has no measured memory profile or "
          "human-subject usability evaluation."),
        P("Configuration validation rejects unknown or duplicate keys and "
          "invalid geometry. Before exposing the interface beyond a "
          "trusted local machine, its server and file output paths would "
          "need access control and further input hardening. The risk "
          "label must be presented as a simulated indicator rather than "
          "an operational safety alert."),
        H("VIII", "FUTURE WORK"),
        P("Next steps are calibration and validation against measured "
          "pedestrian trajectories, repeated-seed sensitivity studies, "
          "uniform end-to-end timing, and peak CPU/GPU memory profiling. "
          "A spatial MPI partition could reduce replicated state, while "
          "multi-GPU tests would be needed before claiming distributed "
          "GPU scaling. Interface usability should be assessed with "
          "participants and a defined task before reporting satisfaction."),
        H("IX", "CONCLUSION"),
        P("Within this defined scope, the five backends reproduced the "
          "same exit outcomes and summary indicators. The local GPU "
          "path was fastest in the largest scaling case; four-thread "
          "OpenMP had the best measured CPU update time in the sweep. "
          "The exit-width study illustrates how the simulator can expose "
          "bottleneck trends while keeping its risk interpretation "
          "explicitly provisional."),
        H("", "REFERENCES"),
        P('[1] D. Helbing and P. Molnár, “Social force model for pedestrian dynamics,” <i>Phys. Rev. E</i>, vol. 51, pp. 4282–4286, 1995. doi: 10.1103/PhysRevE.51.4282.', refstyle),
        P('[2] D. Helbing, I. Farkas, and T. Vicsek, “Simulating dynamical features of escape panic,” <i>Nature</i>, vol. 407, pp. 487–490, 2000. doi: 10.1038/35035023.', refstyle),
        P('[3] D. Helbing, A. Johansson, and H. Zein Al-Abideen, “Dynamics of crowd disasters: An empirical study,” <i>Phys. Rev. E</i>, vol. 75, 046109, 2007. doi: 10.1103/PhysRevE.75.046109.', refstyle),
        P('[4] OpenMP Architecture Review Board, <i>OpenMP Application Programming Interface, Version 5.2</i>, 2021. Available: https://www.openmp.org/specifications/', refstyle),
        P('[5] MPI Forum, <i>MPI: A Message-Passing Interface Standard, Version 4.1</i>, 2023. Available: https://www.mpi-forum.org/docs/mpi-4.1/', refstyle),
        P('[6] NVIDIA, <i>CUDA Programming Guide</i>. Available: https://docs.nvidia.com/cuda/cuda-programming-guide/', refstyle),
        P('[7] A. Grandison, Y. Cavanagh, P. J. Lawrence, and E. R. Galea, “Increasing the simulation performance of large-scale evacuations using parallel computing techniques based on domain decomposition,” <i>Fire Technology</i>, vol. 53, pp. 1399–1438, 2017. doi: 10.1007/s10694-016-0645-8.', refstyle),
        P('[8] C.-H. Choi <i>et al.</i>, “Prediction and prevention of crowd-crush accidents using crowd-density simulation based on unity engine,” <i>Discover Applied Sciences</i>, vol. 7, art. 33, 2025. doi: 10.1007/s42452-024-06451-7.', refstyle),
        P('[9] S. Shigenaka, S. Takami, Y. Tanigaki, S. Watanabe, and M. Onishi, “MAS-Bench: a benchmarking for parameter calibration of multi-agent crowd simulation,” <i>Journal of Computational Social Science</i>, vol. 7, pp. 2121–2145, 2024. doi: 10.1007/s42001-024-00302-6.', refstyle),
    )
    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
