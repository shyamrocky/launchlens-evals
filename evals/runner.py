"""Pinned Writer component evaluation. Imports and dry runs never provision credentials.

Production permissions, prompts and ledgers are untouched. Execution records are
private; only synthetic tests and owner-reviewed cases may enter the public repo.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.error

from launchlens.content_review import ContentCall
from launchlens.live_package import profile
from launchlens.live_research import MAX_REQUEST_BYTES, dumps, strict_json
from launchlens.package_content import (
    CONFIG_SHA256, configuration, load_package_prompt, prepare_call, project_package_context,
)
from launchlens.structured_output import response_format
from launchlens.writer_providers import ProviderHTTP, read_selected_keys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'evals/manifest.json'
MODEL = 'NousResearch/Hermes-4-405B'
SMOKE_CAP = 6
PER_CALL_RESERVATION = Decimal('0.147456')
MAX_RESERVATION = Decimal('0.884736')
COLUMNS = (
    'run_label', 'case_id', 'attempt_no', 'timestamp', 'prompt_file', 'prompt_hash',
    'snapshot_hash', 'model', 'temperature', 'run_status', 'error_message',
    'input_tokens', 'output_tokens', 'latency_ms', 'cost_usd', 'langsmith_trace_id',
    'linkedin_post', 'raw_output_path',
)
DERIVED_PATHS = {
    '$.binding.authoritative_input_sha256',
    '$.projection_manifest.authoritative_input_sha256',
    '$.projection_manifest.model_input_sha256',
}
NOTES_PATH = '$.writer_brief.user_notes_data_only'


class EvalError(ValueError):
    """Fixed, safe diagnostic; never attach raw provider exceptions."""


def require(ok, message):
    if not ok:
        raise EvalError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', value),
            'Invalid case or run label')
    return value


def differences(left, right, path='$'):
    if type(left) is not type(right):
        return {path}
    if isinstance(left, dict):
        result = set()
        for key in left.keys() | right.keys():
            child = path + '.' + key
            result |= {child} if key not in left or key not in right else differences(left[key], right[key], child)
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return {path}
        return set().union(*(differences(a, b, f'{path}[{i}]') for i, (a, b) in enumerate(zip(left, right))))
    return set() if left == right else {path}


def load_manifest(path=MANIFEST):
    value = strict_json(Path(path).read_bytes())
    require(value['schema'] == 'launchlens-writer-eval-v1', 'Unknown manifest')
    require(value['model'] == MODEL and type(value['temperature']) is int and value['temperature'] == 0,
            'Unapproved model settings')
    require(value['max_tokens'] == value['max_completion_tokens'] == 8192 and value['timeout_seconds'] == 180,
            'Unapproved request bounds')
    require(type(value['call_cap']) is int and 0 < value['call_cap'] <= SMOKE_CAP,
            'Unapproved call cap')
    require(Decimal(value['per_call_reservation_usd']) == PER_CALL_RESERVATION and
            Decimal(value['reservation_usd']) == PER_CALL_RESERVATION * value['call_cap'] <= MAX_RESERVATION,
            'Unapproved reservation')
    cfg = configuration()
    spec = profile()['roles']['package_writer']
    require(value['package_configuration_sha256'] == CONFIG_SHA256 and
            sha((ROOT / 'data/templates/gtm/live_package_profile_v11.json').read_bytes()) == value['profile_sha256'],
            'Production configuration hash differs')
    require(spec['model_id'] == value['model'] and spec['max_completion_tokens'] == value['max_tokens'] and
            spec['input_per_million_usd'] == value['input_per_million_usd'] and
            spec['output_per_million_usd'] == value['output_per_million_usd'] and
            spec['context_tokens'] == value['context_tokens'], 'Configured pricing or token bounds differ')
    production = load_package_prompt('package_writer').encode()
    prompt_path = ROOT / value['prompt_file']
    require(prompt_path.resolve().is_relative_to((ROOT / 'evals/prompts').resolve()), 'Prompt location differs')
    require(not prompt_path.is_symlink() and prompt_path.read_bytes() == production and
            sha(production) == value['prompt_hash'] == cfg['prompts']['package_writer']['sha256'],
            'Baseline prompt hash differs')
    return value


def load_snapshot(path, manifest):
    path = Path(path)
    require(path.name != '.env' and not path.is_symlink(), 'Invalid snapshot source')
    raw = path.read_bytes()
    require(sha(raw) == manifest['snapshot_hash'], 'Snapshot hash differs')
    state = strict_json(raw)
    require(state['request']['market_id'] == 'US' and state['launch']['decision'] == 'Proceed' and
            not state['drafts'] and state['writing_attempts'] == 0 and not state.get('writer_retry'),
            'Snapshot is not an initial US Writer input')
    prepare_call(state, 'package_writer', projector=project_package_context)
    return state


def prepare_request(snapshot, notes, manifest):
    require(type(notes) is str and len(notes) <= 1000, 'Notes must be at most 1000 characters')
    state = deepcopy(snapshot)
    state['user_notes'] = notes
    original = prepare_call(snapshot, 'package_writer', projector=project_package_context)
    prepared = prepare_call(state, 'package_writer', projector=project_package_context)
    require(differences(original, prepared) <= DERIVED_PATHS | {NOTES_PATH},
            'A source field other than notes changed')
    model_input = deepcopy(prepared)
    model_input.pop('projection_manifest', None)
    payload = {
        'model': manifest['model'],
        'messages': [
            {'role': 'system', 'content': load_package_prompt('package_writer')},
            {'role': 'user', 'content': dumps(model_input)},
        ],
        'temperature': manifest['temperature'], 'max_tokens': manifest['max_tokens'],
        'stream': False, 'store': False,
    }
    return state, payload


def wire_request(payload, manifest):
    require(payload['messages'][0] == {'role': 'system', 'content': load_package_prompt('package_writer')},
            'Production prompt binding differs')
    content = strict_json(payload['messages'][1]['content'])
    require(content['writer_brief']['package_contract']['sha256'] == manifest['package_configuration_sha256'],
            'Package binding differs')
    wire = deepcopy(payload)
    wire['max_completion_tokens'] = manifest['max_completion_tokens']
    wire['response_format'] = response_format(content['output_schema'])
    require(len(dumps(wire).encode()) <= MAX_REQUEST_BYTES, 'Request exceeds size bound')
    return wire


CASE_TYPES = {'normal': ('N', 15), 'edge': ('E', 9), 'known_failure': ('KF', 4), 'adversarial': ('A', 2)}
SEALED_IDS = frozenset({'A-01', 'E-01', 'E-06', 'KF-03', 'KF-04', 'N-05'})
SEALED_SEED = 20261115
APPROVED_CLAIMS = {
    'PROD-002': 'The documented flavor combines cherry with vanilla notes.',
    'PROD-003': 'Its concept is inspired by classic soda floats.',
}


def validate_dataset(dataset):
    """Validate public v0 metadata and all 30 records without generating/scoring."""
    from launchlens.linkedin_drafting import CTA
    require(type(dataset) is dict and dataset.get('dataset_version') == 'v0', 'Unknown dataset version')
    require(dataset.get('status') == 'draft', 'Unexpected dataset status')
    require(dataset.get('approved_claims') == APPROVED_CLAIMS and dataset.get('fixed_cta') == CTA,
            'Dataset claims or CTA differ')
    require(dataset.get('hashtag_rule') == {
        'count': 3, 'nonempty': True, 'fixed_values': None, 'claim_bearing_hashtags_require_support': True,
    }, 'Dataset hashtag rule differs')
    rules = dataset.get('scoring_rules')
    require(type(rules) is dict and rules.get('global_checks_apply_to_every_case') is True and
            type(rules.get('missing_citation_rule')) is str and rules['missing_citation_rule'] and
            type(rules.get('pass_bars')) is dict, 'Dataset scoring rules are missing')
    draw = dataset.get('sealed_draw')
    require(type(draw) is dict and type(draw.get('seed')) is int and draw['seed'] == SEALED_SEED and
            type(draw.get('case_ids')) is list and len(draw['case_ids']) == 6 and
            set(draw['case_ids']) == SEALED_IDS, 'Approved sealed draw differs; do not redraw')
    cases = dataset.get('cases')
    require(type(cases) is list and len(cases) == 30, 'Dataset must contain 30 cases')
    fields = {'case_id', 'type', 'slice', 'intent', 'pmm_note', 'expected_behavior', 'critical_failures', 'sealed'}
    expected = {f'{prefix}-{i:02d}': kind for kind, (prefix, count) in CASE_TYPES.items()
                for i in range(1, count + 1)}
    seen = set()
    for case in cases:
        require(type(case) is dict and set(case) == fields, 'Unexpected case fields')
        cid = identifier(case['case_id'])
        require(cid not in seen and cid in expected and case['type'] == expected[cid],
                'Case IDs, counts or types differ')
        require(case['slice'] == ('normal' if case['type'] == 'normal' else 'pressure'),
                'Case slice differs from type')
        require(type(case['sealed']) is bool and case['sealed'] == (cid in SEALED_IDS),
                'Case sealed flag differs from approved draw')
        require(all(type(case[k]) is str and case[k].strip() for k in ('intent', 'expected_behavior')),
                'Intent and expected behavior are required')
        require(type(case['pmm_note']) is str and len(case['pmm_note']) <= 1000,
                'Invalid case notes')
        require(type(case['critical_failures']) is list and all(type(v) is str and v.strip()
                for v in case['critical_failures']), 'Invalid critical failures')
        seen.add(cid)
    require(seen == set(expected), 'Missing dataset cases')
    return cases


def cases_from(path, *, mode='working', case_ids=None):
    """Select before preparing requests; never expose sealed cases in Phase 0."""
    path = Path(path)
    require(path.name != '.env', 'Invalid cases source')
    require(mode in {'working', 'smoke'}, 'Unsupported Phase 0 selection mode')
    cases = validate_dataset(strict_json(path.read_bytes()))
    by_id = {c['case_id']: c for c in cases}
    if case_ids is not None:
        require(type(case_ids) is list and case_ids and len(set(case_ids)) == len(case_ids),
                'Explicit case IDs must be nonempty and unique')
        require(all(type(cid) is str and cid in by_id for cid in case_ids), 'Unknown case ID')
        require(not any(by_id[cid]['sealed'] for cid in case_ids), 'Sealed cases are refused in Phase 0')
        selected = [by_id[cid] for cid in case_ids]
    else:
        require(mode != 'smoke', 'Smoke mode requires explicit working case IDs')
        selected = [c for c in cases if not c['sealed']]
    if mode == 'smoke':
        require(5 <= len(selected) <= 6, 'Smoke selection must contain 5 or 6 working cases')
    # Internal compatibility mapping only: preserve public type/slice and note text.
    # No rubric or metadata field enters the Writer request.
    return [dict(deepcopy(case), user_notes=case['pmm_note']) for case in selected]


def private_write(path, data):
    """Exclusive, private files. Never overwrite an earlier execution artifact."""
    raw = data if isinstance(data, bytes) else dumps(data).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def check_approval(approval, manifest, cases, run_label, cap):
    """A separately provisioned, private execution authorization; never made by dry-run."""
    require(type(approval) is dict and approval.get('owner_instruction') == 'run smoke test' and
            approval.get('run_label') == run_label and approval.get('manifest_hash') == sha(dumps(manifest).encode()) and
            approval.get('cases_hash') == sha(dumps(cases).encode()) and
            approval.get('call_cap') == cap and
            approval.get('reservation_usd') == str(PER_CALL_RESERVATION * cap),
            'Separate matching owner smoke authorization is required')


def extract_linkedin(candidate):
    try:
        content = candidate['linkedin']['content']
        fields = [content[name] for name in ('hook', 'body', 'cta')]
        require(all(type(v) is str and v.strip() for v in fields), 'LinkedIn text cannot be extracted')
        tags = content['hashtags']
        require(type(tags) is list and all(type(v) is str for v in tags), 'LinkedIn hashtags cannot be extracted')
        return '\n\n'.join(fields + ([' '.join(tags)] if tags else []))
    except (KeyError, TypeError):
        raise EvalError('LinkedIn structure cannot be extracted') from None


def cost_fields(response, manifest):
    usage = response.get('usage') if type(response) is dict else None
    if type(usage) is not dict:
        return None
    a, b, total = (usage.get(k) for k in ('prompt_tokens', 'completion_tokens', 'total_tokens'))
    if not (all(type(v) is int and v >= 0 for v in (a, b, total)) and a + b == total and
            a <= manifest['context_tokens'] - manifest['max_tokens'] and b <= manifest['max_tokens']):
        return None
    cost = (Decimal(a) * Decimal(manifest['input_per_million_usd']) +
            Decimal(b) * Decimal(manifest['output_per_million_usd'])) / Decimal(1_000_000)
    if cost > PER_CALL_RESERVATION:
        return None
    return a, b, cost


class AttemptTransport:
    def __init__(self, payload, manifest, factory, raw_path):
        self.expected = deepcopy(payload)
        self.manifest, self.factory, self.raw_path = manifest, factory, raw_path
        self.response = None
        self.status = None
        self.used = False

    def __call__(self, payload):
        require(not self.used and payload == self.expected, 'Attempt or prepared request differs')
        self.used = True
        wire = wire_request(payload, self.manifest)
        http = self.factory(wire)
        try:
            reply = http(wire)
        except Exception as error:
            reason = error.reason if isinstance(error, urllib.error.URLError) else error
            self.status = 'timeout' if isinstance(reason, TimeoutError) else 'transport_error'
            raise EvalError('Provider attempt failed') from None
        private_write(self.raw_path, reply.body)
        if reply.status != 200 or reply.credential_redacted:
            self.status = 'transport_error'
            raise EvalError('Provider response was not usable')
        self.status = 'content_fail_unparseable'
        if reply.truncated:
            raise EvalError('Provider response was truncated')
        try:
            self.response = strict_json(reply.body)
        except Exception:
            raise EvalError('Provider response was not JSON') from None
        return self.response


def validate_retry(results, outputs, retry_of, cases, manifest):
    origin = identifier(retry_of)
    with (results / (origin + '.csv')).open(newline='') as stream:
        rows = {row['case_id']: row for row in csv.DictReader(stream)}
    prior = strict_json((outputs / origin / 'inputs.json').read_bytes())
    require(prior['retry_of'] is None and prior['manifest'] == manifest,
            'Only an original baseline attempt may be manually retried')
    for case in cases:
        row = rows.get(case['case_id'], {})
        require(row.get('attempt_no') == '1' and row.get('run_status') in {'transport_error', 'timeout'} and
                case in prior['cases'], 'Only an identical failed transport attempt may be retried')
    ids = {c['case_id'] for c in cases}
    for path in outputs.glob('*/inputs.json'):
        previous = strict_json(path.read_bytes())
        require(previous.get('retry_of') != origin or not ids.intersection(c['case_id'] for c in previous['cases']),
                'A second manual retry is not allowed')


def run_evaluation(manifest, snapshot, cases, run_label, *, live=False, call_cap=None,
                   approval=None, wire_factory=None, storage_root=ROOT, retry_of=None):
    """One attempt per selected case. Injected wire factory is for offline testing."""
    identifier(run_label)
    cap = manifest['call_cap'] if call_cap is None else call_cap
    require(type(cap) is int and 0 < cap <= manifest['call_cap'] <= SMOKE_CAP, 'Call cap exceeds approval')
    require(Decimal(manifest['reservation_usd']) <= MAX_RESERVATION and
            PER_CALL_RESERVATION * cap <= Decimal(manifest['reservation_usd']), 'Reservation exceeds approval')
    require(cases and len({identifier(c['case_id']) for c in cases}) == len(cases), 'Duplicate or missing cases')
    require(not any(c.get('sealed', False) for c in cases), 'Sealed cases are refused in Phase 0')
    # Prepare and validate before making any output directory or acquiring credentials.
    requests = [prepare_request(snapshot, case['user_notes'], manifest) for case in cases[:cap]]
    results, outputs = Path(storage_root) / 'evals/results', Path(storage_root) / 'evals/outputs'
    require(not (results / (run_label + '.csv')).exists() and not (outputs / run_label).exists(),
            'Run label already exists; use a new label')
    if retry_of:
        validate_retry(results, outputs, retry_of, cases, manifest)
    if not live:
        return {'mode': 'dry_run', 'cases_prepared': len(requests), 'calls_made': 0,
                'call_cap': cap, 'maximum_reservation_usd': str(PER_CALL_RESERVATION * cap),
                'cases_beyond_cap': max(0, len(cases) - cap)}
    check_approval(approval, manifest, cases, run_label, cap)
    if wire_factory is None:
        # Environment-only provisioning at separately authorized execution time.
        # Never read .env or discover unrelated service credentials.
        key = read_selected_keys({'NEBIUS_API_KEY'})['NEBIUS_API_KEY']
        def wire_factory(wire):
            require(key.encode() not in dumps(wire).encode(), 'Request contains a credential')
            return ProviderHTTP({'provider': 'nebius', 'model_id': manifest['model']}, key,
                                request_validator=lambda candidate: candidate == wire,
                                timeout_seconds=manifest['timeout_seconds'])
    require(not results.is_symlink() and not outputs.is_symlink(), 'Private output location is a symlink')
    results.mkdir(parents=True, exist_ok=True, mode=0o700)
    outputs.mkdir(parents=True, exist_ok=True, mode=0o700)
    run_dir = outputs / run_label
    run_dir.mkdir(mode=0o700)  # Exclusive reservation of the label, even if interrupted.
    private_write(run_dir / 'inputs.json', {'manifest': manifest, 'cases': cases, 'retry_of': retry_of})
    private_write(run_dir / 'approval.json', approval)
    fd = os.open(results / (run_label + '.csv'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    calls, known_cost, retained = 0, Decimal(0), Decimal(0)
    stop_reason = 'completed'
    with os.fdopen(fd, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        stream.flush()
        for case, (state, payload) in zip(cases[:cap], requests):
            if calls >= cap or known_cost + retained + PER_CALL_RESERVATION > Decimal(manifest['reservation_usd']):
                stop_reason = 'cap_reached'
                break
            raw = run_dir / (case['case_id'] + '.bin')
            transport = AttemptTransport(payload, manifest, wire_factory, raw)
            call = ContentCall(transport, stage='package_writer', model_id=manifest['model'],
                               projector=project_package_context)
            row = dict.fromkeys(COLUMNS, '')
            row.update(run_label=run_label, case_id=case['case_id'], attempt_no=2 if retry_of else 1,
                       timestamp=datetime.now(timezone.utc).isoformat(), prompt_file=manifest['prompt_file'],
                       prompt_hash=manifest['prompt_hash'], snapshot_hash=manifest['snapshot_hash'],
                       model=manifest['model'], temperature=manifest['temperature'])
            # The durable claim precedes dispatch. An interrupted attempt is never silently reused.
            private_write(run_dir / (case['case_id'] + '.claim.json'), {'reserved_usd': str(PER_CALL_RESERVATION)})
            calls += 1
            started = time.monotonic()
            try:
                candidate = call(state)
                row['linkedin_post'] = extract_linkedin(candidate)
                row['run_status'] = 'returned'
            except Exception:
                row['run_status'] = transport.status or 'transport_error'
                row['error_message'] = {
                    'timeout': 'provider_timeout', 'transport_error': 'provider_or_transport_failure',
                    'content_fail_unparseable': 'output_cannot_be_parsed_or_extracted',
                }[row['run_status']]
            row['latency_ms'] = round((time.monotonic() - started) * 1000, 3)
            if raw.exists():
                row['raw_output_path'] = raw.relative_to(storage_root).as_posix()
            measured = cost_fields(transport.response, manifest)
            if measured:
                a, b, cost = measured
                row.update(input_tokens=a, output_tokens=b, cost_usd=str(cost))
                known_cost += cost
            else:
                retained += PER_CALL_RESERVATION
            writer.writerow(row)
            stream.flush()
            os.fsync(stream.fileno())
            if measured is None:
                stop_reason = 'usage_unknown_reservation_retained'
                break
        if stop_reason == 'completed' and len(cases) > cap:
            stop_reason = 'cap_reached'
    summary = {'mode': 'live', 'calls_made': calls, 'call_cap': cap,
               'estimated_known_cost_usd': str(known_cost), 'unknown_cost_reservation_usd': str(retained),
               'accounted_and_reserved_usd': str(known_cost + retained), 'stop_reason': stop_reason}
    private_write(run_dir / 'summary.json', summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--mode', choices=('working', 'smoke'), default='smoke')
    parser.add_argument('--case-ids', nargs='+', help='Explicit working case IDs in execution order')
    parser.add_argument('--run-label', required=True)
    parser.add_argument('--call-cap', type=int)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--approval-file', type=Path)
    parser.add_argument('--retry-of', help='Original run label; manual transport retry only')
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        snapshot = load_snapshot(args.snapshot, manifest)
        cases = cases_from(args.cases, mode=args.mode, case_ids=args.case_ids)
        approval = None
        if args.live:
            require(args.approval_file is not None and args.approval_file.resolve().is_relative_to(
                (ROOT / 'evals/outputs').resolve()), 'A private owner authorization is required')
            approval = strict_json(args.approval_file.read_bytes())
        summary = run_evaluation(manifest, snapshot, cases, args.run_label, live=args.live,
                                 call_cap=args.call_cap, approval=approval, retry_of=args.retry_of)
        print(dumps(summary))
        return 0
    except Exception:
        print('Evaluation stopped: preflight or execution failed; no automatic retry.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
