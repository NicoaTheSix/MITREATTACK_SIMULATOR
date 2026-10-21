"""Register a per-user Linux launcher and Bash/Zsh PATH. Flow: scripts/README.md."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

COMMAND_MARKER = '# Managed by TTP Selection Studio: setup-ttpselecter.sh'
BLOCK_START = '# >>> TTP Selection Studio: user command PATH >>>'
BLOCK_END = '# <<< TTP Selection Studio: user command PATH <<<'
PATH_BLOCK = '''# >>> TTP Selection Studio: user command PATH >>>
case ":${PATH:-}:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin${PATH:+:$PATH}" ;;
esac
# <<< TTP Selection Studio: user command PATH <<<
'''


def profile_plan(path):
    if path.is_symlink() and not path.is_file():
        raise ValueError(f'Profile is not a readable regular file: {path}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Profile path is not a regular file: {path}')
    previous = path.read_bytes() if path.exists() else b''
    lines = previous.splitlines()
    start, end = BLOCK_START.encode(), BLOCK_END.encode()
    if start in lines or end in lines:
        if lines.count(start) != 1 or lines.count(end) != 1:
            raise ValueError(f'Duplicate/incomplete managed PATH block; review this file first: {path}')
        first, last = lines.index(start), lines.index(end)
        if last < first or b'\n'.join(lines[first:last + 1]) != PATH_BLOCK.rstrip().encode():
            raise ValueError(f'Managed PATH block was modified; review this file first: {path}')
        return previous, False
    return previous, True


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if sys.platform != 'linux':
        print('Run this setup inside Linux/WSL2; use setup-ttpselecter.cmd on Windows.', file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent.parent
    home = Path.home().resolve()
    launcher = root / 'start-ttpselecter.sh'
    command = home / '.local/bin/ttpselecter'
    zsh_home = Path(os.environ.get('ZDOTDIR') or str(home)).expanduser()
    if not zsh_home.is_absolute():
        print('ZDOTDIR must be an absolute path when configured.', file=sys.stderr)
        return 1
    profiles = [home / '.profile', home / '.bashrc', zsh_home / '.zprofile', zsh_home / '.zshrc']
    for name in ('.bash_profile', '.bash_login'):
        candidate = home / name
        if candidate.exists() or candidate.is_symlink():
            profiles.append(candidate)
            break  # Bash reads only the first existing login profile.
    profiles = list(dict.fromkeys(profiles))
    token = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    temporary = command.with_name('.ttpselecter-' + token + '.tmp')
    print(f'Input project: {root}', flush=True)
    print(f'Input launcher: {launcher}', flush=True)
    print(f'Output command: {command}', flush=True)
    print(f'Output temporary command: {temporary}', flush=True)
    for path in profiles:
        print(f'Input/output shell profile: {path}', flush=True)
    try:
        print('[Linux command setup 1/4] Checking the installed Linux application', flush=True)
        if not home.is_dir() or not launcher.is_file() or not (root / 'main.py').is_file():
            raise ValueError('Extract the complete project and finish Linux Installation before setup.')
        subprocess.run(['bash', str(launcher), '--check'], check=True)

        print('[Linux command setup 2/4] Checking command ownership and planning profile updates', flush=True)
        if command.is_symlink() or (command.exists() and (
                not command.is_file() or COMMAND_MARKER.encode() not in command.read_bytes().splitlines())):
            raise ValueError(f'Existing command is not managed by this project; nothing was replaced: {command}')
        other = shutil.which('ttpselecter')
        if other and Path(other).resolve() != command.resolve():
            raise ValueError(f'Another ttpselecter command is already on PATH: {other}')
        plans = []
        for path in profiles:
            previous, update = profile_plan(path)
            backup = path.with_name(path.name + '.ttpselecter-backup-' + token) if path.exists() and update else None
            if backup:
                print(f'Output profile backup: {backup}', flush=True)
            if update:
                ancestor = path if path.exists() else path.parent
                while not ancestor.exists():
                    ancestor = ancestor.parent
                if not os.access(ancestor, os.W_OK):
                    raise PermissionError(f'Profile location is not writable: {path}')
            plans.append((path, previous, update, backup))

        print('[Linux command setup 3/4] Installing the user command and backed-up PATH blocks', flush=True)
        wrapper = ('#!/usr/bin/env bash\n' + COMMAND_MARKER + '\nexec bash ' +
                   shlex.quote(str(launcher)) + ' "$@"\n').encode('utf-8')
        command.parent.mkdir(parents=True, exist_ok=True)
        if not command.exists() or command.read_bytes() != wrapper:
            created = False
            try:
                with temporary.open('xb') as output:
                    created = True
                    output.write(wrapper)
                temporary.chmod(0o755)
                temporary.replace(command)
            finally:
                if created and temporary.exists():
                    temporary.unlink()
        else:
            command.chmod(command.stat().st_mode | 0o100)
        for index, (path, previous, update, backup) in enumerate(plans, 1):
            print(f'[Profiles {index}/{len(plans)}] {"Update" if update else "Already configured"}: {path}', flush=True)
            if not update:
                continue
            if path.exists() and path.read_bytes() != previous:
                raise RuntimeError(f'Profile changed during setup; retained without editing: {path}')
            path.parent.mkdir(parents=True, exist_ok=True)
            if backup:
                shutil.copy2(path, backup)
            suffix = (b'\n' if previous and not previous.endswith(b'\n') else b'') + b'\n' + PATH_BLOCK.encode()
            with path.open('ab') as output:
                output.write(suffix)

        print('[Linux command setup 4/4] Verifying command forwarding and persistent PATH blocks', flush=True)
        for path in profiles:
            _, update = profile_plan(path)
            if update:
                raise RuntimeError(f'PATH block verification failed: {path}')
        subprocess.run([str(command), '--check'], check=True)
        print('Setup complete. Close and reopen your Bash/Zsh terminal, then run ttpselecter from any directory.', flush=True)
        print('For this terminal now: export PATH="$HOME/.local/bin:$PATH"', flush=True)
        print('The command uses this project folder. After moving the project, rerun setup from its new location.', flush=True)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Linux command setup failed: {error}', file=sys.stderr, flush=True)
        print('Preflight failures do not replace the command or profiles. For a write/verification failure, review completed steps and the listed backups.', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
