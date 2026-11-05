# IEEE conference report

`PCAP_IEEE_Final_Report.pdf` is a three-page, two-column review PDF built from
the implementation and measurements. Its editable ReportLab source is
`build_report.py`. The strict IEEE conference source is `ieee/main.tex` and
compiled successfully with the Codex desktop LaTeX editor. That editor does
not export a PDF through its compiler tool, so the checked-in PDF is the
separately rendered review copy. For formal submission, export PDF from the
IEEEtran project and inspect that export.

The author names in `ieee/main.tex` are clickable email links. Email addresses
are not displayed separately in the byline. The review PDF is generated from
the separate ReportLab source and does not include those name links.

The root MIT License covers the software and its code documentation. The
manuscript and research figures are scholarly works with separate publication
considerations; their reuse should follow the terms of any eventual journal
publication.

Build from the repository root with Python and ReportLab:

```powershell
python report/build_report.py
python report/ieee/build_figures.py
```

With a local LaTeX distribution that provides `IEEEtran.cls`, compile from
`report/ieee/` using `latexmk -pdf main.tex` or open the project in the Codex
LaTeX editor. The two vector figure PDFs in `ieee/figures/` are inputs to
`main.tex`; regenerate them if benchmark data or figure code changes.

The figure and review-PDF scripts read `results/benchmarks/all_backends/summary.csv`,
`results/benchmarks/configuration_study/summary.csv`, and
`results/risk_study/summary.csv`. Methods, timing boundaries, and validation
details are documented in `docs/model_specification.md`,
`docs/metrics_specification.md`, `docs/hybrid_validation.md`, and
`docs/report_studies.md`.

The report describes one machine with one GPU, one random seed, and an
uncalibrated congestion indicator. Numerical agreement with sequential is not
real-world trajectory accuracy; peak memory and user satisfaction have not
been measured. The nine references are selected for relevance rather than
padded to an arbitrary count. Before external submission, authors should
confirm their preferred names, affiliation wording, and any college-specific
front matter or page-count requirement.
