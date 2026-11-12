#!/usr/bin/env python3
"""IronGlass research desk. Python standard library only."""
import csv, html, io, json, os, re, threading, urllib.parse, urllib.request, urllib.error, ssl, subprocess
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from html.parser import HTMLParser
ROOT = Path(__file__).parent
LOCK = threading.Lock()
DB = ROOT / 'results.json'
MATCH = re.compile(r'iron[\s-]*glass', re.I)
QUERIES = ['site:imdb.com/title/ "IronGlass" "technical"', 'site:imdb.com/title/ "Iron Glass" "technical"', 'site:imdb.com/title/ "IronGlass" "short"', 'site:imdb.com/title/ "IronGlass" "music video"', 'site:imdb.com/title/ "IronGlass" "TV"']
def now(): return datetime.now(timezone.utc).isoformat()
def read(): return json.loads(DB.read_text()) if DB.exists() else []
def merge(rows):
    with LOCK:
        existing = {r['id']: r for r in read()}
        for row in rows:
            old = existing.get(row['id'])
            if not old or old['status'] != 'Gecontroleerd': existing[row['id']] = row
        tmp = DB.with_suffix('.tmp'); tmp.write_text(json.dumps(list(existing.values()), ensure_ascii=False, indent=2)); tmp.replace(DB)
        return list(existing.values())
def fetch(url, headers=None):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=18) as r: return r.read(4_000_000).decode('utf-8', errors='replace')
    except urllib.error.URLError as e:
        if not isinstance(e.reason, ssl.SSLCertVerificationError) or headers: raise
        # macOS curl uses the system trust store; TLS verification stays enabled.
        result=subprocess.run(['curl','-fsS','--max-time','18','--max-filesize','4000000',url],capture_output=True,check=True,timeout=20)
        return result.stdout.decode('utf-8',errors='replace')
class Results(HTMLParser):
    def __init__(self): super().__init__(); self.rows=[]; self.current=None; self.capture=None; self.depth=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs); cls=a.get('class','')
        if tag=='a' and 'result__a' in cls:
            self.current={'url':a.get('href',''), 'title':'', 'description':''}; self.rows.append(self.current); self.capture='title'; self.depth=1
        elif self.current and 'result__snippet' in cls: self.capture='description'; self.depth=1
        elif self.capture: self.depth+=1
    def handle_endtag(self, tag):
        if self.capture:
            self.depth-=1
            if self.depth<=0:self.capture=None
    def handle_data(self, data):
        if self.capture and self.current:self.current[self.capture]+=data

def candidate(url, title, snippet):
    url=html.unescape(url)
    if 'uddg=' in url:url=urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('uddg',[url])[0]
    p=urllib.parse.urlparse(url)
    if p.hostname not in ('imdb.com','www.imdb.com','m.imdb.com'): return None
    match=re.search(r'/title/(tt\d+)', p.path)
    if not match or not MATCH.search(snippet):return None
    ident=match.group(1); year=re.search(r'\b(19\d{2}|20\d{2})\b',title)
    return {'id':ident,'title':re.sub(r'\s*[-–|]\s*(Technical specifications.*|IMDb).*$', '',title,flags=re.I).strip(), 'year':year.group(0) if year else '', 'type':'Onbekend', 'evidence':snippet[:1600], 'url':f'https://www.imdb.com/title/{ident}/technical/', 'status':'Kandidaat', 'checked':now()}

def search():
    found=[]; errors=[]; key=os.environ.get('BRAVE_SEARCH_API_KEY','')
    for q in QUERIES:
        try:
            if key:
                data=json.loads(fetch('https://api.search.brave.com/res/v1/web/search?'+urllib.parse.urlencode({'q':q,'count':20}), {'X-Subscription-Token':key,'Accept':'application/json'}))
                rows=data.get('web',{}).get('results',[])
            else:
                page=fetch('https://html.duckduckgo.com/html/?'+urllib.parse.urlencode({'q':q}))
                parser=Results(); parser.feed(page); rows=parser.rows
                if not rows: raise ValueError('Geen leesbare zoekresultaten; mogelijk zoekmachineblokkade. Gebruik de zoeklinks of stel BRAVE_SEARCH_API_KEY in.')
            for row in rows:
                item=candidate(row.get('url',''), row.get('title',''), html.unescape(re.sub('<[^>]+>','',row.get('description',''))))
                if item:found.append(item)
        except Exception as e:errors.append(f'{q}: {e}')
    return {'rows':merge(found),'found':len({r['id'] for r in found}),'errors':errors}
class Handler(BaseHTTPRequestHandler):
    def json(self, data, status=200):
        raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path=='/api/results':return self.json({'rows':read(),'queries':QUERIES})
        if path=='/export.csv':
            out=io.StringIO(); w=csv.writer(out);w.writerow(['IMDb ID','Titel','Jaar','Type','Status','Bron','Bewijs','Controledatum'])
            for r in read():w.writerow([("'"+str(r[k])) if str(r[k]).startswith(('=','+','-','@')) else r[k] for k in ['id','title','year','type','status','url','evidence','checked']])
            raw=('\ufeff'+out.getvalue()).encode();self.send_response(200);self.send_header('Content-Type','text/csv; charset=utf-8');self.send_header('Content-Disposition','attachment; filename="ironglass.csv"');self.end_headers();self.wfile.write(raw);return
        if path not in ('/','/app.js','/style.css'):return self.json({'error':'Niet gevonden'},404)
        file=ROOT/'static'/({'/':'index.html'}.get(path,path.lstrip('/')));raw=file.read_bytes();self.send_response(200);self.send_header('Content-Type',{'/':'text/html','/app.js':'text/javascript','/style.css':'text/css'}[path]+'; charset=utf-8');self.end_headers();self.wfile.write(raw)
    def do_POST(self):
        # Only same-origin browser requests and local command-line clients.
        if self.headers.get('Origin') and self.headers['Origin'] != 'http://'+self.headers.get('Host',''):return self.json({'error':'Ongeldige herkomst'},403)
        try:
            length=int(self.headers.get('Content-Length',0))
            if length>100_000:raise ValueError('Invoer te groot')
            data=json.loads(self.rfile.read(length) or b'{}')
            if self.path=='/api/search':return self.json(search())
            if self.path=='/api/import':
                row=candidate(data.get('url',''),data.get('title',''),data.get('evidence',''))
                if not row:raise ValueError('Vul een IMDb-titellink en tekst met een expliciete IronGlass-vermelding in.')
                kind=data.get('type','Onbekend')
                if kind not in ['Film','Short','Music video','TV','Onbekend']:raise ValueError('Ongeldig type')
                row['type']=kind
                # A pasted excerpt is user supplied, not independently checked.
                row['status']='Handmatig aangeleverd'
                return self.json({'rows':merge([row])})
            return self.json({'error':'Niet gevonden'},404)
        except Exception as e:return self.json({'error':str(e)},400)
if __name__=='__main__':
    print('IronGlass Research: http://127.0.0.1:8765',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
