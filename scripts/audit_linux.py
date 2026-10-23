"""Run the existing feature audits under Linux Qt. Workflow: scripts/README.md."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time

AUDITS = {name: [] for name in (
    'audit_catalog.py', 'audit_documents.py', 'audit_comments.py', 'audit_domains.py',
    'audit_workspace.py', 'audit_matrix.py', 'audit_matrix_actions.py', 'audit_layers.py',
    'audit_clear_colors.py', 'audit_overlay.py', 'audit_navigator.py',
    'audit_navigator_bundle.py', 'audit_custom_domains.py', 'audit_custom_data_url.py',
    'audit_related_ttps.py', 'audit_batch_operations.py', 'audit_advanced_navigator.py',
    'audit_layer_analysis.py', 'audit_formula_features.py', 'audit_export_options.py', 'audit_svg_themes.py', 'audit_svg_paper.py',
    'audit_formula_compatibility.py', 'audit_formula_scope.py',
    'audit_formula_gradient.py', 'audit_upgrade_review.py', 'audit_upgrade_content.py', 'audit_upgrade_mapping.py', 'audit_upgrade_summary.py',
    'audit_json_annotation_export.py', 'audit_matrix_display.py', 'audit_selection_search.py',
    'audit_source_selection.py', 'audit_source_preview.py', 'audit_studio_lifecycle.py',
    'audit_visibility_presets.py', 'audit_detection_interaction.py', 'audit_navigator_parity.py',
    'audit_manual_language.py', 'audit_car_integration.py', 'audit_workspace_layout.py', 'audit_code_blocks.py', 'audit_matrix_controls.py', 'audit_sidebar_visibility.py', 'audit_mitigation_navigation.py', 'audit_library_navigation.py', 'audit_car_tabs.py',
)}
AUDITS['audit_versions.py'] = ['--picker-only']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=('offscreen', 'xcb', 'wayland'), default='offscreen')
    parser.add_argument('--only', nargs='+', choices=tuple(AUDITS))
    parser.add_argument('--output-dir', type=Path, help='Separate report/log directory for a recheck')
    parser.add_argument('--timeout', type=int, default=240, help='Timeout in seconds per audit')
    args = parser.parse_args()
    if sys.platform != 'linux':
        parser.error('Run this script with native Linux Python, for example inside WSL2.')
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    root = Path(__file__).resolve().parent.parent
    output = (args.output_dir.expanduser().resolve() if args.output_dir else
              root / 'artifacts' / 'linux-wsl' / args.platform)
    selected = args.only or list(AUDITS)
    report = output / 'audit.json'
    print(f'Input project: {root}', flush=True)
    print(f'Input Python: {sys.executable}', flush=True)
    print(f'Input dataset pointer: {root / "data/attack/active.json"}', flush=True)
    print(f'Output report: {report}', flush=True)
    print(f'Output feature artifacts: {root / "artifacts"}', flush=True)
    for name in selected:
        print(f'Input audit: {root / name}', flush=True)
        print(f'Output audit log: {output / (name + ".log")}', flush=True)
    output.mkdir(parents=True, exist_ok=True)
    pointers = {path: sha256(path.read_bytes()).hexdigest() for path in
                (root / 'data/attack/active.json', root / 'data/attack/latest.json') if path.exists()}
    payload = {
        'status': 'RUNNING', 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'system': platform.platform(), 'python': sys.version, 'executable': sys.executable,
        'qt_platform': args.platform, 'project': str(root),
        'packages': {name: version(name) for name in ('PySide6', 'mitreattack-python', 'openpyxl')},
        'results': [],
    }
    environment = {**os.environ, 'QT_QPA_PLATFORM': args.platform,
                   'PYTHONUNBUFFERED': '1', 'PYTHONUTF8': '1'}
    for index, name in enumerate(selected, 1):
        print(f'[Linux audit {index}/{len(selected)}] Running {name} ({args.platform})', flush=True)
        started = time.monotonic()
        log_path = output / (name + '.log')
        timed_out = False
        with log_path.open('w', encoding='utf-8') as log:
            child = subprocess.Popen([sys.executable, '-B', str(root / name), *AUDITS[name]],
                                     cwd=root, env=environment, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try:
                child.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
        text = log_path.read_text(encoding='utf-8', errors='replace')
        result = {'audit': name, 'exit_code': child.returncode, 'timed_out': timed_out,
                  'seconds': round(time.monotonic() - started, 2), 'log': str(log_path),
                  'status': 'PASS' if child.returncode == 0 and not timed_out and
                  'Traceback (most recent call last)' not in text else 'FAIL'}
        payload['results'].append(result)
        report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'[Linux audit {index}/{len(selected)}] {result["status"]}: {name} ({result["seconds"]}s)', flush=True)
        if result['status'] == 'FAIL':
            print(text[-1800:], flush=True)
    payload['official_pointers_unchanged'] = all(
        path.exists() and sha256(path.read_bytes()).hexdigest() == digest for path, digest in pointers.items())
    payload['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
    payload['status'] = ('PASS' if payload['official_pointers_unchanged'] and
                         all(item['status'] == 'PASS' for item in payload['results']) else 'FAIL')
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'[Linux audit complete] {payload["status"]}: '
          f'{sum(item["status"] == "PASS" for item in payload["results"])}/{len(selected)}; {report}', flush=True)
    return 0 if payload['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
