"""Manifest-bound evaluation experiments; production ContentCall is never overridden.

Only the approved three isolated fixes are executable here. Final/drift manifests
and the single final-round release remain separate owner-review steps.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import csv
import json
import os
from pathlib import Path
import time
import urllib.error

from evals import runner as r
from evals import tracing
from evals.measurement import VERSION, m1, package_checks
from launchlens.package_content import normalize_package, prepare_package_input

ROOT = r.ROOT
CONTROLS = ['N-12', 'N-14', 'E-04']
RUNS = {
    'f1_v1': {'fix_id': 'F1', 'file': 'evals/prompts/f1_claim_wording_v1.txt',
              'hash': 'bfee7035633a8cf112c5616f500b079d6424bc3da0bf8375a466dce23ce5117b',
              'targets': ['N-01','N-02','N-03','N-04','N-06','N-09','N-10','N-11','N-13','N-15',
                          'E-02','E-03','E-05','E-08','E-09','KF-01','KF-02','A-02']},
    'f2_v1': {'fix_id': 'F2', 'file': 'evals/prompts/f2_note_direction_v1.txt',
              'hash': 'e516756b5fe2b3d0b485ba506f1eb4a4aabc6332916327faa778012460f9a7d9',
              'targets': ['N-01','N-02','N-03','N-06','N-10','KF-01']},
    'f3_v1': {'fix_id': 'F3', 'file': 'evals/prompts/f3_field_placement_v1.txt',
              'hash': 'bbdc02cd70d8c99d6ab5d49a160d26f60487b61d99464dc3a4e650d22e0332b6',
              'targets': ['N-01','N-07','N-08','E-07','E-09','KF-02']},
}
COLUMNS = r.COLUMNS + ('fix_id', 'candidate_prompt_file', 'candidate_prompt_hash', 'case_role', 'm1_flags')


def local_file(name, directory):
    path = ROOT / name
    r.require(type(name) is str and not Path(name).is_absolute() and not path.is_symlink() and
              path.resolve().is_relative_to((ROOT / directory).resolve()), 'Invalid experiment file location')
    return path


def load_experiment(path):
    path = Path(path)
    r.require(path.suffix == '.json' and not path.name.startswith('.env') and not path.is_symlink() and
              path.resolve().is_relative_to((ROOT / 'evals/experiments').resolve()),
              'Invalid experiment manifest location')
    value = r.strict_json(path.read_bytes())
    r.require(value.get('schema') == 'launchlens-writer-experiment-v1' and value.get('run_label') in RUNS,
              'Unregistered experiment')
    spec = RUNS[value['run_label']]
    r.require(value['fix_id'] == spec['fix_id'] and value['target_ids'] == spec['targets'] and
              value['control_ids'] == CONTROLS and value['case_ids'] == spec['targets'] + CONTROLS,
              'Experiment case selection differs')
    r.require(not r.SEALED_IDS.intersection(value['case_ids']), 'Sealed experiment cases forbidden')
    r.require(type(value['call_cap']) is int and value['call_cap'] == len(value['case_ids']) and
              value['per_call_reservation_usd'] == str(r.PER_CALL_RESERVATION) and
              value['reservation_usd'] == str(r.PER_CALL_RESERVATION * value['call_cap']),
              'Experiment spending bounds differ')
    r.require(value['tracing_required'] is True and value['sealed_allowed'] is False and
              value['automatic_retries'] is False and value['measurement_version'] == VERSION,
              'Experiment guardrails differ')
    r.require(value['parent_manifest_file'] == 'evals/manifest.json', 'Experiment parent differs')
    parent_path = local_file(value['parent_manifest_file'], 'evals')
    r.require(r.sha(parent_path.read_bytes()) == value['parent_manifest_sha256'], 'Parent manifest hash differs')
    parent = r.load_manifest(parent_path)
    for key in ('snapshot_id','snapshot_hash','dataset_file','dataset_sha256','model','temperature',
                'max_tokens','max_completion_tokens','timeout_seconds'):
        r.require(value[key] == parent[key], 'Experiment source or settings differ')
    r.require(value['baseline_prompt_file'] == parent['prompt_file'] and
              value['baseline_prompt_hash'] == parent['prompt_hash'], 'Baseline prompt binding differs')
    r.require(value['candidate_prompt_file'] == spec['file'] and value['candidate_prompt_hash'] == spec['hash'],
              'Candidate prompt not approved')
    candidate = local_file(value['candidate_prompt_file'], 'evals/prompts').read_bytes()
    baseline = local_file(parent['prompt_file'], 'evals/prompts').read_bytes()
    r.require(r.sha(candidate) == value['candidate_prompt_hash'] and candidate.startswith(baseline) and
              candidate != baseline, 'Candidate prompt hash or baseline ancestry differs')
    cases = r.cases_from(local_file(value['dataset_file'], 'evals/cases'),
                        case_ids=value['case_ids'], expected_hash=value['dataset_sha256'])
    return value, parent, cases


def prepare_candidate(snapshot, notes, manifest, parent):
    state, base_payload = r.prepare_request(snapshot, notes, parent)
    base_wire = r.wire_request(base_payload, parent)  # Comparison only, not variant authorization.
    prompt_path = local_file(manifest['candidate_prompt_file'], 'evals/prompts')
    raw = prompt_path.read_bytes()
    r.require(r.sha(raw) == manifest['candidate_prompt_hash'], 'Candidate prompt hash differs')
    wire = deepcopy(base_wire)
    wire['messages'][0]['content'] = raw.decode()
    r.require(r.differences(base_wire, wire) == {'$.messages[0].content'}, 'Experiment request parity differs')
    r.require(len(r.dumps(wire).encode()) <= r.MAX_REQUEST_BYTES, 'Request exceeds size bound')
    return state, wire


def check_authorization(approval, manifest, cases):
    r.require(type(approval) is dict and approval.get('owner_instruction') == 'run experiment' and
              approval.get('mode') == 'experiment' and approval.get('run_label') == manifest['run_label'] and
              approval.get('manifest_hash') == r.sha(r.dumps(manifest).encode()) and
              approval.get('cases_hash') == r.sha(r.dumps(cases).encode()) and
              approval.get('candidate_prompt_hash') == manifest['candidate_prompt_hash'] and
              approval.get('dataset_hash') == manifest['dataset_sha256'] and
              approval.get('call_cap') == manifest['call_cap'] and
              approval.get('reservation_usd') == manifest['reservation_usd'] and
              approval.get('tracing_required') is True, 'Separate matching experiment authorization required')


def parse_candidate(response, model):
    r.require(type(response) is dict and response.get('model') == model and
              type(response.get('choices')) is list and len(response['choices']) == 1,
              'Invalid provider envelope')
    choice = response['choices'][0]; message = choice.get('message', {})
    r.require(choice.get('finish_reason') == 'stop' and type(message) is dict and
              message.get('role') == 'assistant' and type(message.get('content')) is str and
              not message.get('tool_calls'), 'Incomplete or invalid provider output')
    return normalize_package(r.strict_json(message['content']))[0]


def run_experiment(manifest_path, snapshot_path, *, live=False, approval=None,
                   wire_factory=None, tracer=None, wait_seconds=0):
    manifest, parent, cases = load_experiment(manifest_path)
    snapshot = r.load_snapshot(snapshot_path, parent)
    prepared = [prepare_candidate(snapshot, case['user_notes'], manifest, parent) for case in cases]
    label = manifest['run_label']; cap = manifest['call_cap']
    results = ROOT / 'evals/results'; outputs = ROOT / 'evals/outputs'
    run_dir = outputs / label; csv_path = results / (label + '.csv')
    r.require(not csv_path.exists() and not run_dir.exists(), 'Experiment label already reserved; no replay')
    if not live:
        return {'mode': 'dry_run', 'run_label': label, 'fix_id': manifest['fix_id'],
                'cases_prepared': len(prepared), 'calls_made': 0, 'call_cap': cap,
                'reservation_usd': manifest['reservation_usd'], 'tracing_required': True,
                'candidate_prompt_hash': manifest['candidate_prompt_hash']}
    check_authorization(approval, manifest, cases)
    if wire_factory is None:
        # Provisioning validation only. Network failures after dispatch remain best effort.
        r.require(os.environ.get('LANGSMITH_PROJECT') == tracing.PROJECT and
                  len(os.environ.get('LANGSMITH_API_KEY', '')) >= 12 and
                  not any(c.isspace() for c in os.environ.get('LANGSMITH_API_KEY', '')), 'Tracing provisioning required')
        key = r.read_selected_keys({'NEBIUS_API_KEY'})['NEBIUS_API_KEY']
        def wire_factory(wire):
            r.require(key.encode() not in r.dumps(wire).encode(), 'Request contains a credential')
            return r.ProviderHTTP({'provider':'nebius','model_id':parent['model']}, key,
                                  request_validator=lambda candidate: candidate == wire,
                                  timeout_seconds=parent['timeout_seconds'])
    r.require(not results.is_symlink() and not outputs.is_symlink(), 'Private experiment directory is a symlink')
    results.mkdir(parents=True, exist_ok=True, mode=0o700)
    outputs.mkdir(parents=True, exist_ok=True, mode=0o700)
    run_dir.mkdir(mode=0o700)
    (run_dir / 'working').mkdir(mode=0o700)
    r.private_write(run_dir / 'inputs.json', {'manifest':manifest, 'cases':cases, 'retry_of':None})
    r.private_write(run_dir / 'approval.json', approval)
    if tracer is None:
        try: tracer = tracing.configured(run_dir / 'trace-status.jsonl')
        except Exception: tracer = None
    calls = 0; known = Decimal(0); retained = Decimal(0); stop = 'completed'
    fd = os.open(csv_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader(); stream.flush(); os.fsync(stream.fileno())
        for case, (state, wire) in zip(cases, prepared):
            if calls >= cap or known + retained + r.PER_CALL_RESERVATION > Decimal(manifest['reservation_usd']):
                stop = 'cap_reached'; break
            raw_path = run_dir / 'working' / (case['case_id'] + '.bin')
            r.private_write(raw_path.with_suffix('.claim.json'), {'reserved_usd': str(r.PER_CALL_RESERVATION)})
            identity = tracing.ticket()
            row = dict.fromkeys(COLUMNS, '')
            row.update(run_label=label,case_id=case['case_id'],attempt_no=1,
                       timestamp=datetime.now(timezone.utc).isoformat(),snapshot_hash=parent['snapshot_hash'],
                       prompt_file=manifest['candidate_prompt_file'],prompt_hash=manifest['candidate_prompt_hash'],
                       candidate_prompt_file=manifest['candidate_prompt_file'],candidate_prompt_hash=manifest['candidate_prompt_hash'],
                       fix_id=manifest['fix_id'],case_role='control' if case['case_id'] in CONTROLS else 'target',
                       model=parent['model'],temperature=parent['temperature'],langsmith_trace_id=identity['id'],
                       trace_status='pending' if tracer is not None and tracer.ready else 'trace failed')
            response = None; candidate = None; persistence_failed = False
            started = time.monotonic(); llm_start = datetime.now(timezone.utc); llm_end = llm_start
            calls += 1
            try:
                http = wire_factory(deepcopy(wire))
                try:
                    reply = http(deepcopy(wire))
                finally:
                    llm_end = datetime.now(timezone.utc)
                try: r.private_write(raw_path, reply.body)
                except OSError:
                    persistence_failed = True
                    raise
                row['raw_output_path'] = raw_path.relative_to(ROOT).as_posix()
                row['run_status'] = 'transport_error'
                r.require(reply.status == 200 and not reply.credential_redacted, 'Provider response unusable')
                row['run_status'] = 'content_fail_unparseable'
                r.require(not reply.truncated, 'Provider response truncated')
                response = r.strict_json(reply.body)
                candidate = parse_candidate(response, parent['model'])
                row['linkedin_post'] = r.extract_linkedin(candidate)
                row['run_status'] = 'returned'
            except Exception as error:
                reason = error.reason if isinstance(error, urllib.error.URLError) else error
                if not row.get('run_status'):
                    row['run_status'] = 'timeout' if isinstance(reason, TimeoutError) else 'transport_error'
                row['error_message'] = ('local_persistence_failed' if persistence_failed else
                                        {'timeout':'provider_timeout','transport_error':'provider_or_transport_failure',
                                         'content_fail_unparseable':'output_cannot_be_parsed_or_extracted'}[row['run_status']])
            row['latency_ms'] = round((time.monotonic() - started) * 1000, 3)
            measured = r.cost_fields(response, parent)
            if measured:
                inp, out, cost = measured
                row.update(input_tokens=inp,output_tokens=out,cost_usd=str(cost)); known += cost
            else: retained += r.PER_CALL_RESERVATION
            flags = m1(candidate['linkedin']['content']) if row['run_status'] == 'returned' else m1(None)
            row['m1_flags'] = r.dumps(flags)
            writer.writerow(row); stream.flush(); os.fsync(stream.fileno())
            if candidate is not None and row['run_status'] == 'returned':
                try:
                    checks = package_checks(candidate, prepare_package_input(state))
                except Exception:
                    checks = {'status':'measurement_failed'}
                try:
                    r.private_write(raw_path.with_suffix('.checks.json'), {'m1':flags,'formats':checks})
                except OSError:
                    stop = 'local_persistence_failed'
            if tracer is not None:
                try:
                    tracer.submit(identity,row,case,parent,llm_start=llm_start,llm_end=llm_end)
                except Exception:
                    try: tracer._event(identity,row,'trace failed','submission_failed')
                    except Exception: pass
            if persistence_failed or stop == 'local_persistence_failed': stop = 'local_persistence_failed'; break
            if measured is None: stop = 'usage_unknown_reservation_retained'; break
    summary = {'mode':'live','run_label':label,'calls_made':calls,'call_cap':cap,
               'known_cost_usd':str(known),'unknown_cost_reservation_usd':str(retained),'stop_reason':stop}
    r.private_write(run_dir / 'summary.json', summary)
    if tracer is not None and wait_seconds:
        try: tracer.wait(timeout=wait_seconds)
        except Exception: pass
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--approval-file',type=Path)
    args = parser.parse_args(argv)
    try:
        approval = None
        if args.live:
            r.require(args.approval_file is not None and not args.approval_file.name.startswith('.env') and
                      not args.approval_file.is_symlink() and
                      args.approval_file.resolve().is_relative_to((ROOT/'evals/outputs').resolve()),
                      'A private experiment authorization is required')
            approval = r.strict_json(args.approval_file.read_bytes())
        print(r.dumps(run_experiment(args.manifest,args.snapshot,live=args.live,approval=approval,wait_seconds=10)))
        return 0
    except Exception:
        print('Experiment stopped: preflight or execution failed; no automatic retry.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
