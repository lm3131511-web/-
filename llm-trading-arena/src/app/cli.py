from __future__ import annotations

import argparse

from .production_pipeline import run_pipeline_cli


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LLM Trading Arena")
    parser.add_argument("--mode", choices=["paper", "shadow", "canary", "live"], required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--dry_run", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline_cli(mode=args.mode, config_path=args.config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
