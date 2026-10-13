"""Conservative local command denylist for commands proposed by an LLM."""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationResult:
    allowed: bool
    reason: str = ""
    needs_explicit_yes: bool = False


_FORBIDDEN_PATH = re.compile(r"(?<![A-Za-z0-9_.-])/(?:etc|boot|usr|var/lib/pacman)(?:/|\b)", re.IGNORECASE)
_FORK_BOMB = re.compile(r":\s*\(\s*\)\s*\{[^}]*:\s*\|\s*:\s*&?[^}]*\}\s*;\s*:", re.IGNORECASE)
_WRITE_COMMAND = re.compile(
    r"\b(?:cp|mv|install|mkdir|touch|truncate|tee|chmod|chown|chgrp|ln|rm|sed\s+-i|perl\s+-i|dd|mkfs|pacman)\b",
    re.IGNORECASE,
)
_REDIRECT_TO_PROTECTED = re.compile(
    r"(?:>>?|\btee\b(?:\s+-a)?|\binstall\b|\btruncate\b)\s*(?:--\s*)?['\"]?(/(?:etc|boot|usr|var/lib/pacman)(?:/|\b))",
    re.IGNORECASE,
)
_NETWORK_PIPE = re.compile(r"\b(?:curl|wget)\b[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)\b", re.IGNORECASE)
_NESTED_SHELL = re.compile(r"\b(?:bash|sh|zsh|fish)\s+-c\b|\beval\b|`|\$\(", re.IGNORECASE)
_INLINE_CODE = re.compile(r"\b(?:python(?:\d+(?:\.\d+)?)?|perl|ruby|node|php)\s+-(?:c|e|r)\b", re.IGNORECASE)


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _contains_dangerous_recursive_rm(command: str) -> bool:
    """Catch root/home recursive removals, including split/long flags."""
    # Split common shell command separators. False positives are preferable to allowing a dangerous rm.
    segments = re.split(r"&&|\|\||[;|]", command)
    for segment in segments:
        match = re.search(r"\brm\b(.*)$", segment.strip(), re.IGNORECASE)
        if not match:
            continue
        args = _tokens(match.group(1))
        recursive = False
        force = False
        targets: list[str] = []
        options_open = True
        for token in args:
            if options_open and token == "--":
                options_open = False
                continue
            if options_open and token.startswith("--"):
                if token == "--recursive":
                    recursive = True
                    continue
                if token == "--force":
                    force = True
                    continue
                if token in {"--no-preserve-root", "--one-file-system", "--preserve-root"}:
                    continue
            if options_open and token.startswith("-") and token != "-":
                flags = token[1:]
                recursive = recursive or "r" in flags.lower()
                force = force or "f" in flags.lower()
                continue
            options_open = False
            targets.append(token)
        # rm -r against these targets is already hazardous; force is not required for a directory.
        dangerous_targets = {"/", "/*", "/.", "~", "~/", "~/*", "$HOME", "${HOME}", "$HOME/", "${HOME}/"}
        if recursive and any(target in dangerous_targets for target in targets):
            return True
        if recursive and force and any(target.startswith("/") and target.rstrip("/") == "" for target in targets):
            return True
    return False


def validate_command(command: str) -> ValidationResult:
    text = command.strip()
    if not text:
        return ValidationResult(False, "Empty command.")
    if "\x00" in text or "\n" in text or "\r" in text:
        return ValidationResult(False, "A command must be a single line.")

    if _FORK_BOMB.search(text) or re.search(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", text):
        return ValidationResult(False, "Fork-bomb patterns are blocked.")
    if re.search(r"\bdd\b[^;&|]*\bif\s*=", text, re.IGNORECASE):
        return ValidationResult(False, "dd input/raw-device operations are blocked.")
    if re.search(r"\bmkfs(?:\.[A-Za-z0-9_-]+)?\b", text, re.IGNORECASE):
        return ValidationResult(False, "Filesystem formatting commands (mkfs) are blocked.")
    if re.search(r"(?:>|>>|\bof=)\s*['\"]?/dev/sd[a-z0-9]*", text, re.IGNORECASE):
        return ValidationResult(False, "Writes to raw disk devices are blocked.")
    if _contains_dangerous_recursive_rm(text):
        return ValidationResult(False, "Destructive recursive rm root/home patterns are blocked.")
    if re.search(r"\brm\b[^;&|]*\s--no-preserve-root[^;&|]*\s/", text, re.IGNORECASE):
        return ValidationResult(False, "Destructive root filesystem removal is blocked.")
    if _NETWORK_PIPE.search(text):
        return ValidationResult(False, "Piping downloaded network content directly into a shell is blocked.")
    if _NESTED_SHELL.search(text) or _INLINE_CODE.search(text):
        return ValidationResult(False, "Nested shell or inline code evaluation is blocked; use simple commands that can be reviewed.")

    tokens = _tokens(text)
    privileged = {"sudo", "su", "doas", "pkexec"}
    if any(token.rsplit("/", 1)[-1].lower() in privileged for token in tokens):
        return ValidationResult(False, "Privilege escalation is forbidden: Archmage never executes as root.", True)

    if _FORBIDDEN_PATH.search(text) and _WRITE_COMMAND.search(text):
        return ValidationResult(False, "Commands that may write to /etc, /boot, /usr, or /var/lib/pacman are blocked.")
    if _REDIRECT_TO_PROTECTED.search(text):
        return ValidationResult(False, "Redirection or installation to a protected system path is blocked.")

    if tokens and tokens[0] == "pacman":
        mutating_options = {"-S", "-U", "-R", "-D", "-F", "--sync", "--upgrade", "--remove", "--database", "--files", "--refresh"}
        if any(token in mutating_options or (token.startswith("-") and not token.startswith("--") and any(letter in token[1:] for letter in "SURDF")) for token in tokens[1:]):
            return ValidationResult(False, "Mutating pacman operations are not supported inside the sandbox. Install host packages manually.")

    return ValidationResult(True)
