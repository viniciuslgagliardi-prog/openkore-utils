# OpenKore Utils

Network setup tools for **OpenKore** on latamRO (XKore 1 + bridge).

## Repository status

This is the official Git repository. Refactored code lives in `src/openkore_utils/`.

Build the `.exe` with `scripts\build.bat` and run it from the repo root (or any folder where you keep the binary).

## Architecture

**MVP** (Model–View–Presenter) + **Facade**. Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
src/openkore_utils/
  __main__.py          # python -m openkore_utils
  core/                # constants, paths
  domain/              # models + validators (pure rules)
  infrastructure/      # PowerShell, JSON, Windows admin
  services/            # use cases (network, setup, OpenKore)
  controllers/         # AppController — UI ↔ services bridge
  ui/                  # Tkinter window (display + input only)
```

## Features

- **OpenKore Utils** (GUI): network checklist, static IP, DNS, Cloudflare whitelist (`172.65.*`)
- Helper scripts: game shortcut, restore network, multibox
- `ptr/` and `recv/`: pointers and RE (future use after patches)

## Development

Requirements: Python 3.10+, Windows 10/11, administrator rights to change network settings.

```bat
cd src
py -3 -m openkore_utils
```

Build `.exe`:

```bat
scripts\build.bat
```

## OpenKore

The bot itself lives in a separate folder: `Documents\openkore\`
