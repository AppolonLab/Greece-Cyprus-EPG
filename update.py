#!/usr/bin/env python3
"""Download and validate EPGShare01 GR/CY feeds; rebuild only on content change."""
from pathlib import Path
from urllib.request import Request, urlopen
from hashlib import sha256
import gzip
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
SITE = ROOT / 'site'
SITE.mkdir(exist_ok=True)
FEEDS = {
    'GR': 'https://epgshare01.online/epgshare01/epg_ripper_GR1.xml.gz',
    'CY': 'https://epgshare01.online/epgshare01/epg_ripper_CY1.xml.gz',
}
TZ = ZoneInfo('Europe/Athens')
NOW = datetime.now(TZ)
END = NOW + timedelta(days=2)

def fetch(key, url):
    req = Request(url, headers={'User-Agent': 'EPG-Reader/1.0 (+personal XMLTV viewer)', 'Accept': 'application/gzip,application/octet-stream,*/*'})
    with urlopen(req, timeout=65) as response:
        payload = response.read(30_000_000 + 1)
    if len(payload) > 30_000_000:
        raise ValueError(f'{key}: archive exceeds 30 MB limit')
    if payload[:2] != b'\x1f\x8b':
        raise ValueError(f'{key}: response is not gzip')
    xml = gzip.decompress(payload)
    if len(xml) > 200_000_000:
        raise ValueError(f'{key}: XML decompressed size exceeds limit')
    # Parse the actual XML instead of checking its first bytes.
    # EPGShare01 files may start with a UTF-8 BOM (EF BB BF),
    # which is valid XML but fails a startswith('<?xml') test.
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise ValueError(f'{key}: invalid XMLTV XML: {exc}') from exc
    if root.tag != 'tv':
        raise ValueError(f'{key}: not XMLTV tv root')
    channel_count = len(root.findall('channel'))
    program_count = len(root.findall('programme'))
    if channel_count < (80 if key == 'GR' else 20) or program_count < (2000 if key == 'GR' else 300):
        raise ValueError(f'{key}: unexpectedly low counts ({channel_count} channels, {program_count} entries)')
    # Validate forward-looking coverage, not just syntactic validity.
    dates = [e.get('start', '')[:8] for e in root.findall('programme')]
    tomorrow = (NOW + timedelta(days=1)).strftime('%Y%m%d')
    today = NOW.strftime('%Y%m%d')
    if not any(x in (today, tomorrow) for x in dates):
        raise ValueError(f'{key}: feed has no program starting today or tomorrow ({today}/{tomorrow})')
    print(f'{key}: {channel_count} channels, {program_count} events, {len(payload)} compressed bytes')
    return payload

def publish_iptv_xmltv(downloaded):
    """Publish a combined XMLTV feed for IPTV players such as TiviMate.

    Preserve original channel IDs so tvg-id matching works. If a channel ID
    occurs in both feeds, prefer GR to avoid duplicate XMLTV channel IDs.
    """
    roots = {}
    for key, blob in downloaded.items():
        roots[key] = ET.fromstring(gzip.decompress(blob))
    combined = ET.Element('tv', {'generator-info-name': 'Greece-Cyprus-EPG'})
    seen = set()
    for key in FEEDS:
        for ch in roots[key].findall('channel'):
            cid = ch.get('id')
            if cid and cid not in seen:
                seen.add(cid)
                combined.append(ch)
    gr_ids = {ch.get('id') for ch in roots['GR'].findall('channel')}
    counts = {}
    for key in FEEDS:
        n = 0
        for event in roots[key].findall('programme'):
            if event.get('channel') in seen:
                # Duplicate entries from a second feed are harmless for
                # different channels, but skip duplicate channel IDs entirely.
                if key != 'GR' and event.get('channel') in gr_ids:
                    continue
                combined.append(event)
                n += 1
        counts[key] = n
    xml = ET.tostring(combined, encoding='utf-8', xml_declaration=True)
    output = SITE / 'epg.xml.gz'
    tmp = SITE / 'epg.xml.gz.tmp'
    with gzip.open(tmp, 'wb', compresslevel=6) as f:
        f.write(xml)
    os.replace(tmp, output)
    print('IPTV XMLTV published:', output, len(seen), 'channels,', sum(counts.values()), 'programmes')

def main():
    # Download and validate BOTH feeds before replacing ANY local source.
    downloaded = {k: fetch(k, url) for k, url in FEEDS.items()}
    modified = False
    for key, blob in downloaded.items():
        path = DATA / f'{key}.xml.gz'
        if not path.exists() or sha256(path.read_bytes()).digest() != sha256(blob).digest():
            modified = True
    # Always rebuild on a new calendar day, even if feeds unexpectedly remain unchanged.
    stamp_path = DATA / 'build_date.txt'
    if stamp_path.exists() and stamp_path.read_text().strip() == NOW.strftime('%Y-%m-%d') and not modified and (SITE/'index.html').exists() and (SITE/'epg.xml.gz').exists():
        print('No XMLTV changes; same calendar day. Skipping rebuild.')
        return
    for key, blob in downloaded.items():
        path = DATA / f'{key}.xml.gz'
        tmp = path.with_suffix('.tmp')
        tmp.write_bytes(blob)
        os.replace(tmp, path)
    subprocess.run([sys.executable, str(ROOT/'build_epg.py')], check=True, cwd=ROOT)
    if not (SITE/'index.html').exists() or (SITE/'index.html').stat().st_size < 20000:
        raise ValueError('Failed to build a valid EPG page')
    publish_iptv_xmltv(downloaded)
    stamp_path.write_text(NOW.strftime('%Y-%m-%d'))
    (SITE/'status.json').write_text(json.dumps({
        'last_successful_update': NOW.isoformat(), 'source': 'EPGShare01',
        'feeds': list(FEEDS.keys()), 'changed': modified,
    }, ensure_ascii=False, indent=2))
    print('EPG generated successfully.')

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Update rejected, last hosted EPG remains unchanged: {error}', file=sys.stderr)
        sys.exit(1)
