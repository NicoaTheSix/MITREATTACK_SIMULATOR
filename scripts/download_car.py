"""Fetch one fixed CAR source archive without running upstream code. Workflow: scripts/README.md."""
from hashlib import sha256
import io
import json
from pathlib import Path
import urllib.request
import zipfile

COMMIT = '1b922fe1527d956e222a99473472e594f10f610b'
ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / 'data/car'
URL = 'https://codeload.github.com/mitre-attack/car/zip/' + COMMIT


def main():
    print('Input URL: ' + URL, flush=True)
    print('Output manifest: ' + str((TARGET / 'source.json').resolve()), flush=True)
    print('Output source root: ' + str(TARGET.resolve()), flush=True)
    print('[CAR download 1/3] Reading fixed archive (64 MiB maximum)', flush=True)
    with urllib.request.urlopen(URL, timeout=60) as response:
        data = response.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024:
        raise ValueError('CAR archive exceeds size limit.')
    archive = zipfile.ZipFile(io.BytesIO(data))
    selected = []
    for item in archive.infolist():
        relative = '/'.join(item.filename.split('/')[1:])
        path = Path(relative)
        if item.is_dir() or path.is_absolute() or '..' in path.parts:
            continue
        if ((path.parts[0] in ('analytics', 'data_model', 'sensors') and path.suffix == '.yaml')
                or (path.parts[0] == 'scripts' and path.suffix in ('.py', '.yaml'))
                or relative in ('LICENSE.txt', 'NOTICE.txt', 'README.md', 'CONTRIBUTING.md')
                or relative.startswith('docs/analytics/by_technique')):
            destination = (TARGET / path).resolve()
            if not destination.is_relative_to(TARGET.resolve()) or item.file_size > 4 * 1024 * 1024:
                raise ValueError('Invalid CAR archive member.')
            selected.append((item, relative, destination))
    for _, _, path in selected:
        print('Output file: ' + str(path), flush=True)
    print('[CAR download 2/3] Writing original files and hashing each member', flush=True)
    manifest = {'schema': 1, 'repository': 'https://github.com/mitre-attack/car', 'commit': COMMIT,
                'archive_url': URL, 'archive_sha256': sha256(data).hexdigest(), 'files': {}}
    for index, (item, relative, destination) in enumerate(selected, 1):
        payload = archive.read(item)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        manifest['files'][relative] = sha256(payload).hexdigest()
        if index % 20 == 0:
            print(f'[CAR download 2/3] {index}/{len(selected)}', flush=True)
    for folder, count in [('analytics', 102), ('data_model', 13), ('sensors', 7)]:
        if sum(p.startswith(folder + '/') and p.endswith('.yaml') for p in manifest['files']) != count:
            raise ValueError('Unexpected fixed CAR file count: ' + folder)
    TARGET.mkdir(parents=True, exist_ok=True)
    (TARGET / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('[CAR download 3/3] Complete; fixed manifest published', flush=True)


if __name__ == '__main__':
    main()
