"""One pinned exploratory final round: drift first, then final; no implicit live work.

Existing evaluation and production modules are imported, never overridden. Sealed
responses are persisted but never reopened, measured or displayed before release.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import csv
import json
import os
from pathlib import Path
import random
import secrets
import time
import urllib.error

from evals import runner as r, experiments as ex, tracing as tr
from evals.measurement import VERSION, m1, package_checks
from evals.reporting import metrics
from launchlens.package_content import prepare_package_input

ROOT = r.ROOT
ORDER = ('drift_baseline_v1', 'final_v1')
DRIFT_IDS = ['N-09', 'E-07', 'A-02']
CONTROLS = {'N-12', 'N-14', 'E-04'}
PARENT_HASH = '21ccd5c9871b19913ce3408ba2fb01fa8bcbd2b639af92373cdfa0fdc11a6081'
DATASET_HASH = '171b0af3aed00ba3697e5a3839ec0df9d96c80be77bf4b68b08b3ca82dd5ce21'
SNAPSHOT_HASH = '40b13adddd00e1df08937af16e7033afdcd19cc6338450dcc63b0a1e35f99bff'
PROMPTS = {
    'final_v1': ('evals/prompts/f2_note_direction_v1.txt',
                 'e516756b5fe2b3d0b485ba506f1eb4a4aabc6332916327faa778012460f9a7d9'),
    'drift_baseline_v1': ('evals/prompts/baseline_v1.txt',
                        '2198dd6d64f5adca13728b6460db14e0bd5e1ab55468534c3994df3ec890b505')}
CAPS = {'final_v1': 30, 'drift_baseline_v1': 3}
RESERVATIONS = {'final_v1': '4.423680', 'drift_baseline_v1': '0.442368'}
TOTAL_CAP = 33
TOTAL_RESERVATION = Decimal('4.866048')
ROUND_DIR = 'evals/outputs/final_round_v1'
COLUMNS = ex.COLUMNS


def local(name, directory):
    r.require(type(name) is str and not Path(name).is_absolute(), 'Invalid local path')
    path = ROOT / name
    base = ROOT / directory
    r.require(not path.is_symlink() and not base.is_symlink() and
              path.resolve().is_relative_to(base.resolve()) and
              all(not parent.is_symlink() for parent in path.parents if parent != ROOT and ROOT in parent.parents),
              'Invalid local path')
    return path


def load_round():
    """No credentials, private output reads, writes or network."""
    pp = local('evals/manifest.json', 'evals')
    r.require(r.sha(pp.read_bytes()) == PARENT_HASH, 'Parent manifest hash differs')
    parent = r.load_manifest(pp)  # Enforces unchanged production prompt/settings.
    r.require(parent['snapshot_hash'] == SNAPSHOT_HASH and
              parent['dataset_sha256'] == DATASET_HASH, 'Pinned source differs')
    raw = local(parent['dataset_file'], 'evals/cases').read_bytes()
    r.require(r.sha(raw) == DATASET_HASH, 'Frozen dataset hash differs')
    all_cases = r.validate_dataset(r.strict_json(raw))
    all_cases = [dict(deepcopy(c), user_notes=c['pmm_note']) for c in all_cases]
    by_id = {c['case_id']: c for c in all_cases}
    r.require(len(all_cases) == 30 and sum(c['sealed'] for c in all_cases) == 6,
              'Final selection differs')
    manifests, selections = {}, {}
    for label in ORDER:
        path = local('evals/experiments/' + label + '.json', 'evals/experiments')
        m = r.strict_json(path.read_bytes())
        ids = DRIFT_IDS if label == 'drift_baseline_v1' else [c['case_id'] for c in all_cases]
        r.require(m['schema'] == 'launchlens-final-round-v1' and m['run_label'] == label and
                  m['case_ids'] == ids and type(m['call_cap']) is int and
                  m['call_cap'] == CAPS[label], 'Round identity or selection differs')
        r.require(m['parent_manifest_file'] == 'evals/manifest.json' and
                  m['parent_manifest_sha256'] == PARENT_HASH, 'Round parent differs')
        for key in ('snapshot_id', 'snapshot_hash', 'dataset_file', 'dataset_sha256',
                    'model', 'temperature', 'max_tokens', 'max_completion_tokens', 'timeout_seconds'):
            r.require(type(m[key]) is type(parent[key]) and m[key] == parent[key], 'Round settings differ')
        r.require((m['candidate_prompt_file'], m['candidate_prompt_hash']) == PROMPTS[label] and
                  r.sha(local(m['candidate_prompt_file'], 'evals/prompts').read_bytes()) == PROMPTS[label][1],
                  'Round prompt hash differs')
        r.require(m['per_call_reservation_usd'] == str(r.PER_CALL_RESERVATION) and
                  m['reservation_usd'] == RESERVATIONS[label] and
                  type(m['combined_call_cap']) is int and m['combined_call_cap'] == TOTAL_CAP and
                  m['combined_reservation_usd'] == str(TOTAL_RESERVATION), 'Round spending bounds differ')
        r.require(m['execution_order'] == list(ORDER) and m['tracing_required'] is True and
                  m['automatic_retries'] is False and m['sealed_allowed'] is (label == 'final_v1') and
                  m['measurement_version'] == VERSION and m['interpretation'] ==
                  ('exploratory_not_adopted' if label == 'final_v1' else 'baseline_drift_check'),
                  'Round guardrails differ')
        manifests[label], selections[label] = m, [by_id[cid] for cid in ids]
        if label == 'drift_baseline_v1':
            r.require(not r.SEALED_IDS.intersection(ids), 'Sealed drift forbidden')
    return parent, manifests, selections


def prepare(snapshot, case, manifest, parent):
    if manifest['run_label'] == 'final_v1':
        return ex.prepare_candidate(snapshot, case['user_notes'], manifest, parent)
    state, payload = r.prepare_request(snapshot, case['user_notes'], parent)
    return state, r.wire_request(payload, parent)


def authorization(parent, manifests, cases):
    """Bindings for a separately recorded owner go; does not itself grant authority."""
    return {'owner_instruction': 'run final round', 'execution_order': list(ORDER),
            'manifest_hashes': {k: r.sha(r.dumps(v).encode()) for k, v in manifests.items()},
            'cases_hashes': {k: r.sha(r.dumps(v).encode()) for k, v in cases.items()},
            'dataset_hash': parent['dataset_sha256'], 'snapshot_hash': parent['snapshot_hash'],
            'call_caps': CAPS, 'combined_call_cap': TOTAL_CAP,
            'combined_reservation_usd': str(TOTAL_RESERVATION), 'tracing_required': True}


class Budget:
    def __init__(self):
        self.calls = 0
        self.known = Decimal(0)
        self.retained = Decimal(0)
        self.per_run = {label: [0, Decimal(0), Decimal(0)] for label in ORDER}

    def claim(self, label):
        n, known, retained = self.per_run[label]
        r.require(self.calls < TOTAL_CAP and n < CAPS[label] and
                  self.known + self.retained + r.PER_CALL_RESERVATION <= TOTAL_RESERVATION and
                  known + retained + r.PER_CALL_RESERVATION <= Decimal(RESERVATIONS[label]),
                  'Call cap or reservation reached')
        self.calls += 1
        self.retained += r.PER_CALL_RESERVATION
        self.per_run[label][0] += 1
        self.per_run[label][2] += r.PER_CALL_RESERVATION

    def settle(self, label, cost):
        if cost is not None:
            r.require(Decimal(0) <= cost <= r.PER_CALL_RESERVATION, 'Invalid measured cost')
            self.known += cost
            self.retained -= r.PER_CALL_RESERVATION
            self.per_run[label][1] += cost
            self.per_run[label][2] -= r.PER_CALL_RESERVATION

    def record(self):
        return {'calls_made': self.calls, 'known_cost_usd': str(self.known),
                'unknown_cost_reservation_usd': str(self.retained)}


def run_round(snapshot_path, *, live=False, approval=None, wire_factory=None, tracer_factory=None):
    parent, manifests, cases = load_round()
    snapshot = r.load_snapshot(snapshot_path, parent)
    prepared = {label: [prepare(snapshot, c, manifests[label], parent) for c in cases[label]] for label in ORDER}
    # Every label, including the whole round, is exclusive; never resume/retry implicitly.
    for name in (ROUND_DIR, *('evals/outputs/' + k for k in ORDER),
                 *('evals/results/' + k + suffix + '.csv' for k in ORDER for suffix in ('', '_sealed', '_sealed_metrics'))):
        r.require(not local(name, 'evals').exists(), 'Round label already reserved; no replay')
    if not live:
        return {'mode': 'dry_run', 'execution_order': list(ORDER),
                'prepared': {k: len(cases[k]) for k in ORDER}, 'calls_made': 0,
                'call_caps': dict(CAPS), 'combined_call_cap': TOTAL_CAP,
                'combined_reservation_usd': str(TOTAL_RESERVATION), 'hashes_verified': True,
                'sealed_outputs': 'not opened', 'tracing_required': True,
                'automatic_retries': False}
    r.require(approval == authorization(parent, manifests, cases), 'Separate manifest-bound owner go required')
    if wire_factory is None:
        r.require(os.environ.get('LANGSMITH_PROJECT') == tr.PROJECT and
                  len(os.environ.get('LANGSMITH_API_KEY', '')) >= 12, 'Tracing provisioning required')
        key = r.read_selected_keys({'NEBIUS_API_KEY'})['NEBIUS_API_KEY']
        def wire_factory(wire):
            r.require(key.encode() not in r.dumps(wire).encode(), 'Request contains credential')
            return r.ProviderHTTP({'provider': 'nebius', 'model_id': parent['model']}, key,
                                  request_validator=lambda candidate: candidate == wire,
                                  timeout_seconds=parent['timeout_seconds'])
    results = local('evals/results', 'evals')
    results.mkdir(mode=0o700, parents=True, exist_ok=True)
    local('evals/outputs', 'evals').mkdir(mode=0o700, parents=True, exist_ok=True)
    round_dir = local(ROUND_DIR, 'evals/outputs'); round_dir.mkdir(mode=0o700)
    r.private_write(round_dir / 'approval.json', approval)
    budget = Budget(); stop = 'completed'; finished = []
    for label in ORDER:
        m = manifests[label]; directory = local('evals/outputs/' + label, 'evals/outputs')
        directory.mkdir(mode=0o700); (directory / 'working').mkdir(mode=0o700)
        if label == 'final_v1': (directory / 'sealed').mkdir(mode=0o700)
        r.private_write(directory / 'inputs.json', {'manifest': m, 'cases': cases[label]})
        tracer = (tracer_factory or tr.configured)(directory / 'trace-status.jsonl')
        r.require(tracer is not None and tracer.ready, 'Tracing provisioning required')
        try:
            with ExitStack() as stack, (round_dir / 'accounting.jsonl').open('a') as ledger:
                os.chmod(round_dir / 'accounting.jsonl', 0o600)
                def writer(path, columns):
                    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    stream = stack.enter_context(os.fdopen(fd, 'w', newline=''))
                    w = csv.DictWriter(stream, fieldnames=columns); w.writeheader(); stream.flush(); os.fsync(stream.fileno())
                    return w, stream
                regular = writer(results / (label + '.csv'), COLUMNS)
                sealed_csv = writer(results / (label + '_sealed.csv'), COLUMNS) if label == 'final_v1' else None
                sealed_metrics = writer(results / (label + '_sealed_metrics.csv'), r.METRIC_COLUMNS) if label == 'final_v1' else None
                for case, (state, wire) in zip(cases[label], prepared[label]):
                    cid = case['case_id']; sealed = cid in r.SEALED_IDS
                    budget.claim(label)
                    ledger.write(r.dumps({'event': 'claim', 'run_label': label, 'case_id': cid, **budget.record()}) + '\n')
                    ledger.flush(); os.fsync(ledger.fileno())
                    raw = directory / ('sealed' if sealed else 'working') / (cid + '.bin')
                    r.private_write(raw.with_suffix('.claim.json'), {'reserved_usd': str(r.PER_CALL_RESERVATION)})
                    identity = tr.ticket(); start = time.monotonic(); began = datetime.now(timezone.utc)
                    ended = began; response = None; package = None; persistence_failed = False
                    row = dict.fromkeys(COLUMNS, '')
                    row.update(run_label=label, case_id=cid, attempt_no=1, timestamp=began.isoformat(),
                               prompt_file=m['candidate_prompt_file'], prompt_hash=m['candidate_prompt_hash'],
                               candidate_prompt_file=m['candidate_prompt_file'], candidate_prompt_hash=m['candidate_prompt_hash'],
                               snapshot_hash=m['snapshot_hash'], model=m['model'], temperature=0,
                               fix_id='final' if label == 'final_v1' else 'baseline',
                               case_role='sealed' if sealed else 'drift' if label == 'drift_baseline_v1' else 'control' if cid in CONTROLS else 'target',
                               langsmith_trace_id=identity['id'], trace_status='pending')
                    try:
                        try: reply = wire_factory(deepcopy(wire))(deepcopy(wire))
                        finally: ended = datetime.now(timezone.utc)
                        try: r.private_write(raw, reply.body)
                        except OSError: persistence_failed = True; raise
                        row['raw_output_path'] = raw.relative_to(ROOT).as_posix()
                        row['run_status'] = 'transport_error'
                        r.require(reply.status == 200 and not reply.credential_redacted, 'Provider response unusable')
                        row['run_status'] = 'content_fail_unparseable'
                        r.require(not reply.truncated, 'Provider response truncated')
                        response = r.strict_json(reply.body)
                        package = ex.parse_candidate(response, parent['model'])
                        row['linkedin_post'] = r.extract_linkedin(package)
                        row['run_status'] = 'returned'
                    except Exception as error:
                        if not row['run_status']:
                            reason = error.reason if isinstance(error, urllib.error.URLError) else error
                            row['run_status'] = 'timeout' if isinstance(reason, TimeoutError) else 'transport_error'
                        row['error_message'] = 'local_persistence_failed' if persistence_failed else {
                            'timeout': 'provider_timeout', 'transport_error': 'provider_or_transport_failure',
                            'content_fail_unparseable': 'output_cannot_be_parsed_or_extracted'}[row['run_status']]
                    row['latency_ms'] = round((time.monotonic() - start) * 1000, 3)
                    usage = r.cost_fields(response, parent)
                    if usage:
                        a, b, cost = usage; row.update(input_tokens=a, output_tokens=b, cost_usd=str(cost))
                    budget.settle(label, usage[2] if usage else None)
                    # Never semantically inspect or measure sealed content.
                    flags = m1(None, sealed=True) if sealed else m1(package['linkedin']['content'] if package and row['run_status'] == 'returned' else None)
                    row['m1_flags'] = r.dumps(flags)
                    w, stream = sealed_csv if sealed else regular
                    w.writerow(row); stream.flush(); os.fsync(stream.fileno())
                    if sealed:
                        w, stream = sealed_metrics
                        w.writerow({k: row[k] for k in r.METRIC_COLUMNS}); stream.flush(); os.fsync(stream.fileno())
                    elif package is not None and row['run_status'] == 'returned':
                        try: checks = package_checks(package, prepare_package_input(state))
                        except Exception: checks = {'status': 'measurement_failed'}
                        r.private_write(raw.with_suffix('.checks.json'), {'m1': flags, 'formats': checks})
                    try: tracer.submit(identity, row, case, parent, llm_start=began, llm_end=ended)
                    except Exception:
                        try: tracer._event(identity, row, 'trace failed', 'submission_failed')
                        except Exception: pass
                    ledger.write(r.dumps({'event': 'settled', 'run_label': label, 'case_id': cid, **budget.record()}) + '\n')
                    ledger.flush(); os.fsync(ledger.fileno())
                    if persistence_failed: stop = 'local_persistence_failed'; break
                    if usage is None: stop = 'usage_unknown_reservation_retained'; break
        finally:
            try: tracer.close(timeout=10)
            except Exception: pass
        r.private_write(directory / 'summary.json', {'run_label': label, 'calls_made': budget.per_run[label][0], 'stop_reason': stop})
        if stop != 'completed': break
        finished.append(label)
    summary = {'mode': 'live', 'execution_order': list(ORDER), 'completed_runs': finished,
               **budget.record(), 'stop_reason': stop}
    r.private_write(round_dir / 'summary.json', summary)
    return summary


def attempt_rows(label, *, sealed=False):
    r.require(label in ('baseline_v1', *ORDER), 'Invalid report label')
    r.require(not sealed or label in ('baseline_v1', 'final_v1'), 'Sealed drift forbidden')
    suffix = '_sealed_metrics' if sealed else ''
    path = local('evals/results/' + label + suffix + '.csv', 'evals/results')
    return tr.resolved_rows(path, local('evals/outputs/' + label + '/trace-status.jsonl', 'evals/outputs'))


def report():
    """Metrics only: never opens sealed content CSVs or raw responses."""
    working = attempt_rows('final_v1'); sealed = attempt_rows('final_v1', sealed=True)
    drift = attempt_rows('drift_baseline_v1')
    r.require(not r.SEALED_IDS.intersection(x['case_id'] for x in working + drift), 'Invalid working rows')
    r.require(all(x['case_id'] in r.SEALED_IDS for x in sealed), 'Invalid sealed metrics')
    return {'working': metrics(working), 'sealed': metrics(sealed), 'drift': metrics(drift),
            'combined': metrics(working + sealed + drift), 'sealed_content': 'not opened or checked'}


def release_gate(approval, join_path):
    """Explicit later owner release after the working-score join; no auto reveal."""
    parent, manifests, _ = load_round()
    path = local(join_path, 'evals/results'); raw = path.read_bytes(); joined = r.strict_json(raw)
    r.require(approval == {'owner_instruction': 'reveal sealed', 'working_join_sha256': r.sha(raw),
                          'final_prompt_hash': manifests['final_v1']['candidate_prompt_hash']}, 'Separate sealed reveal approval required')
    r.require(joined.get('schema') == 'launchlens-final-working-join-v1' and
              joined.get('status') == 'owner_approved_unblinded' and joined.get('scoring_finished_at') and
              joined.get('dataset_hash') == parent['dataset_sha256'] and
              joined.get('final_prompt_hash') == manifests['final_v1']['candidate_prompt_hash'], 'Working join required')
    r.require(datetime.fromisoformat(joined['scoring_finished_at']).utcoffset() is not None,
              'Scoring finish timezone required')
    source = local('evals/results/final_v1_blind_scores.csv', 'evals/results')
    mapping = local('evals/outputs/final_v1/blind-scoring-mapping.json', 'evals/outputs')
    r.require(r.sha(source.read_bytes()) == joined.get('source_sha256') and
              r.sha(mapping.read_bytes()) == joined.get('mapping_sha256') and
              joined.get('labels') == [f'U{i:03d}' for i in range(1, 52)], 'Working join evidence differs')


def blind_packet(*, sealed=False, approval=None, join_path=None):
    """No automatic packet/reveal during generation; mapping is write-only here."""
    parent, _, cases = load_round()
    if sealed: release_gate(approval, join_path)
    final_cases = {c['case_id']: c for c in cases['final_v1']}
    expected = r.SEALED_IDS if sealed else set(final_cases) - r.SEALED_IDS
    entries = []
    for label in (('baseline_v1', 'final_v1') if sealed else ('baseline_v1', 'final_v1', 'drift_baseline_v1')):
        suffix = '_sealed' if sealed else ''
        with local('evals/results/' + label + suffix + '.csv', 'evals/results').open(newline='') as stream:
            rows = list(csv.DictReader(stream))
        selected = expected if sealed or label != 'drift_baseline_v1' else set(DRIFT_IDS)
        r.require({x['case_id'] for x in rows} == selected and len(rows) == len(selected) and
                  all(x['run_status'] == 'returned' for x in rows), 'Packet requires complete returned attempts')
        entries.extend((label, x) for x in rows)
    seed = secrets.randbits(128); random.Random(seed).shuffle(entries)
    prefix = 'V' if sealed else 'U'; count = 12 if sealed else 51
    r.require(len(entries) == count, 'Packet size differs')
    directory = local('evals/outputs/final_v1', 'evals/outputs')
    stem = 'sealed-blind-scoring' if sealed else 'blind-scoring'
    packet = directory / (stem + '.md'); mapping = directory / (stem + '-mapping.json')
    r.require(not packet.exists() and not mapping.exists(), 'Blind packet already exists')
    lines = ['# Anonymous scoring packet', '', 'Apply the frozen scoring rules; record the scoring-finish time.',
             'Prior baseline exposure limits blinding. Identity and metrics are withheld.', '']
    key = []
    for i, (condition, row) in enumerate(entries, 1):
        label = f'{prefix}{i:03d}'; case = final_cases[row['case_id']]
        lines += ['## ' + label, '', 'PMM note:', case['user_notes'], '', 'Expected behavior:',
                  case['expected_behavior'], '', 'LinkedIn post:', row['linkedin_post'], '',
                  'Scores: contract/citation ___; factual support ___; compliance ___; failure category ___; severity ___', '']
        key.append({'label': label, 'case_id': row['case_id'], 'condition': condition})
    text = ('\n'.join(lines) + '\n').encode()
    r.private_write(packet, text)
    r.private_write(mapping, {'seed': str(seed), 'unblinded': False, 'packet_sha256': r.sha(text), 'rows': key})
    return {'posts': count, 'labels': f'{prefix}001–{prefix}{count:03d}', 'mapping': 'written once; not reopened'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--approval-file')
    args = parser.parse_args(argv)
    try:
        approval = r.strict_json(local(args.approval_file, 'evals/outputs').read_bytes()) if args.live else None
        print(r.dumps(run_round(args.snapshot, live=args.live, approval=approval)))
        return 0
    except Exception:
        print('Final round stopped; no automatic retry or sealed content displayed.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
