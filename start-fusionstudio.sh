#!/usr/bin/env bash
# Native Linux launcher. See README.md for installation and processing flow.
set -euo pipefail

script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
project_root="$(cd -- "$(dirname -- "$script_path")" && pwd -P)"
python_path="${FUSIONSTUDIO_PYTHON:-$project_root/.venv/bin/python}"
if [[ -z "${FUSIONSTUDIO_PYTHON:-}" && ! -x "$python_path" && -x "$project_root/.venv-linux/bin/python" ]]; then
    python_path="$project_root/.venv-linux/bin/python"
fi

printf 'Input program: %s/main.py\nInput Python: %s\n' "$project_root" "$python_path"
printf 'Input requirements: %s/requirements.txt\n' "$project_root"
printf 'Output files: main.py reports application input/output paths before loading\n'
printf '[Linux launch 1/3] Checking Linux and the local Python environment\n'
if [[ "$(uname -s)" != Linux ]]; then
    printf 'Use this launcher inside Linux/WSL2; use fusionstudio.cmd on Windows.\n' >&2
    exit 1
fi
if [[ ! -x "$python_path" || ! -f "$project_root/main.py" ]]; then
    printf 'Missing Linux environment or main.py. Complete the Linux Installation steps in README.md.\n' >&2
    exit 1
fi
printf '[Linux launch 2/3] Checking installed dependencies\n'
"$python_path" -B -c 'import sys; from PySide6 import QtWidgets; import mitreattack, openpyxl, markdown; assert sys.platform == "linux", "Use native Linux Python"'
if [[ "$#" == 1 && ( "$1" == --check || "$1" == -Check ) ]]; then
    printf '[Linux launch 3/3] Ready; no window opened and no files written\n'
    exit 0
fi
printf '[Linux launch 3/3] Starting Fusion Studio; close the window to return to the shell\n'
cd -- "$project_root"
export PYTHONUTF8=1 PYTHONUNBUFFERED=1
exec "$python_path" -B "$project_root/main.py" "$@"
