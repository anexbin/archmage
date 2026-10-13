# Counter-Strike 1.6 with Xash3D FWGS and CS16Client

1. Install and test a current Xash3D FWGS Linux build in `~/Games/cs16`. Upstream options include using a testing build or building the engine from source: <https://github.com/FWGS/xash3d-fwgs>.
2. Obtain the `valve/` and `cstrike/` resource folders from a legitimate copy of Half-Life/Counter-Strike that you own. Place the resources where the Xash3D engine expects them. Xash3D is an engine and does not include the copyrighted game assets.
3. Check the CS16Client project and releases for current Linux support: <https://github.com/Velaron/cs16-client>. Its README requires a recent Xash3D FWGS build and game resource folders. Linux builds have had varying support status; verify release notes before using them.
4. The standard Counter-Strike Steam client is App ID `10`: <https://store.steampowered.com/app/10/CounterStrike/>. SteamCMD App ID `90` is Half-Life Dedicated Server, not the normal desktop client. An optional server can be staged under the game directory using SteamCMD, for example `steamcmd +force_install_dir ./hlds +login anonymous +app_update 90 validate +quit`, if SteamCMD is already installed and you intend to set up a server. This does not replace owned client game assets.
5. Keep extracted resources, downloaded engine files, and any server files under `~/Games/cs16`. Review every proposed command; grant network access only when required.

## Important

Do not run `pacman`, `sudo`, or system installation commands through Archmage. Install host dependencies separately. The sandbox exposes `/usr` and `/etc` read-only and is not designed to mutate the host operating system.
