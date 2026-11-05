#!/usr/bin/env python3
"""Prepare a release; browser verification is mandatory before installation/push.

Never executes scripts supplied by a run. Uses only Python stdlib and node --check.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def prepare(source, output, date):
    source, output = Path(source), Path(output)
    read = lambda name: json.loads((source / name).read_text())
    execution = read('execution.json')
    if execution.get('status') == 'running' or not execution.get('finished_at'):
        raise ValueError('Producer is still running; retry later, do not publish')
    manifest = read('manifest.json')
    if manifest.get('run_id') != source.name or not source.name.startswith(date + '-'):
        raise ValueError('Run/date mismatch')
    if manifest.get('analysis_generated_at', '')[:10] != date:
        raise ValueError('Stale analysis')
    if execution.get('exit_code') != 0:
        raise ValueError('Producer process failed')
    validation = read('validation.json')
    failed = [x for x in validation.get('checks', []) if x.get('passed') is not True]
    # A launcher crash requires an independent browser check, not a fake pass.
    launch_failure = (len(failed) == 1 and failed[0].get('name') in ('validate-browser.cjs', 'real browser validation')
                      and any(x in failed[0].get('detail', '') for x in
                              ('SIGABRT', 'Executable doesn\'t exist', 'browserType.launch')))
    if not validation.get('passed') and not launch_failure:
        raise ValueError('Data/site validation failed: ' + str([x.get('name') for x in failed]))
    if execution.get('errors') and execution['errors'] != ['Agent validation failed']:
        raise ValueError('Unexpected producer error')
    html = (source / 'index.html').read_text()
    if (source / 'index.html').read_bytes() != (source / 'report.html').read_bytes():
        raise ValueError('Index/report mismatch')
    embedded = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)
    if not embedded or json.loads(embedded[1]) != read('run.json'):
        raise ValueError('HTML/run.json mismatch')
    for attrs, content in re.findall(r'<script\b([^>]*)>(.*?)</script>', html, re.S):
        if 'application/json' in attrs:
            json.loads(content)
    marker = "function categoryLabels(){const labels={...D.brand_categories.labels,...(['air','rail'].includes(active)?{tickets:'Продажи билетов'}:{})};"
    if html.count(marker) != 1:
        raise ValueError('Filter implementation changed; review before publication')
    html = html.replace("if(active==='air')delete labels.tours;", '')
    rule = "if(['air','rail'].includes(active))delete labels.tours;"
    if rule not in html:
        html = html.replace(marker, marker + rule)
    # Only the reviewed public exports below are part of the Pages release.
    html = re.sub(r'<a\b[^>]*href="archive\.sqlite"[^>]*>.*?</a>', '', html, flags=re.S)
    html = html.replace('../2026-10-27-october/report.html', 'archive/2026-10-27-october.html')
    output.mkdir(parents=True, exist_ok=True)
    scripts = '\n'.join(body for attrs, body in re.findall(r'<script\b([^>]*)>(.*?)</script>', html, re.S)
                        if 'application/json' not in attrs)
    subprocess.run(['node', '--check'], input=scripts, text=True, check=True, capture_output=True)
    (output / 'index.html').write_text(html)
    names = ['index.html']
    for name in ('report.md', 'run.json', 'monthly-coverage.json', 'archive-readme.md'):
        if (source / name).is_file():
            (output / name).write_bytes((source / name).read_bytes())
            names.append(name)
    hashes = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in names}
    result = {'run': source.name, 'date': date, 'browser_required': True,
              'producer_browser_launch_failed': launch_failure, 'files': hashes}
    (output / 'release-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('output', help='Temporary staging directory, not the live repository')
    parser.add_argument('--date', required=True, help='Moscow date YYYY-MM-DD')
    args = parser.parse_args()
    prepare(args.source, args.output, args.date)
