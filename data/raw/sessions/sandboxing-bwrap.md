# Bubblewrap basics

Bubblewrap (`bwrap`) creates a new mount namespace and constructs the filesystem that a process can see. `--ro-bind SRC DEST` exposes a path read-only; `--bind SRC DEST` exposes it read-write; `--proc /proc`, `--dev /dev`, and `--tmpfs /tmp` provide standard runtime paths. `--unshare-net` gives the process a separate network namespace, normally without host network access.

Archmage's execution sandbox mounts `/usr`, `/lib`, `/lib64` when present, `/bin`, and `/etc` read-only; mounts `/proc` and `/dev`; creates a private `/tmp`; and bind-mounts only `~/Games/cs16` read-write. It also isolates PID, IPC, and UTS namespaces when supported. Network is isolated by default and may be enabled for a command only after an explicit prompt.

Example (illustrative; the source directory must already exist):

```bash
bwrap   --die-with-parent --new-session --unshare-pid --unshare-ipc --unshare-uts --unshare-net   --ro-bind /usr /usr   --ro-bind /lib /lib   --ro-bind /lib64 /lib64   --ro-bind /bin /bin   --ro-bind /etc /etc   --proc /proc --dev /dev --tmpfs /tmp   --bind "$HOME/Games/cs16" "$HOME/Games/cs16"   --chdir "$HOME/Games/cs16"   -- /bin/bash --noprofile --norc -c 'pwd; ls -la'
```

Some Arch installations make `/lib`, `/lib64`, or `/bin` symlinks or omit `/lib64`; Archmage handles missing optional paths rather than assuming they exist. Bubblewrap setup can be blocked by host kernel or user-namespace policy. Exact errors are surfaced to the user.

Sandboxing reduces filesystem exposure but does not make arbitrary software trustworthy. Review commands and never treat a model-generated command as safe merely because it runs under `bwrap`.
