"""Export the report's vector diagrams for IEEEtran LaTeX."""
import csv
import sys
from pathlib import Path
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "report"))
from build_report import ArchitectureDiagram, RuntimeChart  # noqa: E402

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)
with (ROOT / "results/benchmarks/all_backends/summary.csv").open(newline="") as f:
    rows = list(csv.DictReader(f))
runtime = {(int(r["pedestrians"]), r["backend"]): float(r["total_median_ms"])
           for r in rows if r["study"] == "crowd"}
for name, figure in (("architecture", ArchitectureDiagram()),
                     ("runtime", RuntimeChart(runtime))):
    path = OUT / f"{name}.pdf"
    pdf = canvas.Canvas(str(path), pagesize=(figure.width, figure.height))
    figure.drawOn(pdf, 0, 0)
    pdf.showPage()
    pdf.save()
    print(path)
