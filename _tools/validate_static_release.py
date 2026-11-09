"""Static fallback when browser tooling is unavailable; never claims UI coverage."""
import argparse, hashlib, json, re, subprocess, tempfile
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from html.parser import HTMLParser

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]
    def handle_starttag(self, tag, attrs):
        for k,v in attrs:
            if k in ('href','src') and v: self.links.append(v)

def validate(folder):
    p=Path(folder); html=(p/'index.html').read_text()
    scripts=re.findall(r'<script\b([^>]*)>(.*?)</script>',html,re.S)
    embedded=[json.loads(body) for attrs,body in scripts if 'id="report-data"' in attrs]
    data=json.loads((p/'run.json').read_text()); assert embedded == [data], 'Embedded data mismatch'
    date=data['period']['as_of'][:10]
    assert date <= datetime.now(ZoneInfo('Europe/Moscow')).date().isoformat(), 'Future data'
    facts=data['facts']; assert facts, 'Empty facts'
    ids=[f['id'] for f in facts]; assert len(ids)==len(set(ids)), 'Duplicate IDs'
    for attrs,body in scripts:
        if 'application/json' in attrs: json.loads(body)
        else:
            with tempfile.NamedTemporaryFile(suffix='.js',mode='w') as f:
                f.write(body); f.flush(); subprocess.run(['node','--check',f.name],check=True,capture_output=True)
    assert "if(['air','rail'].includes(active))delete labels.tours;" in html, 'Missing tours exclusion'
    links=Links(); links.feed(html)
    for link in links.links:
        if link.startswith(('http:','https:','data:','blob:','#','mailto:')) or '${' in link: continue
        target=(p/link.split('#')[0].split('?')[0]).resolve()
        assert target.is_relative_to(p.resolve()) and target.is_file(), 'Missing local link: '+link
    manifest=json.loads((p/'release-check.json').read_text())
    hashes={n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in manifest['files']}
    assert hashes==manifest['files'], 'Manifest hash mismatch'
    receipt={'mode':'static_fallback','browser_checked':False,'limitation':'Interactive behavior and rendering not tested','date':date,'facts':len(facts),'files':hashes,'checked_at':datetime.now(ZoneInfo('Europe/Moscow')).isoformat()}
    (p/'static-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('staging');validate(parser.parse_args().staging)
