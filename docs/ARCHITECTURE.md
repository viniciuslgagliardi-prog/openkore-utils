# Architecture — OpenKore Utils

## Pattern: **MVP** (Model–View–Presenter) + **Facade**

| Layer | Folder | Responsibility |
|--------|-------|------------------|
| **View** | `ui/` | Tkinter: buttons, labels, tabs — display and capture clicks only |
| **Presenter** | `controllers/` | Orchestrates UI actions (calls services, saves config) |
| **Model / domain** | `domain/` | Pure rules: validate IP, build checklist |
| **Services** | `services/` | Use cases: apply network, read OpenKore |
| **Infrastructure** | `infrastructure/` | Technical details: PowerShell, JSON file, Windows admin |

## SOLID (how we apply it)

- **S** — One responsibility per file (`validators.py` only validates, `network_service.py` only talks to the adapter).
- **O** — New checklist steps go into `SetupService` without rewriting the UI.
- **L** — N/A (little inheritance).
- **I** — Small, focused services (`HostsService`, `OpenKoreService`).
- **D** — The UI depends on `AppController`, not PowerShell directly.

## Click flow

```
User clicks "Fix" (View)
    -> AppController.apply_lan() (Presenter)
        -> NetworkService.apply_lan_profile() (Service)
            -> run_powershell() (Infrastructure)
    -> ConfigStore.save() (Infrastructure)
    -> View updates checklist
```

## How to run

```bat
cd src
py -3 -m openkore_utils
```

## Structure

```
src/openkore_utils/
  __main__.py          # python -m openkore_utils
  core/                # constants, paths
  domain/              # models + validators
  infrastructure/      # PS, config, admin
  services/            # business logic
  controllers/         # UI <-> services bridge
  ui/                  # Tkinter window
```
