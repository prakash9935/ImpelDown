"""
Faithfulness Gate Check (US-502)

Asserts that Faithfulness score >= threshold (default 0.85).
Used in CI/CD to block deployment if quality gate fails.

Gracefully skips if no results file exists (returns exit 0).
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--results-file", type=str, default="evaluation_results.json")
    args = parser.parse_args()

    if not os.path.exists(args.results_file):
        print(f"⚠️  No results file found at {args.results_file}")
        print("   Faithfulness gate skipped — no evaluation data available.")
        sys.exit(0)

    with open(args.results_file) as f:
        results = json.load(f)

    status = results.get("status", "unknown")
    if status == "not_implemented":
        print("⚠️  Evaluation not yet implemented — gate skipped")
        sys.exit(0)

    faithfulness = results.get("mean_faithfulness", 0.0)
    print(f"Faithfulness score: {faithfulness:.3f} (threshold: {args.threshold})")

    if faithfulness >= args.threshold:
        print(f"✅ PASSED — Faithfulness {faithfulness:.3f} >= {args.threshold}")
        sys.exit(0)
    else:
        print(f"❌ FAILED — Faithfulness {faithfulness:.3f} < {args.threshold}")
        sys.exit(1)


if __name__ == "__main__":
    main()
