"""CLI — benchmark the four prompting strategies by execution accuracy."""
from __future__ import annotations

import argparse
import json

from .benchmark import run
from .generator import get_generator


def main() -> None:
    ap = argparse.ArgumentParser(description="Benchmark NL->SQL strategies by execution accuracy.")
    ap.add_argument("--provider", choices=["auto", "mock", "bedrock", "anthropic"], default="auto")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = run(get_generator(args.provider))
    if args.json:
        print(json.dumps(res, indent=2))
        return

    m = res["_meta"]
    print("=" * 76)
    print(f"  TEXT-TO-SQL — strategy benchmark   ({m['n']} questions, {m['provider']})")
    print("=" * 76)
    print(f"{'strategy':<24}{'exec acc':>10}{'exact':>9}   {'by failure mode (exec acc)':<30}")
    print("-" * 76)
    for name, r in res["strategies"].items():
        bf = "  ".join(f"{k}:{v:.2f}" for k, v in sorted(r["by_failure"].items()))
        print(f"{name:<24}{r['execution_accuracy']:>10.1%}{r['exact_match']:>9.1%}   {bf:<30}")
    print("-" * 76)
    z = res["strategies"]["zero_shot"]
    print(f"execution accuracy vs string match (zero-shot): {z['execution_accuracy']:.0%} vs "
          f"{z['exact_match']:.0%} — string match under-counts correct-but-reworded SQL")
    print(f"best strategy: {res['best']}")
    print("=" * 76)


if __name__ == "__main__":
    main()
