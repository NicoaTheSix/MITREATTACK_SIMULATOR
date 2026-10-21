# Linux Command Setup Evidence

Verified on 2026-10-20 in Kali WSL2 with native Linux Python. `audit.json` records **43 passing assertions**, including a real WSLg/xcb GUI smoke test launched by the bare `ttpselecter` command from `/tmp`.

The source test is `scripts/audit_linux_command.py`; operation flow and reproduction commands are in [scripts/README.md](../../scripts/README.md#linux-command-setup). It creates isolated HOME directories under the native Linux test project, preserves fixture profile prefixes, checks exact backups, exercises Bash/Zsh interactive and login startup, verifies repeat setup, rejects unmanaged commands/edited blocks, tests missing dependencies and quoted paths, and launches the actual GUI with recovery disabled. It prints absolute inputs/outputs and six-stage progress; the JSON is published only after assertions pass.

`logs/` contains each isolated case transcript. Exit code 1 is expected for the `unmanaged-command`, `edited-managed-block` and `missing-environment` cases; their rejection is a passing assertion. `gui-smoke.png` is the real native GUI preview. Original absolute fixture/log paths in the JSON refer to the WSL workspace; exported logs are alongside this README under `logs/`.

`current-user-install.log`, `current-user-bash.log` and `current-user-zsh.log` separately record installation in the real Kali account and fresh-shell command checks. Existing profiles received timestamped backups before appending PATH blocks. Personal profiles/backups and generated HOME contents are not exported here. The real command points to `/home/kali/.local/share/ttp-selection-studio-wsl-test/project/start-ttpselecter.sh`.

This result covers Bash and Zsh on the tested distribution. Fish and other shell startup formats remain unconfigured. Application feature verification remains separately documented in [the Linux/WSL2 report](../../LINUX_WSL2_TEST_REPORT.md).
