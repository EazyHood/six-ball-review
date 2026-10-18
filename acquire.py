"""Acquire the public official IPL JSON archive without extracting or executing it."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
import zipfile

ROOT = Path('D:/IA/datasets/cricsheet-ipl')
INDEX = 'https://cricsheet.org/downloads/'
MAX_BYTES = 50 * 1024 * 1024

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if urlparse(href).path.endswith('/ipl_json.zip') or href == 'ipl_json.zip':
                self.links.append(urljoin(INDEX, href))

def request(url):
    return Request(url, headers={'User-Agent': 'SixBallReview-Research/0.1 (+https://cricsheet.org/)'})

def main():
    target = ROOT / 'ipl-json-2026-10-18.zip'
    meta = ROOT / 'acquisition.json'
    if target.exists():
        if not meta.exists():
            raise RuntimeError('Archive exists without acquisition manifest; inspect before replacing.')
        expected = json.loads(meta.read_text(encoding='utf-8'))
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != expected['sha256']:
            raise RuntimeError('Existing archive checksum differs; no overwrite performed.')
        print(json.dumps({'status': 'reused_existing_verified_archive', 'bytes': target.stat().st_size, 'sha256': digest}))
        return
    with urlopen(request(INDEX), timeout=45) as response:
        html = response.read(2 * 1024 * 1024).decode('utf-8')
    parser = Links()
    parser.feed(html)
    links = sorted(set(parser.links))
    if len(links) != 1:
        raise RuntimeError(f'Expected one official IPL JSON link, found {links!r}')
    url = links[0]
    if urlparse(url).scheme != 'https' or urlparse(url).netloc != 'cricsheet.org':
        raise RuntimeError('Unexpected archive origin')
    (ROOT / 'downloads-index-2026-10-18.html').write_text(html, encoding='utf-8')
    temporary = target.with_suffix('.part')
    digest = hashlib.sha256()
    total = 0
    with urlopen(request(url), timeout=60) as response, temporary.open('xb') as destination:
        final_url = response.url
        content_type = response.headers.get('Content-Type')
        last_modified = response.headers.get('Last-Modified')
        etag = response.headers.get('ETag')
        if urlparse(final_url).scheme != 'https' or urlparse(final_url).netloc != 'cricsheet.org':
            raise RuntimeError('Unexpected download redirect')
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_BYTES:
                raise RuntimeError('Archive exceeds declared 50 MiB acquisition cap')
            digest.update(chunk)
            destination.write(chunk)
    if not zipfile.is_zipfile(temporary):
        raise RuntimeError('Response was not a ZIP; left .part for inspection')
    temporary.replace(target)
    record = {
        'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
        'index_url': INDEX, 'archive_url': url, 'final_url': final_url,
        'local_path': str(target), 'bytes': total, 'sha256': digest.hexdigest(),
        'content_type': content_type, 'last_modified': last_modified, 'etag': etag,
        'data_license': 'ODC-By-1.0', 'license_source': 'https://cricsheet.org/licensing/',
        'canonical_copy_only': True,
        'pre_download_check': 'Listed D:/IA/datasets and D:/IA/cache roots; bounded filename search datasets depth4/cache depth3 found no matching cricsheet/IPL archive. No exhaustive cache-content assertion.'
    }
    meta.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))

if __name__ == '__main__':
    main()
