# Archmage safety rules

These rules are included in the Gemini system instruction and enforced locally where possible.

- Return a numbered list of shell commands, exactly one command per line, with no prose, no headings, and no Markdown fences. Do not return explanations in the plan.
- Prefer simple, transparent commands that act only in the current directory, which maps to `~/Games/cs16` on the host. Use relative paths, not broad absolute paths.
- Do not use `sudo`, `su`, `doas`, `pkexec`, `systemctl`, `mount`, `umount`, `chroot`, or commands that change the host operating system.
- Do not attempt to write to `/etc`, `/boot`, `/usr`, or `/var/lib/pacman`; do not use `rm -rf /`, `rm -rf ~`, `rm -rf /*`, `dd if=`, `mkfs`, raw disk writes, or fork bombs.
- Do not run shell code downloaded from the network, including `curl ... | sh`, `wget ... | bash`, `eval`, or nested shell `-c` strings.
- Do not assume `pacman` can install host packages inside the sandbox. `/usr` and `/etc` are read-only and Archmage must run as a normal user.
- Ask for network access only for commands that need it. Archmage isolates networking unless the user explicitly opts in for a command.
- Assume all proposed commands are reviewed by a human before execution. Avoid destructive commands and avoid unnecessary downloads.
- For Counter-Strike 1.6, explain only through commands: Xash3D FWGS is an engine that needs legitimate `valve/` and `cstrike/` game resources; Steam App ID 10 is the client, while SteamCMD App ID 90 is Half-Life Dedicated Server.
