"""Human approval, network gating, and Bubblewrap command execution."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ..config import GAMES_DIR


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    sandbox_error: str | None = None

    @property
    def combined_output(self) -> str:
        pieces: list[str] = []
        if self.stdout.strip():
            pieces.append(self.stdout.rstrip())
        if self.stderr.strip():
            pieces.append("[stderr]\n" + self.stderr.rstrip())
        return "\n".join(pieces)


def explain_command(command: str) -> str:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return "Run the proposed shell command inside the game-directory sandbox."
    executable = Path(tokens[0]).name
    if executable == "mkdir":
        return "Create directory paths inside the sandbox's writable game folder."
    if executable == "git":
        if len(tokens) > 1 and tokens[1] == "clone":
            return "Clone a source repository into the game folder; this normally requires network access."
        return "Run a Git operation inside the sandbox; remote operations may require network access."
    if executable in {"curl", "wget", "aria2c"}:
        return "Download the specified resource into the sandbox; inspect the URL and enable network only if needed."
    if executable == "steamcmd":
        return "Fetch or verify Steam server content inside the sandbox; this requires network access."
    if executable in {"tar", "unzip", "7z"}:
        return "Extract an archive in the sandbox; confirm the archive name and destination."
    if executable in {"ls", "find", "file", "pwd", "du", "stat"}:
        return "Inspect files or paths without intentionally modifying them."
    if executable in {"cmake", "make", "ninja", "meson"}:
        return "Build software in the writable sandbox folder; review build scripts before execution."
    if executable in {"printf", "echo", "cat", "head", "tail"}:
        return "Print or inspect text in the sandbox."
    return "Run this command in Bubblewrap with system paths read-only and persistent writes scoped to the game folder."


def command_needs_network(command: str) -> bool:
    """Heuristic only; prompts for likely networked actions, not every use of a program."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    if not tokens:
        return False
    for index, token in enumerate(tokens):
        name = Path(token).name.lower()
        following = tokens[index + 1].lower() if index + 1 < len(tokens) else ""
        if name in {"curl", "wget", "steamcmd", "aria2c"}:
            return True
        if name == "git" and following in {"clone", "fetch", "pull", "push", "submodule", "ls-remote"}:
            return True
        if name in {"pip", "pip3"} and following in {"install", "download"}:
            return True
        if name == "pacman" and any(arg.startswith("-") and "S" in arg for arg in tokens[index + 1 :]):
            return True
    return False


def build_bwrap_argv(command: str, network_enabled: bool, games_dir: Path | str = GAMES_DIR) -> list[str]:
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise FileNotFoundError("bwrap executable not found in PATH")

    game_path = Path(games_dir).expanduser().absolute()
    try:
        game_path.relative_to(Path.home().absolute())
    except ValueError as exc:
        raise RuntimeError("The writable sandbox directory must be inside your home directory.") from exc
    # Do not let a pre-existing symlink redirect writes outside the intended game folder.
    for candidate in (game_path, *game_path.parents):
        if candidate.is_symlink():
            raise RuntimeError(f"Refusing a symlinked sandbox path component: {candidate}")
    game_path.mkdir(parents=True, exist_ok=True)
    args = [bwrap, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts"]
    if not network_enabled:
        args.append("--unshare-net")

    # Arch paths vary: /lib64 can be absent and /bin or /lib can be symlinks.
    for source, destination in (("/usr", "/usr"), ("/lib", "/lib"), ("/lib64", "/lib64"), ("/bin", "/bin"), ("/etc", "/etc")):
        if os.path.lexists(source):
            args.extend(["--ro-bind", source, destination])
        elif destination == "/lib64":
            args.extend(["--dir", destination])

    args.extend([
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--bind", str(game_path), str(game_path),
        "--clearenv",
        "--setenv", "HOME", str(game_path),
        "--setenv", "PATH", "/usr/local/sbin:/usr/local/bin:/usr/bin:/bin",
        "--setenv", "LANG", os.environ.get("LANG", "C.UTF-8"),
        "--chdir", str(game_path),
        "--", "/bin/bash", "--noprofile", "--norc", "-c",
        "printf '__ARCHMAGE_SANDBOX_STARTED__\\n'; exec /bin/bash --noprofile --norc -c " + shlex.quote(command),
    ])
    return args


def run_in_sandbox(command: str, network_enabled: bool, games_dir: Path | str = GAMES_DIR, timeout: int = 300) -> ExecutionResult:
    try:
        argv = build_bwrap_argv(command, network_enabled, games_dir)
    except FileNotFoundError as exc:
        raise RuntimeError(str(exc) + ". Install Bubblewrap manually, for example: pacman -S bubblewrap") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not prepare Bubblewrap sandbox: {exc}") from exc

    try:
        completed = subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return ExecutionResult(124, str(stdout), str(stderr) + "\nArchmage stopped the command after the timeout.")
    except OSError as exc:
        raise RuntimeError(f"Failed to invoke bwrap: {exc}. Install it manually with: pacman -S bubblewrap") from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    sentinel = "__ARCHMAGE_SANDBOX_STARTED__\n"
    if sentinel in stdout:
        stdout = stdout.replace(sentinel, "", 1)
    else:
        exact_error = stderr.strip() or stdout.strip() or f"bwrap exited with status {completed.returncode} without starting the command"
        raise RuntimeError(f"Bubblewrap failed: {exact_error}\nInstall Bubblewrap manually with: pacman -S bubblewrap")
    return ExecutionResult(completed.returncode, stdout, stderr)
