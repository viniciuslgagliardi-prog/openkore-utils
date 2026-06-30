# OpenKore Utils

Ferramentas de rede para **OpenKore** no **latamRO** — modo **XKore 1 + bridge** (login pelo Ragexe).

> **Screenshots:** adicione PNGs em [`docs/img/`](docs/img/README.md) (`screenshot-setup.png`, `screenshot-network.png`, `screenshot-profiles.png`) para exibir capturas no README e no [GUIA](docs/GUIA.md).

## Documentação

| Guia | Descrição |
|------|-----------|
| **[docs/GUIA.md](docs/GUIA.md)** | **Tutorial completo passo a passo** (instalação, rede, perfis, multibox, troubleshooting) |
| [docs/RUN.md](docs/RUN.md) | Resumo rápido (5 passos) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Arquitetura do código |
| [CHANGELOG.md](CHANGELOG.md) | Histórico de versões |

## Início rápido

1. Baixe ou compile `OpenKoreUtils.exe` → execute **como administrador**
2. **Setup** → pastas OpenKore e Ragnarok → **Save**
3. **Network / DNS** → *Apply network from adapter* → *Add* no IP `172.65.*`
4. **Profiles** → selecione o perfil → **Run OpenKore** → **Run Ragexe** → login no jogo
5. Ao terminar → **Reset setup** (volta DHCP)

Tutorial detalhado: **[docs/GUIA.md](docs/GUIA.md)**

## Capturas de tela (opcional)

Instruções em **[docs/img/README.md](docs/img/README.md)**. Depois de salvar os PNGs, o README e o guia passam a exibir as imagens automaticamente.

## O que faz

- IP estático na LAN + DNS (Cloudflare / Google)
- Whitelist de IPs `172.65.*` na placa de rede (latamRO / Cloudflare)
- Gestão de perfis OpenKore (`profiles/`)
- Lançamento do OpenKore e do Ragexe com o perfil selecionado

## Requisitos

- Windows 10/11, **permissão de administrador**
- OpenKore (`openkore.pl`, `control/`, `profiles/`)
- Ragnarok latam (`Ragexe.exe`, `bridge.dll`)
- Perl no PATH (Strawberry Perl) para *Run OpenKore*

## Instalação

### Executável (release)

Baixe `OpenKoreUtils.exe` em [Releases](https://github.com/viniciuslgagliardi-prog/openkore-utils/releases) ou compile:

```bat
git clone https://github.com/viniciuslgagliardi-prog/openkore-utils.git
cd openkore-utils
scripts\build.bat
```

### Desenvolvimento

```bat
cd src
py -3 -m openkore_utils
```

Python 3.10+

## Estrutura do projeto

```
src/openkore_utils/
  ui/                  # janela Tkinter (Setup · Network · Profiles)
  controllers/         # AppController
  services/            # rede, perfis, launch, OpenKore
  infrastructure/      # PowerShell, JSON, admin Windows
docs/
  GUIA.md              # tutorial de uso
  img/                 # screenshots para o README
scripts/
  build.bat            # PyInstaller → OpenKoreUtils.exe
```

## Config local

`openkore_utils_config.json` fica **ao lado do `.exe`** (paths, IPs, adaptador). Não é versionado.

## OpenKore

O bot fica em pasta separada, em geral `Documents\openkore\`. O Utils só aponta para ela na aba Setup.

## Licença

Uso pessoal / comunidade OpenKore. Sem garantias.
