"""Fetch a pinned, reviewable ATLAS snapshot. Workflow: scripts/README.md."""
from hashlib import sha256
import json
from pathlib import Path
from urllib.request import urlopen

COMMIT = '3259f388d19cbcca11bacf12a0ef97f4198f711b'
BASE = f'https://raw.githubusercontent.com/mitre-atlas/atlas-data/{COMMIT}/'
ROOT = Path(__file__).resolve().parent.parent / 'data' / 'atlas'
FILES = {'ATLAS-2026.09.yaml': 'dist/v6/ATLAS-2026.09.yaml', 'LICENSE': 'LICENSE'}


def main():
    for name, relative in FILES.items():
        print(f'Input URL: {BASE + relative}', flush=True)
        print(f'Output file: {(ROOT / name).resolve()}', flush=True)
    print(f'Output manifest: {(ROOT / "source.json").resolve()}', flush=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    entries = {}
    for index, (name, relative) in enumerate(FILES.items(), 1):
        print(f'[ATLAS download {index}/3] Fetching {name}', flush=True)
        with urlopen(BASE + relative, timeout=30) as stream:
            data = stream.read(16 * 1024 * 1024 + 1)
        if len(data) > 16 * 1024 * 1024:
            raise ValueError('ATLAS source exceeds 16 MiB.')
        temporary = ROOT / (name + '.tmp')
        print(f'Output temporary file: {temporary.resolve()}', flush=True)
        temporary.write_bytes(data)
        temporary.replace(ROOT / name)
        entries[name] = {'url': BASE + relative, 'sha256': sha256(data).hexdigest()}
    (ROOT / 'source.json').write_text(json.dumps({'commit': COMMIT, 'release': '2026.09',
        'format_version': '6.0.0', 'files': entries}, indent=2) + '\n', encoding='utf-8')
    print('[ATLAS download 3/3] Complete; pinned source and license saved', flush=True)


if __name__ == '__main__':
    main()
