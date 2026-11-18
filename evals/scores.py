"""Lossless owner-score import. No service calls, scoring inference or feedback upload."""
import csv
from io import StringIO
import json
from pathlib import Path

from evals import runner as r

FIELDS = ('case_id', 'slice', 'contract_citation', 'factual_support', 'compliance',
          'failure_category', 'severity', 'notes')
QUALITY_FIELDS = ('contract_citation', 'factual_support', 'compliance')


def working_ids():
    return {f'{prefix}-{i:02d}' for prefix, count in r.CASE_TYPES.values()
            for i in range(1, count + 1)} - r.SEALED_IDS


def parse_scores(raw):
    reader = csv.DictReader(StringIO(raw.decode('utf-8-sig'), newline=''))
    r.require(reader.fieldnames == list(FIELDS), 'Unexpected owner-score columns')
    rows = list(reader)
    r.require(len(rows) == 24 and {v['case_id'] for v in rows} == working_ids(),
              'Owner scores require exactly the 24 working cases')
    r.require(len({v['case_id'] for v in rows}) == 24, 'Duplicate owner-score IDs')
    for row in rows:
        r.require(set(row) == set(FIELDS) and all(type(v) is str for v in row.values()),
                  'Malformed owner-score row')
        r.require(row['slice'] == ('normal' if row['case_id'].startswith('N-') else 'pressure'),
                  'Owner-score slice differs')
        r.require(all(row[k] in {'pass', 'fail'} for k in QUALITY_FIELDS), 'Invalid owner quality label')
        r.require(row['severity'] in {'critical', 'minor', 'none'} and row['failure_category'] != '',
                  'Invalid owner failure label')
    return rows


def import_scores(source, *, root=r.ROOT):
    source = Path(source)
    r.require(source.name != '.env' and not source.name.startswith('.env.') and not source.is_symlink(), 'Invalid owner-score source')
    raw = source.read_bytes()
    rows = parse_scores(raw)
    directory = Path(root) / 'evals/results'
    r.require(not directory.is_symlink(), 'Invalid private score directory')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    csv_path = directory / 'baseline_v1_owner_scores.csv'
    json_path = directory / 'baseline_v1_owner_scores.json'
    r.require(not csv_path.exists() and not json_path.exists(), 'Imported scores already exist')
    document = {'schema': 'launchlens-owner-scores-v1', 'run_label': 'baseline_v1',
                'source_sha256': r.sha(raw), 'fields': list(FIELDS), 'rows': rows,
                'status': 'owner_confirmed_baseline', 'feedback_upload_authorized': False}
    r.private_write(csv_path, raw)
    r.private_write(json_path, document)
    r.require(csv_path.read_bytes() == raw and json.loads(json_path.read_bytes())['rows'] == rows,
              'Owner-score copy verification failed')
    return {'rows': len(rows), 'source_sha256': r.sha(raw), 'byte_identical_csv': True,
            'all_field_values_preserved': True, 'feedback_uploaded': False}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(import_scores(args.source)))
        return 0
    except Exception:
        print('Owner-score import stopped; no values changed or feedback uploaded.')
        return 1


def feedback_plan(document, source_csv, attempt_rows, *, unblinded=False):
    """Prepare write arguments only; no SDK/client/network/upload is present here.

    Current release supports baseline working scores only. Sealed feedback and
    later score imports require their own reviewed reveal/import release.
    """
    from uuid import UUID, NAMESPACE_URL, uuid5
    r.require(unblinded is True, 'Owner scoring must be unblinded before feedback planning')
    r.require(type(document) is dict and document.get('schema') == 'launchlens-owner-scores-v1' and
              document.get('run_label') == 'baseline_v1', 'Unsupported score release')
    source_csv = Path(source_csv)
    r.require(source_csv.name != '.env' and not source_csv.name.startswith('.env.') and not source_csv.is_symlink(), 'Invalid feedback score source')
    raw = source_csv.read_bytes()
    r.require(r.sha(raw) == document['source_sha256'] and parse_scores(raw) == document['rows'],
              'Score source or imported values changed')
    selected = [row for row in attempt_rows if row.get('case_id') in working_ids()]
    r.require(len(selected) == 24 and {row['case_id'] for row in selected} == working_ids() and
              len(attempt_rows) == 24, 'Feedback requires only the 24 working attempt rows')
    by_id = {row['case_id']: row for row in selected}
    plan = []
    fields = {'contract':'contract_citation','factual_support':'factual_support','compliance':'compliance',
              'failure_category':'failure_category','severity':'severity'}
    for row in document['rows']:
        attempt = by_id[row['case_id']]
        r.require(attempt.get('run_label') == 'baseline_v1' and attempt.get('attempt_no') == '1' and attempt.get('trace_status') == 'delivered',
                  'Feedback attempt identity differs')
        trace_id = str(UUID(attempt['langsmith_trace_id']))
        for key, field in fields.items():
            item = {'run_id':trace_id,'trace_id':trace_id,'key':key,'value':row[field],
                    'feedback_id':str(uuid5(NAMESPACE_URL,'launchlens-feedback/'+trace_id+'/'+key+'/'+document['source_sha256'])),
                    'stop_after_attempt':1,
                    'source_info':{'case_id':row['case_id'],'run_label':'baseline_v1',
                                   'scoring_source_sha256':document['source_sha256'],'owner_confirmed':True}}
            if field in QUALITY_FIELDS:
                item['score'] = 1 if row[field] == 'pass' else 0
            plan.append(item)
    return plan


if __name__ == '__main__':
    raise SystemExit(main())
