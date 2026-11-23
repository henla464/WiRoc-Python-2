"""Self-check for the /api/logs/wiroc/ filters (since/until/level/logger, offset/limit paging).
Run on a device/venv with the full WiRoc dependency set:
    python3 test_log_tail_filters.py
Uses a synthetic log file; touches no real WiRoc.log or database.
"""
import json
import logging
import os
import tempfile
import time

import webroutes.api as api

FMT = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
ENTRIES = [
    ('2026-11-22 10:00:00', 'WiRoc', 'DEBUG', 'noise A'),
    ('2026-11-22 10:00:01', 'WiRoc', 'INFO', 'mesh root picks parent WR-24'),
    ('2026-11-22 10:00:02', 'WiRoc.Input', 'INFO', 'input noise'),
    ('2026-11-22 10:00:03', 'WiRoc', 'DEBUG', 'big debug entry line1\n  continuation line2'),
    ('2026-11-22 10:00:04', 'WiRoc.Display', 'ERROR', 'display failed\nTraceback...'),
    ('2026-11-22 10:00:05', 'WiRoc', 'VERBOSE', 'verbose noise'),
]


def write_log():
    path = os.path.join(tempfile.mkdtemp(), 'WiRoc.log')
    with open(path, 'w') as f:
        for ts, name, level, msg in ENTRIES:
            rec = logging.LogRecord(name, logging.INFO, '', 0, msg, None, None)
            rec.levelname = level
            rec.created = time.mktime(time.strptime(ts, '%Y-%m-%d %H:%M:%S'))
            rec.msecs = 0.0
            f.write(FMT.format(rec) + '\n')
    api.WIROC_LOG_PATH = path
    api.WIROC_LOG_BACKUP_COUNT = 0


def get(**params):
    resp = api.app.test_client().get('/api/logs/wiroc/', query_string=params)
    assert resp.status_code == 200, resp.data
    return json.loads(resp.data)['Value']


def main():
    write_log()

    lines = get(level='INFO')['lines']
    assert any('mesh root picks parent' in t for t in lines)
    assert not any('noise A' in t or 'verbose noise' in t or 'big debug' in t for t in lines)
    assert 'Traceback...' in ''.join(lines)  # continuation lines stay with their entry

    assert not any('input noise' in t for t in get(logger='WiRoc')['lines'])  # exact match
    assert len(get(logger='WiRoc.Input')['lines']) == 1

    lines = get(since='2026-11-22 10:00:02,000', until='2026-11-22 10:00:04,000')['lines']
    assert len(lines) == 3 and 'input noise' in lines[0]

    page = get(level='INFO', limit=2)
    assert len(page['lines']) == 2 and page['hasMore'] and page['nextOffset'] == 2
    rest = get(level='INFO', limit=2, offset=2)
    assert rest['lines'][0] not in page['lines'] and not rest['hasMore']

    tail = get(limit=3)  # no filters -> fast tail path, unchanged behaviour
    assert len(tail['lines']) == 3 and tail['hasMore'] is False

    print('all log tail filter checks passed')


if __name__ == '__main__':
    main()
