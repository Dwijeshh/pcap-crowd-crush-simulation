"""Compare snapshot CSVs from two backends of the same scenario."""

import argparse
import csv
import math
import sys


FIELDS = ("x", "y", "vx", "vy")
IDENTITY_FIELDS = ("step", "id", "active")
STATIC_FIELDS = ("time", "preferred_speed", "radius")


def rows(path):
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = set(FIELDS + IDENTITY_FIELDS + STATIC_FIELDS)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path}: missing required snapshot columns")
        return list(reader)


def compare(reference_path, candidate_path, abs_tol):
    reference, candidate = rows(reference_path), rows(candidate_path)
    if len(reference) != len(candidate):
        raise ValueError(f"row count differs: {len(reference)} vs {len(candidate)}")
    if not reference:
        raise ValueError("no snapshot rows to compare")

    maxima = {field: 0.0 for field in FIELDS}
    worst = None
    for line, (left, right) in enumerate(zip(reference, candidate), start=2):
        if any(left[field] != right[field] for field in IDENTITY_FIELDS):
            raise ValueError(f"line {line}: step, id, or active state differs")
        for field in STATIC_FIELDS:
            if float(left[field]) != float(right[field]):
                raise ValueError(f"line {line}: {field} differs")
        for field in FIELDS:
            a, b = float(left[field]), float(right[field])
            if not (math.isfinite(a) and math.isfinite(b)):
                raise ValueError(f"line {line}: non-finite {field}")
            delta = abs(a - b)
            maxima[field] = max(maxima[field], delta)
            if delta > abs_tol and worst is None:
                worst = (line, field, delta)

    print(f"Compared {len(reference)} snapshot rows; maximum absolute differences:")
    for field in FIELDS:
        print(f"  {field}: {maxima[field]:.9g}")
    if worst:
        line, field, delta = worst
        raise ValueError(f"line {line}: {field} differs by {delta:.9g} (limit {abs_tol})")
    print(f"PASS: active states match and all motion fields are within {abs_tol:g}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", help="sequential _snapshots.csv file")
    parser.add_argument("candidate", help="CUDA _snapshots.csv file")
    parser.add_argument("--abs-tol", type=float, default=0.001,
                        help="maximum allowed absolute position/velocity difference")
    args = parser.parse_args()
    if not math.isfinite(args.abs_tol) or args.abs_tol < 0:
        parser.error("--abs-tol must be finite and nonnegative")
    try:
        compare(args.reference, args.candidate, args.abs_tol)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
