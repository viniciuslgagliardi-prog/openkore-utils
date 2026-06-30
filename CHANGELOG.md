# Changelog

## [5.2.0] — 2026-06-29

### Added

- GUI com abas **Setup**, **Network / DNS** e **Profiles** (tema Dracula)
- Configuração de pastas OpenKore e Ragnarok
- IP estático LAN, DNS e whitelist `172.65.*` via PowerShell
- Perfis OpenKore: criar, listar, abrir pasta
- Botões **Run OpenKore** e **Run Ragexe** (XKore 1 + bridge)
- Documentação passo a passo em [docs/GUIA.md](docs/GUIA.md)
- Build com `scripts/build.bat` (PyInstaller, UAC admin)

### Notes

- Config local: `openkore_utils_config.json` ao lado do `.exe` (não versionado)
- Requer Windows 10/11 e execução como administrador para alterar rede
