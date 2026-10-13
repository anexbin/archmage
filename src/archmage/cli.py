"""Command-line entry point for Archmage."""
from __future__ import annotations

import os
import sys


def _build_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Archmage: an AI-assisted, human-approved Arch Linux sandbox CLI")
    parser.add_argument("query", help="Task to plan with Gemini")
    parser.add_argument("--plan-only", action="store_true", help="Show the proposed plan without execution prompts")
    return parser


def main() -> int:
    try:
        from . import config
    except RuntimeError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        print("Refusing to run as root. Run Archmage as a normal user.", file=sys.stderr)
        return 1

    args = _build_parser().parse_args()
    corpus_files = sorted(config.RAW_SESSIONS_DIR.rglob("*.md")) if config.RAW_SESSIONS_DIR.is_dir() else []
    if not corpus_files:
        print(
            f"Corpus directory is empty: {config.RAW_SESSIONS_DIR}\n"
            "Add Markdown files (*.md) to data/raw/sessions/ and rerun Archmage.",
            file=sys.stderr,
        )
        return 1

    if not config.INDEX_PATH.is_file():
        print("Embedding index is missing; building it from the local corpus (CPU)...")
        try:
            from .ingest.embedder import build_index
            build_index()
        except SystemExit as exc:
            return int(exc.code or 1)
        except Exception as exc:
            print(f"Could not build the embedding index: {exc}", file=sys.stderr)
            return 1

    try:
        from .rag.retriever import Retriever
        from .llm.client import GeminiClient
        from .agent.loop import PlanParseError, execute_plan, parse_numbered_commands

        retriever = Retriever(config.INDEX_PATH)
        context = retriever.retrieve(args.query, top_k=config.TOP_K)
        client = GeminiClient()
        raw_response = client.generate_command_plan(args.query, context)
        try:
            commands = parse_numbered_commands(raw_response)
        except PlanParseError as first_error:
            print(f"Gemini response format invalid ({first_error}); requesting one strict retry.", file=sys.stderr)
            retry_response = None
            try:
                retry_response = client.generate_command_plan(args.query, context, repair_response=raw_response)
                commands = parse_numbered_commands(retry_response)
                raw_response = retry_response
            except Exception as retry_error:
                print(f"Could not parse Gemini's response after one retry: {retry_error}", file=sys.stderr)
                print("Raw Gemini response:", file=sys.stderr)
                print(retry_response if retry_response is not None else raw_response, file=sys.stderr)
                return 1

        print("\nArchmage proposed plan")
        print("Retrieved context:")
        for item in context:
            print("  - {0} (score {1:.3f})".format(item.get("source", "unknown"), float(item.get("score", 0.0))))
        for number, command in enumerate(commands, start=1):
            print(f"{number}. {command}")
        execute_plan(commands, plan_only=args.plan_only)
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
