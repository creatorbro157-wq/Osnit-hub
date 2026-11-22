import argparse
import json
from pathlib import Path

from exporter import save_csv, save_html, save_json
from scanner import run_investigation


def main() -> None:
    parser = argparse.ArgumentParser(description="Modular Email OSINT CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inv_parser = subparsers.add_parser("investigate", help="Investigate an email address")
    inv_parser.add_argument("email", help="Target email address")
    inv_parser.add_argument(
        "--platforms",
        default="platforms.json",
        help="Path to platforms JSON file (default: platforms.json)",
    )
    inv_parser.add_argument(
        "-o",
        "--output",
        help="Output file path (.json, .csv, or .html)",
    )

    args = parser.parse_args()

    if args.command == "investigate":
        report = run_investigation(args.email, Path(args.platforms))
        print(json.dumps(report, indent=2, ensure_ascii=False))

        if args.output:
            out_path = Path(args.output)
            ext = out_path.suffix.lower()
            if ext == ".csv":
                save_csv(report, out_path)
            elif ext == ".html":
                save_html(report, out_path)
            else:
                save_json(report, out_path)
            print(f"\nReport saved to: {out_path}")


if __name__ == "__main__":
    main()
