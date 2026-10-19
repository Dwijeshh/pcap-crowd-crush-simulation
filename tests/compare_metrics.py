"""Compare summary and cell metrics from two simulation output prefixes."""

import argparse
import csv
import math
from pathlib import Path


TEXT_FIELDS = {"risk_category"}
INTEGER_FIELDS = {"step", "active", "exited", "bottleneck_occupancy",
                  "congested_cells", "column", "row", "count", "congested"}


def read(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def compare(left, right, tolerance, summary_only=False):
    total = 0
    max_difference = 0.0
    suffixes = ("_metrics.csv",) if summary_only else ("_metrics.csv", "_cells.csv")
    for suffix in suffixes:
        fields_a, rows_a = read(left + suffix)
        fields_b, rows_b = read(right + suffix)
        if fields_a != fields_b or len(rows_a) != len(rows_b):
            raise ValueError(f"{suffix}: schema or row count differs")
        for line, (a, b) in enumerate(zip(rows_a, rows_b), 2):
            for field in fields_a:
                if field in TEXT_FIELDS or field in INTEGER_FIELDS:
                    if a[field] != b[field]:
                        raise ValueError(f"{suffix}:{line}: {field} differs")
                else:
                    x, y = float(a[field]), float(b[field])
                    if not (math.isfinite(x) and math.isfinite(y)):
                        raise ValueError(f"{suffix}:{line}: non-finite {field}")
                    delta = abs(x - y)
                    max_difference = max(max_difference, delta)
                    if delta > tolerance:
                        raise ValueError(f"{suffix}:{line}: {field} differs by {delta:g}")
        total += len(rows_a)
        print(f"{suffix}: {len(rows_a)} rows match")
    print(f"PASS: {total} metric rows; maximum numeric difference {max_difference:g}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference_prefix")
    parser.add_argument("candidate_prefix")
    parser.add_argument("--abs-tol", type=float, default=0.001)
    parser.add_argument("--summary-only", action="store_true",
                        help="skip cell rows when device rounding moves a centre across a cell edge")
    args = parser.parse_args()
    if args.abs_tol < 0 or not math.isfinite(args.abs_tol):
        parser.error("--abs-tol must be finite and nonnegative")
    compare(args.reference_prefix, args.candidate_prefix, args.abs_tol, args.summary_only)
