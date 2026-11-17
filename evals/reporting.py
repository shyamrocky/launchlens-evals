"""Private baseline reporting: working content only, sealed numeric aggregates.

Never opens the sealed content CSV or sealed raw responses. Reporting is offline;
trace delivery is resolved exclusively from the append-only local sidecar.
"""
from collections import Counter
from decimal import Decimal
import csv
import json
import math
from pathlib import Path
import statistics

from evals.runner import METRIC_COLUMNS, PER_CALL_RESERVATION, SEALED_IDS, require
from evals.tracing import resolved_rows

STATUSES = {'returned', 'content_fail_unparseable', 'transport_error', 'timeout'}
TRACE_STATUSES = {'disabled', 'pending', 'trace failed', 'delivered'}
DISPLAY_COLUMNS = ('case_id', 'run_status', 'input_tokens', 'output_tokens', 'cost_usd',
                   'latency_ms', 'trace_status', 'linkedin_post')


def metrics(rows):
    """Strict numeric/status projection, never text or diagnostic propagation."""
    status_counts = Counter()
    trace_counts = Counter()
    latencies = []
    cost = Decimal(0)
    unknown_costs = 0
    tokens = {'input_tokens': 0, 'output_tokens': 0}
    unknown_tokens = {'input_tokens': 0, 'output_tokens': 0}
    for row in rows:
        require(row['run_status'] in STATUSES and row['trace_status'] in TRACE_STATUSES,
                'Invalid metric status')
        status_counts[row['run_status']] += 1
        trace_counts[row['trace_status']] += 1
        latency = float(row['latency_ms'])
        require(math.isfinite(latency) and latency >= 0, 'Invalid latency metric')
        latencies.append(latency)
        if row['cost_usd'] == '':
            unknown_costs += 1
        else:
            value = Decimal(row['cost_usd'])
            require(value.is_finite() and 0 <= value <= PER_CALL_RESERVATION, 'Invalid cost metric')
            cost += value
        for name in tokens:
            if row[name] == '':
                unknown_tokens[name] += 1
            else:
                value = int(row[name])
                require(value >= 0, 'Invalid token metric')
                tokens[name] += value
    p95 = (statistics.quantiles(latencies, n=100, method='inclusive')[94]
           if len(latencies) > 1 else latencies[0] if latencies else None)
    return {'calls': len(rows), 'status_counts': dict(status_counts),
            'trace_status_counts': dict(trace_counts), **tokens,
            'unknown_token_attempts': unknown_tokens, 'known_cost_usd': str(cost),
            'unknown_cost_attempts': unknown_costs,
            'retained_reservation_usd': str(PER_CALL_RESERVATION * unknown_costs),
            'p50_latency_ms': statistics.median(latencies) if latencies else None,
            'p95_latency_ms': p95, 'max_latency_ms': max(latencies) if latencies else None}


def code_checks(row, *, root, manifest, snapshot):
    """Existing LinkedIn checks on a working response only; no semantic verdict."""
    from launchlens.package_content import normalize_package, prepare_package_input, check_field_claims
    from launchlens.linkedin_drafting import CTA, admit_output, evidence_records
    from launchlens.content_contracts import validate_draft
    from launchlens.voice_policy import validate_tone_structure
    from evals.runner import prepare_request, cases_from
    require(row['case_id'] not in SEALED_IDS, 'Sealed content checks are forbidden')
    if row['run_status'] != 'returned':
        return {'status': 'not_run_output_unavailable'}
    path = Path(root) / row['raw_output_path']
    expected = Path(root) / 'evals/outputs/baseline_v1/working' / (row['case_id'] + '.bin')
    require(path == expected and not path.is_symlink(), 'Invalid working response source')
    try:
        response = json.loads(path.read_bytes())
        candidate, _ = normalize_package(json.loads(response['choices'][0]['message']['content']))
        draft = candidate['linkedin']
        case = cases_from(Path(root) / manifest['dataset_file'], case_ids=[row['case_id']],
                          expected_hash=manifest['dataset_sha256'])[0]
        state, _ = prepare_request(snapshot, case['user_notes'], manifest)
        inputs = prepare_package_input(state)
    except Exception:
        return {'status': 'not_run_response_unavailable'}
    result = {}
    operations = {
        'structure_and_reference_validity': lambda: validate_draft(draft, format_name='linkedin',
                                                                  evidence_records=evidence_records(inputs)),
        'admission': lambda: admit_output(draft, inputs),
        'field_citation_coverage': lambda: check_field_claims(draft, 'linkedin'),
        'tone_structure': lambda: validate_tone_structure(draft, 'linkedin', inputs['tone_policy'], CTA),
    }
    for name, operation in operations.items():
        try:
            operation()
            result[name] = 'pass'
        except Exception as error:
            result[name] = {'result': 'fail', 'diagnostic': getattr(error, 'diagnostic', {'rule': 'check_failed'})}
    content = draft.get('content', {})
    tags = content.get('hashtags') if type(content) is dict else None
    result['cta_exact'] = type(content) is dict and content.get('cta') == CTA
    result['hashtag_count'] = len(tags) if type(tags) is list else None
    result['hashtags_nonempty'] = type(tags) is list and all(type(t) is str and t.strip() for t in tags)
    result['body_words'] = len(content['body'].split()) if type(content.get('body')) is str else None
    result['semantic_review_required'] = True
    return result


def baseline_report(root, *, manifest=None, snapshot=None):
    """Returns 24 working records and sealed aggregates, never sealed content."""
    root = Path(root)
    results = root / 'evals/results'
    sidecar = root / 'evals/outputs/baseline_v1/trace-status.jsonl'
    working = resolved_rows(results / 'baseline_v1.csv', sidecar)
    from evals.runner import CASE_TYPES
    allowed = {f'{prefix}-{i:02d}' for prefix, count in CASE_TYPES.values()
               for i in range(1, count + 1)} - SEALED_IDS
    require(all(row['case_id'] in allowed for row in working) and
            len({row['case_id'] for row in working}) == len(working), 'Invalid working result IDs')
    metric_path = results / 'baseline_v1_sealed_metrics.csv'
    with metric_path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == list(METRIC_COLUMNS), 'Invalid sealed metrics columns')
    sealed = resolved_rows(metric_path, sidecar)
    require(all(row['case_id'] in SEALED_IDS for row in sealed) and
            len({row['case_id'] for row in sealed}) == len(sealed), 'Invalid sealed metric IDs')
    visible = []
    for row in working:
        item = {key: row[key] for key in DISPLAY_COLUMNS}
        if manifest is not None and snapshot is not None:
            item['code_checks'] = code_checks(row, root=root, manifest=manifest, snapshot=snapshot)
        visible.append(item)
    return {'working': visible, 'sealed': metrics(sealed), 'totals': metrics(working + sealed),
            'p95_method': 'inclusive linear interpolation; all recorded attempts',
            'sealed_content': 'not opened or checked'}


def main(argv=None):
    import argparse
    from evals.runner import ROOT, load_manifest, load_snapshot
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest()
        snapshot = load_snapshot(args.snapshot, manifest)
        print(json.dumps(baseline_report(ROOT, manifest=manifest, snapshot=snapshot), ensure_ascii=False))
        return 0
    except Exception:
        print('Report stopped: offline verification failed; no sealed content displayed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
