#!/usr/bin/env bash
# One-time Linux command setup. See README.md.
set -euo pipefail
script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
project_root="$(cd -- "$(dirname -- "$script_path")" && pwd -P)"
printf 'Input installer: %s/scripts/install_linux_command.py\n' "$project_root"
exec python3 -B "$project_root/scripts/install_linux_command.py" "$@"
