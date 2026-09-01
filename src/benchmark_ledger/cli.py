from __future__ import annotations

import argparse
import functools
import http.server
import json
from pathlib import Path
from typing import Sequence

from .pipeline import build, clean, compute_analysis, default_project_root
from .validation import ProjectValidationError, validate_project


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchmark-ledger",
        description="Validate, calculate, and inspect compute benchmark basis vintages.",
    )
    parser.add_argument("--project-root", type=Path, default=default_project_root())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate schemas, references, and semantic invariants")
    subparsers.add_parser("build", help="Build deterministic analysis and dashboard data")
    subparsers.add_parser("basis", help="Print the strict matched-specification basis monitor")
    subparsers.add_parser("hedge", help="Print the gated cross-benchmark tracking analysis")
    serve_parser = subparsers.add_parser("serve", help="Build and serve the dashboard locally")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", default=8000, type=int)
    subparsers.add_parser("clean", help="Remove only generated analysis artifacts")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.project_root.resolve()
    try:
        if args.command == "validate":
            report = validate_project(root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["valid"] else 1
        if args.command == "build":
            analysis = build(root)
            print(
                f"Built {len(analysis['pairs'])} matched cells; "
                f"{analysis['headline']['decision_eligible_cells']} decision eligible."
            )
            return 0
        if args.command == "basis":
            print(json.dumps(compute_analysis(root)["basis_monitor"], indent=2, sort_keys=True))
            return 0
        if args.command == "hedge":
            print(
                json.dumps(
                    compute_analysis(root)["analytics"]["cross_benchmark_tracking"],
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "clean":
            removed = clean(root)
            print(f"Removed {len(removed)} generated artifact(s).")
            return 0
        if args.command == "serve":
            build(root)
            handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
            server = http.server.ThreadingHTTPServer((args.host, args.port), handler)
            print(f"Dashboard: http://{args.host}:{args.port}/web/")
            print("Press Ctrl-C to stop.")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")
            finally:
                server.server_close()
            return 0
    except ProjectValidationError as exc:
        print(json.dumps({"valid": False, "issues": exc.issues}, indent=2, sort_keys=True))
        return 1
    return 2
