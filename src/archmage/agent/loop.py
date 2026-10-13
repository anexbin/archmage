"""Command-plan parsing and interactive, per-command approval loop."""
from __future__ import annotations

import re
import sys

from ..config import GAMES_DIR
from ..safety.audit import AuditLogError, log_action
from ..safety.denylist import validate_command
from .tools import command_needs_network, explain_command, run_in_sandbox

_NUMBERED_LINE = re.compile(r"^\s*(\d+)[.)]\s+(.+?)\s*$")


class PlanParseError(ValueError):
    pass


def parse_numbered_commands(response: str) -> list[str]:
    """Accept only a numbered list containing one shell command on each nonblank line."""
    lines = [line.rstrip() for line in response.strip().splitlines() if line.strip()]
    if not lines:
        raise PlanParseError("Gemini returned no commands.")
    commands: list[str] = []
    expected = 1
    for line in lines:
        if line.strip() in {"```", "```bash", "```sh", "```shell"}:
            continue
        match = _NUMBERED_LINE.match(line)
        if not match:
            raise PlanParseError(f"Line is not a numbered command: {line[:120]}")
        number = int(match.group(1))
        command = match.group(2).strip()
        if number != expected:
            raise PlanParseError(f"Expected command number {expected}, received {number}.")
        if not command:
            raise PlanParseError("A numbered command line is empty.")
        commands.append(command)
        expected += 1
    if not commands:
        raise PlanParseError("Gemini response contained no numbered commands.")
    return commands


def _write_audit_or_die(command: str, decision: str, exit_code: int | None, output: str = "", network_enabled: bool = False) -> None:
    try:
        path = log_action(command, decision, exit_code, output, network_enabled=network_enabled)
    except AuditLogError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Audit: {path}")


def _ask_for_approval() -> str:
    while True:
        try:
            answer = input("[y/N/explain] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return "n"
        if answer in {"y", "n", "", "explain"}:
            return answer or "n"
        print("Please enter y, N, or explain.")


def execute_plan(commands: list[str], plan_only: bool = False) -> dict[str, int]:
    summary = {"planned": len(commands), "executed": 0, "succeeded": 0, "failed": 0, "skipped_or_blocked": 0}
    if plan_only:
        print("Plan-only mode: no commands will be executed.")
        return summary

    for index, command in enumerate(commands, start=1):
        print(f"\n[{index}/{len(commands)}] Command: {command}")
        print(f"Why: {explain_command(command)}")
        validation = validate_command(command)
        if validation.needs_explicit_yes:
            print(f"BLOCKED: {validation.reason}")
            print("To acknowledge this blocked command, type 'yes' (not 'y'); it will remain blocked and will not execute.")
            try:
                acknowledgement = input("Type yes to acknowledge: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                acknowledgement = ""
            decision = "blocked_sudo_acknowledged" if acknowledgement == "yes" else "blocked_sudo_rejected"
            _write_audit_or_die(command, decision, None, validation.reason)
            summary["skipped_or_blocked"] += 1
            continue
        if not validation.allowed:
            print(f"BLOCKED: {validation.reason}")
            _write_audit_or_die(command, "blocked_denylist", None, validation.reason)
            summary["skipped_or_blocked"] += 1
            continue

        while True:
            answer = _ask_for_approval()
            if answer == "explain":
                print(f"More detail: this runs as your normal user with a separate mount namespace. System directories are read-only; persistent writes are scoped to {GAMES_DIR}.")
                print("Review the exact command and any URLs before approving it.")
                continue
            break

        if answer != "y":
            _write_audit_or_die(command, "skipped_by_user", None, "")
            summary["skipped_or_blocked"] += 1
            continue

        needs_network = command_needs_network(command)
        network_enabled = False
        if needs_network:
            print("NETWORK WARNING: this command appears to access the network. Network access is disabled by default.")
            print("Enable network access inside the Bubblewrap sandbox for this command only? [y/N] ", end="", flush=True)
            try:
                network_answer = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                network_answer = ""
            if network_answer != "y":
                _write_audit_or_die(command, "skipped_network_not_enabled", None, "", False)
                summary["skipped_or_blocked"] += 1
                continue
            network_enabled = True

        print("Executing in Bubblewrap sandbox...")
        try:
            result = run_in_sandbox(command, network_enabled)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            _write_audit_or_die(command, "sandbox_failed", None, str(exc), network_enabled)
            summary["failed"] += 1
            break

        output = result.combined_output
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        _write_audit_or_die(command, "approved_and_executed", result.exit_code, output, network_enabled)
        summary["executed"] += 1
        if result.exit_code == 0:
            summary["succeeded"] += 1
        else:
            summary["failed"] += 1
            print(f"Command exited with status {result.exit_code}.")

    print("\nArchmage summary")
    print(f"  Planned:             {summary['planned']}")
    print(f"  Executed:            {summary['executed']}")
    print(f"  Succeeded:           {summary['succeeded']}")
    print(f"  Failed:              {summary['failed']}")
    print(f"  Skipped or blocked:  {summary['skipped_or_blocked']}")
    return summary
