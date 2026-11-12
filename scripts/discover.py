#!/usr/bin/env python3
"""Discover explicit IronGlass mentions via search indexes, never IMDb crawling."""
import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import fetch, Results
ROOT = Path(__file__).resolve().parents[1]
BRAND = re.compile(r'\biron[\s-]*glass\b', re.I)


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def query_plan(year=None):
    year = year or datetime.now(timezone.utc).year
    common = [f'site:imdb.com/title/ "{brand}" {suffix}'.strip()
              for brand in ('IronGlass', 'Iron Glass', 'Iron-Glass')
              for suffix in ('', '"technical"', '"company credits"', '"full credits"')]
    extra = [f'site:imdb.com/title/ "{brand}" "{kind}"'
             for brand in ('IronGlass', 'Iron Glass')
             for kind in ('Short', 'Music Video', 'TV Series', 'TV Episode', 'Documentary', 'Video')]
    extra += [f'site:imdb.com/title/ "{brand}" {y}'
              for y in range(1990, year + 2) for brand in ('IronGlass', 'Iron Glass')]
    return common, extra


def normalize_url(url):
    url = html.unescape(url)
    if url.startswith('//'):
        url = 'https:' + url
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname and parsed.hostname.endswith('duckduckgo.com'):
        url = urllib.parse.parse_qs(parsed.query).get('uddg', [url])[0]
    return url


def extract(row, query, provider):
    url = normalize_url(row.get('url', ''))
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('https', 'http') or parsed.hostname not in ('imdb.com', 'www.imdb.com', 'm.imdb.com'):
        return None
    match = re.fullmatch(r'/(?:[a-z]{2}(?:-[A-Z]{2})?/)?title/(tt\d+)(?:/(technical|companycredits|fullcredits))?/?', parsed.path)
    if not match:
        return None
    snippet = ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', row.get('description', ''))).split())
    brand = BRAND.search(snippet)
    if not brand:
        return None
    # Keep a short attributable excerpt around the explicit brand, not a full page.
    start = max(0, brand.start() - 100)
    evidence = ('…' if start else '') + snippet[start:start + 420] + ('…' if len(snippet) > start + 420 else '')
    title = html.unescape(re.sub('<[^>]+>', '', row.get('title', '')))
    year = re.search(r'\b(?:19|20)\d{2}\b', title)
    kind = next((label for term, label in [('music video', 'Music video'), ('short', 'Short'), ('tv episode', 'TV'), ('tv series', 'TV')] if re.search(r'\b' + term + r'\b', title, re.I)), 'Onbekend')
    title = re.sub(r'\s*[-–|]\s*(Technical specifications|Company credits|Full cast.*|Full credits|IMDb).*$', '', title, flags=re.I).strip()
    suffix = match.group(2)
    return {'id': match.group(1), 'title': title or match.group(1), 'year': year.group() if year else '',
            'type': kind, 'evidence': evidence, 'url': f'https://www.imdb.com/title/{match.group(1)}/' + (suffix + '/' if suffix else ''),
            'status': 'Kandidaat', 'checked': timestamp(), 'provider': provider, 'query': query,
            'sourceKind': {'technical': 'Lensspecificaties', 'companycredits': 'Bedrijfscredits', 'fullcredits': 'Credits'}.get(suffix, 'Titelpagina')}


class Blocked(Exception):
    pass


class BraveResults(HTMLParser):
    """Read visible web-result cards; ignore scripts and unrelated page content."""
    def __init__(self):
        super().__init__()
        self.rows = []
        self.depth = 0
        self.block = None
        self.capture = None
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'div':
            self.depth += 1
            if 'snippet' in classes and attrs.get('data-type') == 'web':
                self.block = self.depth
                self.current = {'url': '', 'title': '', 'description': ''}
                self.rows.append(self.current)
            if self.current is not None:
                if 'search-snippet-title' in classes:
                    self.current['title'] = attrs.get('title', '')
                if 'content' in classes:
                    self.capture = self.depth
        if tag == 'a' and self.current is not None and not self.current['url']:
            self.current['url'] = attrs.get('href', '')

    def handle_endtag(self, tag):
        if tag != 'div':
            return
        if self.capture == self.depth:
            self.capture = None
        if self.block == self.depth:
            self.block = None
            self.current = None
            self.capture = None
        self.depth = max(0, self.depth - 1)

    def handle_data(self, data):
        if self.capture is not None and self.current is not None:
            self.current['description'] += data


