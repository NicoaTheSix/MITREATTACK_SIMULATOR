# Installation and Startup

## Requirements

Use Windows or a Linux graphical session with the project source and its declared dependencies. The application is a Python / PySide6 desktop program. Linux is tested with Kali 2026.2 on WSL2/WSLg, Python 3.14.7 and PySide6 6.12.0. WSLg supplies Linux GUI windows on Windows; a terminal-only Linux server requires a graphical session for interactive use.

## Create the project environment

Open PowerShell in the project folder and create a project-local virtual environment:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
```

The Windows environment snapshot is in `requirements-lock.txt`. Linux users should install from `requirements.txt` in their own Linux environment. The root README provides the complete installation reference.

## Start the interface

```powershell
& '.\.venv\Scripts\python.exe' -B '.\main.py'
```

The application announces absolute input paths before loading the selected local dataset. Wait for the completed loading stages. If a previous recovery checkpoint is available, choose whether to restore it.

## Linux / WSL2 installation and startup

Inside Kali Linux, install the Python environment support, Qt runtime libraries and Traditional Chinese fonts:

```bash
printf 'Input package sources: /etc/apt/sources.list and /etc/apt/sources.list.d\nOutput package directories: /usr, /var/lib/apt/lists, /var/cache/apt\n'
sudo apt-get update
sudo apt-get install -y --no-install-recommends python3 python3-venv \
  libegl1 libopengl0 libglib2.0-0t64 libxkbcommon-x11-0 \
  libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-image0 libxcb-render-util0 fonts-noto-cjk
```

Prefer a separate source copy in the Linux home directory. In that project's folder:

```bash
printf 'Input requirements: %s/requirements.txt\nOutput environment: %s/.venv\n' "$PWD" "$PWD"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
# Download only when a valid cached ATT&CK snapshot is not already present:
.venv/bin/python -B scripts/download_attack_data.py
bash start-ttpselecter.sh
```

Do not reuse Windows `.venv` or the `.cmd` launch scripts in Linux. For a shared Windows source folder, create `.venv-linux` instead; the Bash launcher detects its `bin/python` when Linux `.venv/bin/python` is absent. `bash start-ttpselecter.sh --check` checks dependencies; `--no-session` disables recovery for an isolated workspace. The launcher prints absolute inputs and three-stage progress, then the application reports dataset/settings/session paths and loading progress. Keep its terminal open while using the window. Use `QT_QPA_PLATFORM=xcb bash start-ttpselecter.sh` to select WSLg/X11 explicitly; unset an earlier `QT_QPA_PLATFORM=offscreen` setting for visible windows. Other distributions may use different system package names.

## One-time Linux command setup

After completing Linux installation, run `bash setup-ttpselecter.sh` in the project folder. Reopen Bash or Zsh, then enter `ttpselecter` from any directory. For the current terminal immediately, use `export PATH="$HOME/.local/bin:$PATH"` once. `ttpselecter --check` validates dependencies without opening a window.

Setup writes an executable wrapper to the current user's `~/.local/bin`, retains the installed project at its original location, and adds a marked PATH block to Bash/Zsh startup files. Existing profiles are backed up before changes; repeated setup avoids duplicate blocks/backups. No `sudo` is needed. After moving the project, rerun setup there. Other shells need their own PATH configuration. Setup prints absolute inputs, command/profile/backup outputs and four-stage progress; preflight refuses unrelated commands or edited managed blocks.

## Data and language

The current default dataset is ATT&CK v20.0. Downloaded snapshots can be used offline; downloading other releases requires access to official MITRE GitHub sources.

The interface and manual default to English. Choose **Settings → Language → 繁體中文（臺灣）** for Taiwan Traditional Chinese. The preference is stored in the local settings file, separately from Studio documents.

[Return to the operating manual](in_app_manual_en.md)
