#!/usr/bin/env python3
"""Run once in a clean local checkout and publish only discovery data."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys
from discover import run
ROOT=Path(__file__).resolve().parents[1]
def git(*args, capture=True):
    result=subprocess.run(['git',*args],cwd=ROOT,check=True,text=True,capture_output=capture)
    return result.stdout.strip() if capture else result

def main():
    if git('branch','--show-current')!='main':raise RuntimeError('Branch main vereist; er is niets gewijzigd.')
    remote=git('remote','get-url','origin').removesuffix('.git')
    if remote not in ('https://github.com/tvlmedia/ironglass-tool','git@github.com:tvlmedia/ironglass-tool'):raise RuntimeError('Onverwachte origin; er is niets gepubliceerd.')
    if git('status','--porcelain'):raise RuntimeError('Lokale wijzigingen gevonden. Er wordt niets overschreven of gestasht.')
    lock_path=Path(git('rev-parse','--git-path','ironglass-sync.lock'))
    if not lock_path.is_absolute():lock_path=ROOT/lock_path
    with lock_path.open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        git('pull','--ff-only',capture=False)
        report=run()
        changed=git('diff','--name-only').splitlines()
        if any(p not in ('results.json','scan-status.json') for p in changed) or git('diff','--cached','--name-only'):raise RuntimeError('Andere lokale wijzigingen; scan bewaard maar niet gecommit.')
        git('add','--','results.json','scan-status.json')
        if git('diff','--cached','--name-only'):
            git('commit','-m','Update discovered IMDb mentions from local scan',capture=False)
            git('push','origin','HEAD:main',capture=False)
        print(json.dumps({k:report[k] for k in ['state','newTitles','matchedTitles','errors']},indent=2))
        return 2 if report['state']=='blocked' else 0
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as e:print(f'Synchronisatie gestopt: {e}',file=sys.stderr);sys.exit(1)
