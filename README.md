# Archmage

Archmage is a local, synchronous CLI assistant for planning and performing narrowly scoped Arch Linux game-installation tasks with Gemini for command planning, a local `all-MiniLM-L6-v2` retrieval index, per-command human approval, a denylist, an append-only audit log, and a Bubblewrap (`bwrap`) mount sandbox. It is designed to run as a normal user and makes no background service or web server.

## Setup

1. Install Python 3.11+, `venv`, and Bubblewrap on Arch Linux. Install Bubblewrap manually on the host; Archmage itself never runs package-manager commands as root:

   ```bash
   sudo pacman -S bubblewrap python python-pip
   ```

2. From the project root, create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` using a key from Google AI Studio. `GEMINI_MODEL` is optional.

   ```bash
   cp .env.example .env
   nano .env
   ```

4. Ensure the corpus files in `data/raw/sessions/` are present. The first embedding build downloads the sentence-transformers model once and runs it locally on CPU.

## First run

From the project root, activate the virtual environment and build the local index:

```bash
source .venv/bin/activate
cd src
python -m archmage.ingest.embedder
```

Then ask for a plan:

```bash
python -m archmage.cli "install CS 1.6 and sandbox it"
```

Archmage prints every proposed command and a short explanation. Enter `y` to approve a command, `N` (or press Enter) to skip it, or `explain` to see more context. Commands recognized as needing network access require a second, explicit network opt-in; networking is otherwise isolated with `bwrap --unshare-net`. Use `--plan-only` to query Gemini and display a plan without prompting to execute commands:

```bash
python -m archmage.cli --plan-only "inspect the game directory"
```

The audit log is written to `logs/audit/YYYY-MM-DD.log`. The process stops if an audit entry cannot be written. It refuses to run as root.

## CS 1.6 notes

- Xash3D FWGS is an engine; it still needs legitimate game resource files. Follow the upstream [Xash3D FWGS installation notes](https://github.com/FWGS/xash3d-fwgs) and [CS16Client project](https://github.com/Velaron/cs16-client). CS16Client's upstream README says to use a current Xash3D FWGS build and copy the `valve` and `cstrike` resource folders from a game copy you own.
- Steam's Counter-Strike client is [App ID 10](https://store.steampowered.com/app/10/CounterStrike/). SteamCMD App ID 90 is **Half-Life Dedicated Server**, a server/tool distribution—not the standard desktop CS 1.6 client. Use it only if you intend to set up a dedicated server. See [SteamDB App 90](https://steamdb.info/app/90/).
- Archmage cannot install host system packages inside its sandbox: `/usr` and `/etc` are read-only, it does not run as root, and the writable game directory is intentionally narrow. Install host dependencies manually first.

## Known limitations

- Google marks `google-generativeai` as a legacy, no-longer-actively-maintained SDK and recommends `google-genai`. This project retains `google-generativeai` because that is an explicit requirement. Model names, API availability, and free-tier quotas change; adjust `GEMINI_MODEL` if needed.
- The model may propose commands that do not work on the host. Review all commands before approving them. The denylist is defense in depth, not a complete shell-language security proof.
- Bubblewrap is a mount/user-namespace sandbox, not a virtual machine. It intentionally exposes only selected system paths and the game directory; GUI launch support for Hyprland/Wayland sockets is not configured in this version.
- The `/tmp` mount is a private, disposable tmpfs because it is explicitly part of the requested Bubblewrap layout. Persistent writes are intended to be limited to `~/Games/cs16`.
- The first CPU embedding run downloads model artifacts from Hugging Face and can take time on low-memory hardware. No GPU is required.
- This tool does not automatically update itself, run a daemon, or support unattended execution.