def provider_search(provider, query, page=0):
    if provider == 'Brave':
        key = os.environ['BRAVE_SEARCH_API_KEY']
        data = json.loads(fetch('https://api.search.brave.com/res/v1/web/search?' + urllib.parse.urlencode({'q': query, 'count': 20, 'offset': page}), {'X-Subscription-Token': key, 'Accept': 'application/json'}))
        return data.get('web', {}).get('results', [])
    if provider == 'Brave Web':
        content = fetch('https://search.brave.com/search?' + urllib.parse.urlencode({'q': query, 'source': 'web'}))
        parser = BraveResults(); parser.feed(content)
        if not parser.rows:
            if 'No results found' in content or 'No search results' in content:
                return []
            raise Blocked('Geen leesbare webresultaten; mogelijk een zoekmachineblokkade.')
        return parser.rows
    if provider == 'DuckDuckGo':
        content = fetch('https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query}))
        if 'anomaly.js' in content or 'anomaly-modal' in content or 'challenge-form' in content:
            raise Blocked('Zoekmachine vraagt een CAPTCHA; deze bron wordt deze ronde overgeslagen.')
        parser = Results(); parser.feed(content)
        if not parser.rows and 'No results found' not in content and 'no-results' not in content:
            raise Blocked('Zoekpagina niet leesbaar; mogelijk geblokkeerd.')
        return parser.rows
    content = fetch('https://www.bing.com/search?' + urllib.parse.urlencode({'q': query, 'format': 'rss'}))
    root = ET.fromstring(content)
    if root.tag != 'rss':
        raise Blocked('Geen leesbare zoekfeed ontvangen.')
    return [{'url': item.findtext('link', ''), 'title': item.findtext('title', ''), 'description': item.findtext('description', '')} for item in root.findall('./channel/item')]


def atomic_json(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def run(root=ROOT, limit=20, delay=1.2):
    started = timestamp()
    status_path = root / 'scan-status.json'
    previous = json.loads(status_path.read_text()) if status_path.exists() else {}
    common, extra = query_plan()
    cursor = int(previous.get('nextCursor', 0)) % len(extra)
    take = min(max(limit - len(common), 0), len(extra))
    selected = common[:limit] + [extra[(cursor + n) % len(extra)] for n in range(take)]
    providers = ['Brave'] if os.environ.get('BRAVE_SEARCH_API_KEY') else ['Brave Web', 'DuckDuckGo', 'Bing RSS']
    records = json.loads((root / 'results.json').read_text())
    by_id = {r['id']: r for r in records}
    disabled = set(); reports = []; hits = set(); added = set(); successful = 0
    for query in selected:
        for provider in providers:
            if provider in disabled:
                continue
            pages = range(2) if provider == 'Brave' else range(1)
            for page in pages:
                report = {'query': query, 'provider': provider, 'page': page + 1, 'matches': 0}
                try:
                    results = provider_search(provider, query, page)
                    if results and not any('imdb.com' in normalize_url(r.get('url', '')) for r in results):
                        raise ValueError('Zoekbron negeerde de IMDb-filter; resultaten verworpen.')
                    successful += 1
                    report['results'] = len(results)
                    for result in results:
                        row = extract(result, query, provider)
                        if not row:
                            continue
                        ident = row['id']; hits.add(ident); report['matches'] += 1
                        old = by_id.get(ident)
                        if old is None:
                            by_id[ident] = row; added.add(ident)
                        elif old.get('status') == 'Kandidaat':
                            # Preserve the title and best source rather than swapping for a less specific main page.
                            old['lastSeen'] = row['checked']
                            if old.get('sourceKind') in (None, 'Titelpagina') and row['sourceKind'] != 'Titelpagina':
                                old.update(row)
                    report['status'] = 'ok'
                except Exception as exc:
                    # Never include exception URLs/headers, which could expose credentials.
                    report['status'] = 'error'
                    report['error'] = str(exc)[:240] if isinstance(exc, (Blocked, ValueError)) else type(exc).__name__ + ': zoekbron niet beschikbaar'
                    if isinstance(exc, Blocked):
                        disabled.add(provider)
                reports.append(report)
                print(f'{provider}: {report["status"]}, {report["matches"]} matches — {query}', flush=True)
                if delay:
                    time.sleep(delay)
                if provider in disabled:
                    break
            if report.get('status') == 'ok' and report.get('matches', 0):
                break
        if len(disabled) == len(providers):
            break
    errors = sum(r['status'] == 'error' for r in reports)
    state = 'ok' if hits and not errors else 'partial' if hits else 'no_matches' if successful else 'blocked'
    status = {'state': state, 'startedAt': started, 'finishedAt': timestamp(),
              'lastSuccessfulAt': timestamp() if hits else previous.get('lastSuccessfulAt'),
              'queriesPlanned': len(selected), 'queriesAttempted': len({r['query'] for r in reports}),
              'requestsSucceeded': successful, 'errors': errors, 'matchedTitles': len(hits), 'newTitles': len(added),
              'totalTitles': len(by_id), 'providers': providers,
              'nextCursor': (cursor + take) % len(extra), 'queryInventory': len(common) + len(extra),
              'coverage': 'Zoekmachine-indexen; geen volledige IMDb-scan. Nul vondsten betekent niet dat er geen vermeldingen zijn.',
              'reports': reports}
    atomic_json(root / 'results.json', list(by_id.values()))
    atomic_json(status_path, status)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as f:
            f.write(f'## IronGlass zoekronde\n\nStatus: **{state}**. Nieuwe titels: **{len(added)}**. Unieke matches: **{len(hits)}**. Fouten: **{errors}**.\n\nDit doorzoekt zoekmachine-indexen, niet heel IMDb. Details staan in scan-status.json.\n')
    return status


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.limit <= 150:
        parser.error('--limit moet tussen 1 en 150 liggen')
    result = run(limit=args.limit)
    print(json.dumps({k: v for k, v in result.items() if k != 'reports'}, indent=2))
