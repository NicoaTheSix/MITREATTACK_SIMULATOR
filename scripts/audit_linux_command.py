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

from install_linux_command import BLOCK_START, BLOCK_END, PATH_BLOCK, LEGACY_COMMAND_MARKER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui-smoke', action='store_true', help='Also open the real application via WSLg/xcb')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Run inside Linux with the project virtual environment.')
    root = Path(__file__).resolve().parent.parent
    output = root / 'artifacts/linux-command-setup' / uuid.uuid4().hex
    print(f'Input installer: {root / "setup-fusionstudio.sh"}', flush=True)
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
                'PATH': '/usr/bin:/bin', 'FUSIONSTUDIO_PYTHON': sys.executable, 'PYTHONDONTWRITEBYTECODE': '1', 'QT_QPA_PLATFORM': 'xcb'}

    def run(name, command, env, expected=0):
        log = output / (name + '.log')
        print(f'Output command log: {log}', flush=True)
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd='/tmp', env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=90)
        results.append({'case': name, 'exit_code': result.returncode, 'log': str(log)})
        check(result.returncode == expected, name + ': expected exit code')
        return log.read_text(encoding='utf-8', errors='replace')

    print('[Command audit 1/7] First install and backed-up shell profiles', flush=True)
    home = output / "home with spaces 測試 'quote"
    env = environment(home)
    originals = {}
    for path in (home / '.profile', home / '.bashrc', home / '.bash_profile',
                 home / 'zsh-config/.zprofile', home / 'zsh-config/.zshrc'):
        path.parent.mkdir(parents=True, exist_ok=True)
        original = b'# Existing user content\nexport TTP_SETUP_SENTINEL=retained\n'
        path.write_bytes(original)
        originals[path] = original
    run('first-install', ['bash', str(root / 'setup-fusionstudio.sh')], env)
    command = home / '.local/bin/fusionstudio'
    check(command.is_file() and os.access(command, os.X_OK), 'user command is executable')
    for path, original in originals.items():
        check(path.read_bytes().startswith(original), str(path.name) + ': existing bytes preserved')
        backups = list(path.parent.glob(path.name + '.fusionstudio-backup-*'))
        check(len(backups) == 1 and backups[0].read_bytes() == original, str(path.name) + ': exact original backup')
        check(path.read_bytes().splitlines().count(BLOCK_START.encode()) == 1, str(path.name) + ': single PATH block')

    print('[Command audit 2/7] Bash interactive/login and Zsh startup from /tmp', flush=True)
    shell_code = 'cd /tmp; command -v fusionstudio; fusionstudio --check'
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

    print('[Command audit 3/7] Repeated setup adds no blocks or backups', flush=True)
    before = {path: path.read_bytes() for path in [command, *originals]}
    backups = sorted(str(path) for path in home.rglob('*.fusionstudio-backup-*'))
    run('repeat-install', ['bash', str(root / 'setup-fusionstudio.sh')], env)
    check(all(path.read_bytes() == value for path, value in before.items()), 'repeat setup preserves installed contents')
    check(sorted(str(path) for path in home.rglob('*.fusionstudio-backup-*')) == backups,
          'repeat setup creates no extra backups')

    print('[Command audit 4/7] Refuse unrelated commands and edited managed blocks', flush=True)
    conflict_home = output / 'unrelated-command-home'
    conflict_env = environment(conflict_home)
    conflict = conflict_home / '.local/bin/fusionstudio'
    conflict.parent.mkdir(parents=True)
    conflict.write_bytes(b'#!/bin/sh\necho unrelated\n')
    run('unmanaged-command', ['bash', str(root / 'setup-fusionstudio.sh')], conflict_env, 1)
    check(conflict.read_bytes() == b'#!/bin/sh\necho unrelated\n' and not (conflict_home / '.profile').exists(),
          'unrelated command and absent profiles preserved on preflight failure')
    edited_home = output / 'edited-profile-home'
    edited_env = environment(edited_home)
    edited = edited_home / '.bashrc'
    content = (BLOCK_START + '\n# user changed the managed block\n' + BLOCK_END + '\n').encode()
    edited.write_bytes(content)
    run('edited-managed-block', ['bash', str(root / 'setup-fusionstudio.sh')], edited_env, 1)
    check(edited.read_bytes() == content and not (edited_home / '.local/bin/fusionstudio').exists(),
          'edited PATH block is retained without installing a command')

    print('[Command audit 5/7] Quoted project paths and missing environment', flush=True)
    project = output / "project with spaces 測試 'quote"
    (project / 'scripts').mkdir(parents=True)
    for name in ('setup-fusionstudio.sh', 'start-fusionstudio.sh'):
        shutil.copyfile(root / name, project / name)
    shutil.copyfile(root / 'scripts/install_linux_command.py', project / 'scripts/install_linux_command.py')
    (project / 'main.py').write_text('import json, os, sys\nprint(json.dumps({\"cwd\": os.getcwd(), \"args\": sys.argv[1:]}))\n')
    (project / 'README.md').write_text('Generated command-installer path-quoting fixture. No application window is launched here.\n')
    missing_env = environment(output / 'missing-environment-home')
    missing_env.pop('FUSIONSTUDIO_PYTHON', None)
    run('missing-environment', ['bash', str(project / 'setup-fusionstudio.sh')], missing_env, 1)
    check(not (Path(missing_env['HOME']) / '.local').exists(), 'missing environment fails before user command/profile writes')
    (project / '.venv').symlink_to(Path(sys.executable).parent.parent, target_is_directory=True)
    quoted_env = environment(output / 'quoted-project-home')
    quoted_env.pop('FUSIONSTUDIO_PYTHON', None)
    run('quoted-project-install', ['bash', str(project / 'setup-fusionstudio.sh')], quoted_env)
    run('quoted-project-command', [str(Path(quoted_env['HOME']) / '.local/bin/fusionstudio'), '--check'], quoted_env)
    check(True, 'project paths with spaces, Unicode and apostrophes are forwarded correctly')
    (project / '.venv').rename(project / '.venv-linux')
    run('fallback-environment', [str(Path(quoted_env['HOME']) / '.local/bin/fusionstudio'), '-Check'], quoted_env)
    check(True, 'shared checkout uses .venv-linux and accepts -Check')
    text = run('argument-forwarding', [str(Path(quoted_env['HOME']) / '.local/bin/fusionstudio'),
                                      '--example', 'two words'], quoted_env)
    forwarded = json.loads(text.splitlines()[-1])
    check(forwarded == {'cwd': str(project), 'args': ['--example', 'two words']},
          'launcher forwards arguments and starts in the project directory')

    print('[Command audit 6/7] Migrate intact legacy wrappers and preserve unrelated entries', flush=True)
    migration_home = output / 'legacy-migration-home'
    migration_env = environment(migration_home)
    legacy = migration_home / '.local/bin/ttpselecter'
    legacy.parent.mkdir(parents=True)
    old_target = migration_home / "previous project 'quoted/start-ttpselecter.sh"
    legacy_content = ('#!/usr/bin/env bash\n' + LEGACY_COMMAND_MARKER + '\nexec bash ' +
                      shlex.quote(str(old_target)) + ' "$@"\n').encode()
    legacy.write_bytes(legacy_content)
    legacy.chmod(0o755)
    legacy_profiles = {}
    for path in (migration_home / '.profile', migration_home / '.bashrc',
                 migration_home / 'zsh-config/.zprofile', migration_home / 'zsh-config/.zshrc'):
        path.parent.mkdir(parents=True, exist_ok=True)
        content = b'# Existing user profile\n' + PATH_BLOCK.encode()
        path.write_bytes(content)
        legacy_profiles[path] = content
    text = run('legacy-migration', ['bash', str(root / 'setup-fusionstudio.sh')], migration_env)
    check(not legacy.exists() and (legacy.parent / 'fusionstudio').is_file(), 'intact old wrapper replaced by new command')
    check('Removed former managed command:' in text, 'migration reports old command removal')
    check(all(path.read_bytes() == content for path, content in legacy_profiles.items()),
          'legacy PATH blocks and all profile bytes reused unchanged')
    check(not list(migration_home.rglob('*.fusionstudio-backup-*')), 'migration needs no profile backups when blocks exist')
    run('migration-repeat', ['bash', str(root / 'setup-fusionstudio.sh')], migration_env)
    check(not legacy.exists(), 'repeated migration does not recreate old command')
    text = run('migration-shell', ['bash', '--noprofile', '--rcfile', str(migration_home / '.bashrc'),
                                 '-ic', 'hash -r; ! command -v ttpselecter && fusionstudio --check'], migration_env)
    check('[Linux launch 3/3] Ready' in text, 'fresh shell resolves only the new managed entry')

    for name, content in (
        ('unrelated-legacy', b'#!/bin/sh\necho unrelated\n'),
        ('edited-legacy', legacy_content + b'# user added content\n'),
    ):
        legacy_home = output / (name + '-home')
        legacy_env = environment(legacy_home)
        old = legacy_home / '.local/bin/ttpselecter'
        old.parent.mkdir(parents=True)
        old.write_bytes(content)
        expected = 1 if name == 'edited-legacy' else 0
        run(name, ['bash', str(root / 'setup-fusionstudio.sh')], legacy_env, expected)
        check(old.read_bytes() == content, name + ': old entry preserved')
        check((old.parent / 'fusionstudio').exists() == (expected == 0),
              name + ': correct preflight/install outcome')

    symlink_home = output / 'symlink-legacy-home'
    symlink_env = environment(symlink_home)
    old_link = symlink_home / '.local/bin/ttpselecter'
    old_link.parent.mkdir(parents=True)
    old_link.symlink_to(symlink_home / 'absent-target')
    run('legacy-symlink', ['bash', str(root / 'setup-fusionstudio.sh')], symlink_env)
    check(old_link.is_symlink(), 'legacy symlink is retained without following or removing it')

    # Failures before verification must keep the intact old entry usable.
    blocked_home = output / 'blocked-migration-home'
    blocked_env = environment(blocked_home)
    blocked_old = blocked_home / '.local/bin/ttpselecter'
    blocked_old.parent.mkdir(parents=True)
    blocked_old.write_bytes(legacy_content)
    (blocked_old.parent / 'fusionstudio').write_bytes(b'#!/bin/sh\necho unrelated\n')
    run('blocked-migration', ['bash', str(root / 'setup-fusionstudio.sh')], blocked_env, 1)
    check(blocked_old.read_bytes() == legacy_content and not (blocked_home / '.profile').exists(),
          'conflicting new command leaves intact legacy entry and profiles unchanged')

    failed_home = output / 'verification-failure-home'
    failed_env = environment(failed_home)
    failed_old = failed_home / '.local/bin/ttpselecter'
    failed_old.parent.mkdir(parents=True)
    failed_old.write_bytes(legacy_content)
    # Inject failure only on the second dependency check, after the new wrapper exists.
    shim = failed_home / 'python-check-fixture'
    counter = failed_home / 'check-count'
    shim.write_text('#!/usr/bin/env bash\n'
                    f'counter={shlex.quote(str(counter))}\n'
                    'if test -e "$counter"; then exit 7; fi\n'
                    'printf "1\\n" > "$counter"\n', encoding='utf-8')
    shim.chmod(0o755)
    failed_env['FUSIONSTUDIO_PYTHON'] = str(shim)
    text = run('verification-failure', ['bash', str(root / 'setup-fusionstudio.sh')], failed_env, 1)
    check('[Linux command setup 4/4]' in text, 'injected failure occurs during installed-command verification')
    check(failed_old.read_bytes() == legacy_content, 'failed new-command verification retains intact former wrapper')

    path_home = output / 'path-conflict-home'
    path_env = environment(path_home)
    other_directory = path_home / 'other-bin'
    other_directory.mkdir()
    other = other_directory / 'fusionstudio'
    other.write_bytes(b'#!/bin/sh\necho unrelated\n')
    other.chmod(0o755)
    path_env['PATH'] = str(other_directory) + ':' + path_env['PATH']
    run('path-conflict', ['bash', str(root / 'setup-fusionstudio.sh')], path_env, 1)
    check(not (path_home / '.local').exists() and other.read_bytes() == b'#!/bin/sh\necho unrelated\n',
          'conflicting command elsewhere on PATH prevents user command/profile writes')

    print('[Command audit 7/7] Optional real GUI launch and report', flush=True)
    if args.gui_smoke:
        screenshot = output / 'gui-smoke.png'
        print(f'Output GUI screenshot: {screenshot}', flush=True)
        text = run('gui-smoke', ['bash', '-lc', 'cd /tmp; fusionstudio --smoke-test --no-session --screenshot ' +
                                  shlex.quote(str(screenshot))], env)
        check('[Verification] PASS' in text and screenshot.is_file(), 'real WSLg GUI smoke via the registered bare command')
    payload = {'status': 'PASS', 'checks': checks, 'count': len(checks), 'results': results,
               'gui_smoke': args.gui_smoke, 'isolated_home': str(home), 'project': str(root)}
    (output / 'audit.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[Command audit] PASS: {len(checks)} checks; {output / "audit.json"}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
