"""Exercise Linux command setup in isolated homes. Workflow: scripts/README.md."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import uuid

from install_linux_command import BLOCK_START, BLOCK_END


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui-smoke', action='store_true', help='Also open the real application via WSLg/xcb')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Run inside Linux with the project virtual environment.')
    root = Path(__file__).resolve().parent.parent
    output = root / 'artifacts/linux-command-setup' / uuid.uuid4().hex
    print(f'Input installer: {root / "setup-ttpselecter.sh"}', flush=True)
    print(f'Input Linux environment: {sys.executable}', flush=True)
    print(f'Output fixture homes/logs/report: {output}', flush=True)
    print(f'Output report: {output / "audit.json"}', flush=True)
    output.mkdir(parents=True)
    checks = []
    results = []

    def check(value, label):
        if not value:
            raise AssertionError(label)
        checks.append(label)

    def environment(home):
        home.mkdir(parents=True, exist_ok=True)
        return {**os.environ, 'HOME': str(home), 'ZDOTDIR': str(home / 'zsh-config'),
                'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1', 'QT_QPA_PLATFORM': 'xcb'}

    def run(name, command, env, expected=0):
        log = output / (name + '.log')
        print(f'Output command log: {log}', flush=True)
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd='/tmp', env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=90)
        results.append({'case': name, 'exit_code': result.returncode, 'log': str(log)})
        check(result.returncode == expected, name + ': expected exit code')
        return log.read_text(encoding='utf-8', errors='replace')

    print('[Command audit 1/6] First install and backed-up shell profiles', flush=True)
    home = output / "home with spaces 測試 'quote"
    env = environment(home)
    originals = {}
    for path in (home / '.profile', home / '.bashrc', home / '.bash_profile',
                 home / 'zsh-config/.zprofile', home / 'zsh-config/.zshrc'):
        path.parent.mkdir(parents=True, exist_ok=True)
        original = b'# Existing user content\nexport TTP_SETUP_SENTINEL=retained\n'
        path.write_bytes(original)
        originals[path] = original
    run('first-install', ['bash', str(root / 'setup-ttpselecter.sh')], env)
    command = home / '.local/bin/ttpselecter'
    check(command.is_file() and os.access(command, os.X_OK), 'user command is executable')
    for path, original in originals.items():
        check(path.read_bytes().startswith(original), str(path.name) + ': existing bytes preserved')
        backups = list(path.parent.glob(path.name + '.ttpselecter-backup-*'))
        check(len(backups) == 1 and backups[0].read_bytes() == original, str(path.name) + ': exact original backup')
        check(path.read_bytes().splitlines().count(BLOCK_START.encode()) == 1, str(path.name) + ': single PATH block')

    print('[Command audit 2/6] Bash interactive/login and Zsh startup from /tmp', flush=True)
    shell_code = 'cd /tmp; command -v ttpselecter; ttpselecter --check'
    for name, shell in (
        ('bash-interactive', ['bash', '--noprofile', '--rcfile', str(home / '.bashrc'), '-ic']),
        ('bash-login', ['bash', '-lc']),
        ('zsh-interactive', ['zsh', '-ic']),
        ('zsh-login', ['zsh', '-lic']),
    ):
        if name.startswith('zsh') and not shutil.which('zsh'):
            results.append({'case': name, 'status': 'NOT_RUN', 'reason': 'zsh not installed'})
            continue
        text = run(name, [*shell, shell_code], env)
        check(str(command) in text and '[Linux launch 3/3] Ready' in text,
              name + ': command resolves and reaches the real dependency check')
        check('Traceback (most recent call last)' not in text, name + ': no traceback')

    print('[Command audit 3/6] Repeated setup adds no blocks or backups', flush=True)
    before = {path: path.read_bytes() for path in [command, *originals]}
    backups = sorted(str(path) for path in home.rglob('*.ttpselecter-backup-*'))
    run('repeat-install', ['bash', str(root / 'setup-ttpselecter.sh')], env)
    check(all(path.read_bytes() == value for path, value in before.items()), 'repeat setup preserves installed contents')
    check(sorted(str(path) for path in home.rglob('*.ttpselecter-backup-*')) == backups,
          'repeat setup creates no extra backups')

    print('[Command audit 4/6] Refuse unrelated commands and edited managed blocks', flush=True)
    conflict_home = output / 'unrelated-command-home'
    conflict_env = environment(conflict_home)
    conflict = conflict_home / '.local/bin/ttpselecter'
    conflict.parent.mkdir(parents=True)
    conflict.write_bytes(b'#!/bin/sh\necho unrelated\n')
    run('unmanaged-command', ['bash', str(root / 'setup-ttpselecter.sh')], conflict_env, 1)
    check(conflict.read_bytes() == b'#!/bin/sh\necho unrelated\n' and not (conflict_home / '.profile').exists(),
          'unrelated command and absent profiles preserved on preflight failure')
    edited_home = output / 'edited-profile-home'
    edited_env = environment(edited_home)
    edited = edited_home / '.bashrc'
    content = (BLOCK_START + '\n# user changed the managed block\n' + BLOCK_END + '\n').encode()
    edited.write_bytes(content)
    run('edited-managed-block', ['bash', str(root / 'setup-ttpselecter.sh')], edited_env, 1)
    check(edited.read_bytes() == content and not (edited_home / '.local/bin/ttpselecter').exists(),
          'edited PATH block is retained without installing a command')

    print('[Command audit 5/6] Quoted project paths and missing environment', flush=True)
    project = output / "project with spaces 測試 'quote"
    (project / 'scripts').mkdir(parents=True)
    for name in ('setup-ttpselecter.sh', 'start-ttpselecter.sh'):
        shutil.copyfile(root / name, project / name)
    shutil.copyfile(root / 'scripts/install_linux_command.py', project / 'scripts/install_linux_command.py')
    (project / 'main.py').write_text('# Path-quoting fixture; only --check is used.\n')
    (project / 'README.md').write_text('Generated command-installer path-quoting fixture. No application window is launched here.\n')
    missing_env = environment(output / 'missing-environment-home')
    run('missing-environment', ['bash', str(project / 'setup-ttpselecter.sh')], missing_env, 1)
    check(not (Path(missing_env['HOME']) / '.local').exists(), 'missing environment fails before user command/profile writes')
    (project / '.venv').symlink_to(root / '.venv', target_is_directory=True)
    quoted_env = environment(output / 'quoted-project-home')
    run('quoted-project-install', ['bash', str(project / 'setup-ttpselecter.sh')], quoted_env)
    run('quoted-project-command', [str(Path(quoted_env['HOME']) / '.local/bin/ttpselecter'), '--check'], quoted_env)
    check(True, 'project paths with spaces, Unicode and apostrophes are forwarded correctly')

    print('[Command audit 6/6] Optional real GUI launch and report', flush=True)
    if args.gui_smoke:
        screenshot = output / 'gui-smoke.png'
        print(f'Output GUI screenshot: {screenshot}', flush=True)
        text = run('gui-smoke', ['bash', '-lc', 'cd /tmp; ttpselecter --smoke-test --no-session --screenshot ' +
                                  shlex.quote(str(screenshot))], env)
        check('[Verification] PASS' in text and screenshot.is_file(), 'real WSLg GUI smoke via the registered bare command')
    payload = {'status': 'PASS', 'checks': checks, 'count': len(checks), 'results': results,
               'gui_smoke': args.gui_smoke, 'isolated_home': str(home), 'project': str(root)}
    (output / 'audit.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[Command audit] PASS: {len(checks)} checks; {output / "audit.json"}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
