"""Cache official ATT&CK release introductions. Workflow: scripts/README.md."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://attack.mitre.org/resources/versions/'
TARGET = ROOT / 'data' / 'info' / 'attack-release-notes.json'


def report(message):
    print(message, flush=True)


def fetch(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'attack.mitre.org':
        raise ValueError('Expected an official HTTPS ATT&CK URL')
    with urlopen(Request(url, headers={'User-Agent': 'Fusion-Studio-info'}), timeout=30) as response:
        final = urlparse(response.geturl())
        if final.scheme != 'https' or final.netloc != 'attack.mitre.org':
            raise ValueError('Unexpected redirect outside the official site')
        content = response.read(8 * 1024 * 1024 + 1)
    if len(content) > 8 * 1024 * 1024:
        raise ValueError('Official page exceeds the size limit')
    return content.decode('utf-8')


class OfficialPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.version = None
        self.releases = []
        self.anchor = None
        self.heading = None
        self.started = False
        self.finished = False
        self.paragraph = None
        self.paragraphs = []
        self.all_paragraphs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.anchor = [dict(attrs).get('href', ''), []]
        if tag == 'h1':
            self.heading = []
        if tag == 'h2' and self.started:
            self.finished = True
        if tag == 'p' and self.started:
            self.paragraph = []

    def handle_data(self, value):
        match = re.search(r'ATT&CK v(\d+\.\d+)', value)
        if match:
            self.version = match.group(1)
        if self.anchor is not None:
            self.anchor[1].append(value)
        if self.heading is not None:
            self.heading.append(value)
        if self.paragraph is not None:
            self.paragraph.append(value)

    def handle_endtag(self, tag):
        if tag == 'a' and self.anchor is not None:
            href, parts = self.anchor
            if self.version and ' '.join(''.join(parts).split()) == 'Release Notes':
                self.releases.append((self.version, urljoin(SOURCE, href)))
            self.anchor = None
        if tag == 'h1' and self.heading is not None:
            self.started = ''.join(self.heading).strip().startswith('Updates')
            self.heading = None
        if tag == 'p' and self.paragraph is not None:
            text = ' '.join(''.join(self.paragraph).split())
            if text:
                self.all_paragraphs.append(text)
                if not self.finished:
                    self.paragraphs.append(text)
            self.paragraph = None


def release_entry(version, url):
    parser = OfficialPage()
    parser.feed(fetch(url))
    words = ' '.join(parser.paragraphs or parser.all_paragraphs).split()
    # Keep a short attributed introduction, with the full log available by link.
    if not words:
        raise ValueError(f'No release introduction found for v{version}: {url}')
    summary = ' '.join(words[:25]) + (' …' if len(words) > 25 else '')
    return {'version': version, 'url': url, 'summary': summary}


def main():
    temporary = TARGET.with_suffix('.json.part')
    report(f'Input URL: {SOURCE}')
    report('Input files: None (official HTTPS pages)')
    report(f'Output file: {TARGET}\nTemporary output file: {temporary}')
    report('[Info content 1/3] Reading official version history')
    parser = OfficialPage()
    parser.feed(fetch(SOURCE))
    releases = dict(parser.releases)
    if '20.0' not in releases or len(releases) < 15:
        raise ValueError('Incomplete official version-history page; previous cache retained')
    report(f'[Info content 2/3] Downloading {len(releases)} release introductions')
    entries = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {pool.submit(release_entry, version, url): version for version, url in releases.items()}
        for task in as_completed(tasks):
            entries.append(task.result())
            report(f'[Info content 2/3] v{tasks[task]} complete ({len(entries)}/{len(releases)})')
    entries.sort(key=lambda item: tuple(map(int, item['version'].split('.'))), reverse=True)
    payload = {'schema_version': 1, 'source_url': SOURCE,
               'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'releases': entries}
    report('[Info content 3/3] Publishing validated offline cache')
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(TARGET)
    finally:
        temporary.unlink(missing_ok=True)
    report('[Info content 3/3] Complete')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        report('[Info content] Cancelled; previous cache retained unless publication completed')
        raise SystemExit(130)
    except Exception as error:
        report(f'[Info content] Failed: {error}; previous cache retained')
        raise SystemExit(1)
