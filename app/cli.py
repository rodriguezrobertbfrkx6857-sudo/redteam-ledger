import argparse
import json
from pathlib import Path

from app.evaluation import run


def main():
    parser = argparse.ArgumentParser(description="Reproducible detector regression evaluation")
    parser.add_argument("--target", choices=["keyword", "normalized", "sentinel"], default="normalized")
    parser.add_argument("--split", choices=["dev", "challenge", "all"], default="challenge")
    parser.add_argument("--output", type=Path, default=Path("report.json"))
    parser.add_argument("--gate", action="store_true", help="Exit 1 if the measured gate fails")
    args = parser.parse_args()
    result = run(args.target, args.split)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))
    return int(args.gate and not result["gate"]["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
