"""Mocked evaluation tests. All fixtures are independently authored or canonical
synthetic fixtures; no saved runs, case notes, credentials or private artifacts.
"""
from copy import deepcopy
import csv
from io import StringIO
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import Mock, patch

from evals import runner as ev
from launchlens.agent_foundation import initial_state
from launchlens.content_review import ContentCall
from launchlens.evidence_payload import storage_fields
from launchlens.launch_checks import evaluate_launch
from launchlens.live_package import LiveTransport, preflight
from launchlens.live_research import dumps
from launchlens.model_context import CSV_TEXT_FIELDS, structured_packet_text
from launchlens.offline_fixtures import ReviewFixtureTools, request
from launchlens.package_content import FORMATS, prepare_call, prepare_package_input, project_package_context
from launchlens.voice_policy import BRAND_POLICY_ID
from launchlens.writer_comparison import WireResponse
from launchlens.writer_context import identity


def synthetic_snapshot():
    req = request('US')
    tools = ReviewFixtureTools()
    state = initial_state(req, 'offline_package', '', BRAND_POLICY_ID)
    state['pmm'] = tools.read_pmm(req)
    state['pmm']['blocks'] = [{'type': 'paragraph', 'content': {'rich_text': [
        {'text': 'OFFLINE SYNTHETIC: guidance is not launch permission.'}]}, 'children': []}]
    context = tools.read_launch(req)
    for row in context['calendar']:
        row['values']['Notes'] = 'OFFLINE SYNTHETIC: planned schedule only.'
    state['launch'] = evaluate_launch(context, req['evaluation_date'])
    found = tools.search('OFFLINE SYNTHETIC claims', 'public_product_facts')
    for row in found['records']:
        packet = row['evidence_payload']
        packet['claim_source_mappings'] = [{field: 'OFFLINE SYNTHETIC' for field in CSV_TEXT_FIELDS}]
        packet['claim_source_mappings'][0]['claim_id'] = packet['unit_id']
        packet['text'] = structured_packet_text(packet)
        row['evidence_sha256'] = storage_fields(packet)['evidence_sha256']
    state['evidence'] = [found]
    inputs = prepare_package_input(state)
    pmm, launch = inputs['research_context']['pmm'], inputs['research_context']['launch']
    policy = {
        'version': 'offline-synthetic-eval', 'pmm_sha256': identity(pmm), 'launch_sha256': identity(launch),
        'pmm_selection': [{'source': 'research_context.pmm.blocks.0.content.rich_text',
                           'purpose': 'Synthetic caveat', 'spans': [[0, len(pmm['blocks'][0]['content']['rich_text'][0]['text']),
                                                                    'Preserve synthetic caveat']]}],
        'evidence_sha256': {r['unit_id']: r['evidence_sha256'] for r in found['records']},
        'segment_selection': {},
        'launch_fields': ['authority', 'decision', 'product_id', 'market_id', 'evaluation_date',
                          'promotional_draft_allowed', 'publishing_allowed', 'conditions', 'notice'],
        'readiness_fields': ['Requirement', 'Status', 'Blocker / Missing Information', 'Last Updated'],
        'material_boundaries': ['OFFLINE SYNTHETIC: never real product evidence.'],
    }
    return state, policy


def synthetic_case(name='synthetic-case'):
    return {'case_id': name, 'slice': 'normal', 'user_notes': 'OFFLINE SYNTHETIC: concise and qualified.',
            'expected_behavior': 'Return extractable synthetic text; this is a wiring fixture.'}


def synthetic_dataset():
    """Schema fixtures authored for tests, never golden notes or saved-run data."""
    cases = []
    for kind, (prefix, count) in ev.CASE_TYPES.items():
        for i in range(1, count + 1):
            cid = f'{prefix}-{i:02d}'
            cases.append({'case_id': cid, 'type': kind,
                          'slice': 'normal' if kind == 'normal' else 'pressure',
                          'intent': 'OFFLINE SYNTHETIC schema fixture.',
                          'pmm_note': f'OFFLINE SYNTHETIC note for {cid}.',
                          'expected_behavior': 'OFFLINE SYNTHETIC: remain inside the contract.',
                          'critical_failures': [], 'sealed': cid in ev.SEALED_IDS})
    return {
        'dataset_version': 'v1', 'status': 'frozen', 'approved_claims': deepcopy(ev.APPROVED_CLAIMS),
        'fixed_cta': "What would you like to know about Cherry Float's flavor inspiration?",
        'hashtag_rule': {'count': 3, 'nonempty': True, 'fixed_values': None,
                         'claim_bearing_hashtags_require_support': True},
        'scoring_rules': {'global_checks_apply_to_every_case': True,
                          'missing_citation_rule': 'OFFLINE SYNTHETIC: missing citation is not automatically critical.',
                          'pass_bars': {'synthetic': True}},
        'sealed_draw': {'seed': 20261115, 'case_ids': sorted(ev.SEALED_IDS)},
        'cases': cases,
    }


def reply(wire, *, content=None, finish='stop'):
    package = {f: {'content': {'fixture': 'OFFLINE SYNTHETIC'}} for f in FORMATS}
    package['linkedin']['content'] = {'hook': 'Synthetic hook', 'body': 'Synthetic body',
                                      'cta': 'Synthetic CTA', 'hashtags': ['#Synthetic']}
    value = {'model': wire['model'], 'choices': [{'finish_reason': finish, 'message': {
        'role': 'assistant', 'content': dumps(package) if content is None else content}}],
        'usage': {'prompt_tokens': 1000, 'completion_tokens': 100, 'total_tokens': 1100}}
    return WireResponse(200, dumps(value).encode(), {})


class FakeProvider:
    def __init__(self, behavior=None):
        self.calls = []
        self.behavior = behavior or reply

    def __call__(self, expected):
        used = False
        def http(wire):
            nonlocal used
            if used or wire != expected:
                raise AssertionError('Synthetic provider reused or request changed')
            used = True
            self.calls.append(deepcopy(wire))
            return self.behavior(wire)
        return http


def approval(manifest, cases, label, cap=1):
    return {'owner_instruction': 'run smoke test', 'run_label': label,
            'manifest_hash': ev.sha(dumps(manifest).encode()), 'cases_hash': ev.sha(dumps(cases).encode()),
            'call_cap': cap, 'reservation_usd': str(ev.PER_CALL_RESERVATION * cap)}


def rows(root, label):
    with (root / 'evals/results' / (label + '.csv')).open(newline='') as stream:
        return list(csv.DictReader(stream))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        # Failure is immediate on any accidental source, provider, or tracing network attempt.
        for target in ['socket.socket.connect', 'socket.socket.connect_ex', 'socket.create_connection',
                       'urllib.request.OpenerDirector.open']:
            blocker = patch(target, side_effect=AssertionError('Mocked test attempted network'))
            mocked = blocker.start()
            self.addCleanup(blocker.stop)
            self.addCleanup(lambda m=mocked: self.assertEqual(m.call_count, 0))
        original = Path.open
        def safe_open(path, *args, **kwargs):
            parts = path.parts
            if path.name == '.env' or path.name.startswith('.env.') or 'workspace' in parts or (
                    'data' in parts and any(p in parts for p in ('private', 'generated'))):
                raise AssertionError('Tests may not access private files')
            return original(path, *args, **kwargs)
        blocker = patch.object(Path, 'open', safe_open)
        blocker.start()
        self.addCleanup(blocker.stop)
        self.snapshot, policy = synthetic_snapshot()
        # Synthetic policy authorizes only synthetic fixture identities. Runtime code
        # and production policy files are unchanged; real projection logic still runs.
        blocker = patch('launchlens.writer_context.load_policy', return_value=policy)
        blocker.start()
        self.addCleanup(blocker.stop)
        self.manifest = ev.load_manifest()
        self.tmp = tempfile.TemporaryDirectory(prefix='launchlens-eval-synthetic-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.case = synthetic_case()

    def execute(self, label, provider, cases=None, cap=1, retry_of=None):
        cases = cases or [self.case]
        return ev.run_evaluation(self.manifest, self.snapshot, cases, label, live=True, call_cap=cap,
                                 approval=approval(self.manifest, cases, label, cap), wire_factory=provider,
                                 storage_root=self.root, retry_of=retry_of)

    def test_request_parity_with_production_and_only_notes_derived_hash_differences(self):
        original = deepcopy(self.snapshot)
        state, payload = ev.prepare_request(self.snapshot, self.case['user_notes'], self.manifest)
        a = prepare_call(self.snapshot, 'package_writer', projector=project_package_context)
        b = prepare_call(state, 'package_writer', projector=project_package_context)
        self.assertEqual(ev.differences(a, b), ev.DERIVED_PATHS | {ev.NOTES_PATH})
        model_a, model_b = deepcopy(a), deepcopy(b)
        model_a.pop('projection_manifest'); model_b.pop('projection_manifest')
        self.assertEqual(ev.differences(model_a, model_b), {
            ev.NOTES_PATH, '$.binding.authoritative_input_sha256'})
        guard = Mock()
        guard.permission = {'request': state['request'],
                            'scope_sha256': preflight(request=state['request'])['scope_sha256']}
        guard.store = None
        guard.claim.return_value = {'sequence': 1}
        production_wires = []
        def wire_factory(model, validator):
            def http(wire):
                self.assertTrue(validator(wire))
                production_wires.append(deepcopy(wire))
                return reply(wire)
            return http
        transport = LiveTransport('package_writer', guard, {'NEBIUS_API_KEY': 'OFFLINE-' + 'X' * 24},
                                  wire_factory=wire_factory)
        ContentCall(transport, stage='package_writer', model_id=ev.MODEL,
                    projector=project_package_context)(state)
        provider = FakeProvider()
        result = self.execute('parity', provider)
        self.assertEqual(provider.calls, production_wires)
        self.assertEqual(provider.calls[0], ev.wire_request(payload, self.manifest))
        self.assertEqual(result['calls_made'], 1)
        self.assertEqual(self.snapshot, original)
        before = set(self.root.rglob('*'))
        dry = ev.run_evaluation(self.manifest, self.snapshot, [self.case], 'dry', storage_root=self.root)
        self.assertEqual(dry['calls_made'], 0)
        self.assertEqual(set(self.root.rglob('*')), before)
        with self.assertRaises(ev.EvalError):
            ev.run_evaluation(self.manifest, self.snapshot, [self.case], 'denied', live=True,
                              wire_factory=FakeProvider(), storage_root=self.root)
        path = self.root / 'synthetic-snapshot.json'
        path.write_text(dumps(self.snapshot))
        with self.assertRaises(ev.EvalError):
            ev.load_snapshot(path, self.manifest)  # Does not match approved snapshot hash.
        wrong = deepcopy(self.manifest); wrong['prompt_hash'] = '0' * 64
        path = self.root / 'wrong-manifest.json'; path.write_text(dumps(wrong))
        with self.assertRaises(ev.EvalError):
            ev.load_manifest(path)
        altered = deepcopy(self.snapshot); altered['pmm']['blocks'][0]['content']['rich_text'][0]['text'] += ' drift'
        with self.assertRaises(Exception):
            ev.prepare_request(altered, self.case['user_notes'], self.manifest)

    def test_one_attempt_per_case_no_retry_one_call_one_row_and_cap(self):
        provider = FakeProvider()
        result = self.execute('once', provider)
        self.assertEqual(len(provider.calls), 1)
        saved = rows(self.root, 'once')
        self.assertEqual(len(saved), 1)
        self.assertEqual(list(saved[0]), list(ev.COLUMNS))
        self.assertEqual(saved[0]['attempt_no'], '1')
        self.assertEqual(saved[0]['run_status'], 'returned')
        self.assertEqual(saved[0]['cost_usd'], '0.0013')
        self.assertEqual(result['estimated_known_cost_usd'], '0.0013')
        self.assertEqual(saved[0]['langsmith_trace_id'], '')
        original = (self.root / 'evals/results/once.csv').read_bytes()
        with self.assertRaises(ev.EvalError):
            self.execute('once', provider)
        self.assertEqual((self.root / 'evals/results/once.csv').read_bytes(), original)
        self.assertEqual(len(provider.calls), 1)
        cases = [synthetic_case(f'synthetic-{i}') for i in range(7)]
        provider = FakeProvider()
        result = self.execute('capped', provider, cases, cap=6)
        self.assertEqual(len(provider.calls), 6)
        self.assertEqual(len(rows(self.root, 'capped')), 6)
        self.assertEqual(result['stop_reason'], 'cap_reached')
        with self.assertRaises(ev.EvalError):
            self.execute('over-cap', FakeProvider(), cases, cap=7)
        with self.assertRaises(ev.EvalError):
            self.execute('duplicate', FakeProvider(), [self.case, self.case])

    def test_failed_attempts_kept_errors_timeouts_unparseable_and_manual_retry(self):
        def transport_error(wire):
            raise OSError('OFFLINE SYNTHETIC exception must never be persisted')
        def timeout(wire):
            raise TimeoutError('OFFLINE SYNTHETIC timeout must never be persisted')
        cases = [
            ('transport', transport_error, 'transport_error', False),
            ('timeout', timeout, 'timeout', False),
            ('invalid-json', lambda wire: reply(wire, content='{'), 'content_fail_unparseable', True),
            ('missing-linkedin', lambda wire: reply(wire, content='{}'), 'content_fail_unparseable', True),
            ('incomplete', lambda wire: reply(wire, finish='length'), 'content_fail_unparseable', True),
        ]
        for label, behavior, status, raw_exists in cases:
            with self.subTest(status=label):
                provider = FakeProvider(behavior)
                result = self.execute(label, provider)
                saved = rows(self.root, label)
                self.assertEqual(len(provider.calls), 1)
                self.assertEqual(len(saved), 1)
                self.assertEqual(saved[0]['run_status'], status)
                self.assertEqual(saved[0]['attempt_no'], '1')
                self.assertEqual(bool(saved[0]['raw_output_path']), raw_exists)
                self.assertNotIn('OFFLINE SYNTHETIC exception', dumps(saved))
                self.assertNotIn('OFFLINE SYNTHETIC timeout', dumps(saved))
                if status in {'transport_error', 'timeout'}:
                    self.assertEqual(saved[0]['cost_usd'], '')
                    self.assertEqual(result['unknown_cost_reservation_usd'], '0.147456')
                    self.assertEqual(result['stop_reason'], 'usage_unknown_reservation_retained')
                else:
                    self.assertEqual(saved[0]['input_tokens'], '1000')
                    self.assertEqual(saved[0]['cost_usd'], '0.0013')
        original = (self.root / 'evals/results/timeout.csv').read_bytes()
        self.execute('manual-retry', FakeProvider(), retry_of='timeout')
        self.assertEqual(rows(self.root, 'manual-retry')[0]['attempt_no'], '2')
        self.assertEqual((self.root / 'evals/results/timeout.csv').read_bytes(), original)
        with self.assertRaises(ev.EvalError):
            self.execute('third-attempt', FakeProvider(), retry_of='timeout')
        with self.assertRaises(ev.EvalError):
            self.execute('retry-content', FakeProvider(), retry_of='invalid-json')


    def test_public_dataset_schema_and_validation(self):
        dataset = synthetic_dataset()
        self.assertEqual(len(ev.validate_dataset(dataset)), 30)
        path = self.root / 'synthetic-dataset.json'
        path.write_text(dumps(dataset))
        self.assertEqual(len(ev.cases_from(path)), 24)
        for issue in ('missing-note', 'missing-rules', 'missing-case', 'duplicate-id',
                      'wrong-type', 'wrong-slice', 'wrong-seed', 'wrong-sealed-flag',
                      'wrong-critical-type', 'empty-intent', 'too-long-note', 'draft-status', 'old-version'):
            with self.subTest(issue=issue):
                bad = deepcopy(dataset)
                if issue == 'draft-status': bad['status'] = 'draft'
                elif issue == 'old-version': bad['dataset_version'] = 'v0'
                elif issue == 'missing-note': del bad['cases'][0]['pmm_note']
                elif issue == 'missing-rules': del bad['scoring_rules']
                elif issue == 'missing-case': bad['cases'].pop()
                elif issue == 'duplicate-id': bad['cases'][1]['case_id'] = bad['cases'][0]['case_id']
                elif issue == 'wrong-type': bad['cases'][0]['type'] = 'edge'
                elif issue == 'wrong-slice': bad['cases'][0]['slice'] = 'pressure'
                elif issue == 'wrong-seed': bad['sealed_draw']['seed'] = 1
                elif issue == 'wrong-sealed-flag': bad['cases'][0]['sealed'] = True
                elif issue == 'wrong-critical-type': bad['cases'][0]['critical_failures'] = 'synthetic'
                elif issue == 'empty-intent': bad['cases'][0]['intent'] = ''
                elif issue == 'too-long-note': bad['cases'][0]['pmm_note'] = 'x' * 1001
                path.write_text(dumps(bad))
                with self.assertRaises(ev.EvalError):
                    ev.cases_from(path)

    def test_pmm_note_mapping_preserves_exact_text_and_request_boundaries(self):
        dataset = synthetic_dataset()
        note = '  OFFLINE SYNTHETIC: preserve “quotes”, punctuation, and 🍒.\nSecond line.  '
        dataset['cases'][0]['pmm_note'] = note
        path = self.root / 'synthetic-dataset.json'
        path.write_text(dumps(dataset))
        selected = ev.cases_from(path, case_ids=['N-01'])
        self.assertEqual(selected[0]['pmm_note'], note)
        self.assertEqual(selected[0]['user_notes'], note)
        self.assertEqual(selected[0]['type'], 'normal')
        self.assertEqual(selected[0]['slice'], 'normal')
        state, payload = ev.prepare_request(self.snapshot, selected[0]['user_notes'], self.manifest)
        model = json.loads(payload['messages'][1]['content'])
        self.assertEqual(state['user_notes'], note)
        self.assertEqual(model['writer_brief']['user_notes_data_only'], note)
        for field in ('case_id', 'type', 'slice', 'intent', 'expected_behavior', 'critical_failures', 'sealed'):
            self.assertNotIn(field, model['writer_brief'])
        before = prepare_call(self.snapshot, 'package_writer', projector=project_package_context)
        after = prepare_call(state, 'package_writer', projector=project_package_context)
        self.assertEqual(ev.differences(before, after), ev.DERIVED_PATHS | {ev.NOTES_PATH})
        self.assertEqual(dataset['cases'][0]['pmm_note'], note)

    def test_smoke_refuses_sealed_ids_and_implicit_selection(self):
        path = self.root / 'synthetic-dataset.json'
        dataset = synthetic_dataset()
        path.write_text(dumps(dataset))
        working = ['N-01', 'N-02', 'E-02', 'KF-01']
        for cid in sorted(ev.SEALED_IDS):
            with self.subTest(sealed_id=cid):
                with self.assertRaisesRegex(ev.EvalError, 'Sealed cases'):
                    ev.cases_from(path, mode='smoke', case_ids=[cid] + working)
        with self.assertRaisesRegex(ev.EvalError, 'explicit working'):
            ev.cases_from(path, mode='smoke')
        with self.assertRaises(ev.EvalError):
            ev.cases_from(path, mode='smoke', case_ids=working)
        with self.assertRaises(ev.EvalError):
            ev.cases_from(path, mode='sealed')
        sealed = next(c for c in dataset['cases'] if c['sealed'])
        internal = dict(sealed, user_notes=sealed['pmm_note'])
        provider = FakeProvider()
        with self.assertRaisesRegex(ev.EvalError, 'Sealed cases'):
            ev.run_evaluation(self.manifest, self.snapshot, [internal], 'sealed-denied',
                              wire_factory=provider, storage_root=self.root)
        self.assertEqual(provider.calls, [])

    def test_explicit_working_ids_preserve_requested_order_and_cli_selection(self):
        path = self.root / 'synthetic-dataset.json'
        path.write_text(dumps(synthetic_dataset()))
        chosen = ['KF-01', 'N-12', 'A-02', 'E-08', 'N-01']
        selected = ev.cases_from(path, mode='smoke', case_ids=chosen)
        self.assertEqual([c['case_id'] for c in selected], chosen)
        self.assertTrue(all(not c['sealed'] for c in selected))
        six = ev.cases_from(path, mode='smoke', case_ids=chosen + ['N-13'])
        self.assertEqual(len(six), 6)
        all_working = ev.cases_from(path)
        self.assertEqual(len(all_working), 24)
        self.assertFalse(ev.SEALED_IDS.intersection(c['case_id'] for c in all_working))
        for invalid in (['N-01', 'N-01'], ['UNKNOWN'], []):
            with self.assertRaises(ev.EvalError):
                ev.cases_from(path, case_ids=invalid)
        manifest = dict(self.manifest, dataset_sha256=ev.sha(path.read_bytes()))
        with patch.object(ev, 'load_manifest', return_value=manifest), \
                patch.object(ev, 'load_snapshot', return_value=self.snapshot), \
                patch.object(ev, 'run_evaluation', wraps=ev.run_evaluation) as run, \
                patch('sys.stdout', new_callable=StringIO) as output:
            status = ev.main(['--snapshot', 'synthetic-unused.json', '--cases', str(path),
                              '--run-label', 'synthetic-cli-selection', '--mode', 'smoke',
                              '--case-ids', *chosen])
            self.assertEqual(status, 0)
            self.assertEqual([c['case_id'] for c in run.call_args.args[2]], chosen)
            self.assertEqual(json.loads(output.getvalue())['calls_made'], 0)

    def test_frozen_dataset_binding_default_selection_and_hash_rejection(self):
        dataset = synthetic_dataset()
        directory = self.root / 'evals/cases'
        directory.mkdir(parents=True)
        path = directory / 'golden_v1.json'
        path.write_text(dumps(dataset))
        manifest = dict(self.manifest, dataset_sha256=ev.sha(path.read_bytes()))
        selected = ['N-01', 'N-12', 'E-07', 'KF-02', 'A-02']
        with patch.object(ev, 'ROOT', self.root), \
                patch.object(ev, 'load_manifest', return_value=manifest), \
                patch.object(ev, 'load_snapshot', return_value=self.snapshot) as snapshot, \
                patch('sys.stdout', new_callable=StringIO) as output:
            args = ['--snapshot', 'synthetic-unused.json', '--run-label', 'synthetic-v1',
                    '--case-ids', *selected]
            self.assertEqual(ev.main(args), 0)
            self.assertEqual(json.loads(output.getvalue())['cases_prepared'], 5)
            self.assertEqual(json.loads(output.getvalue())['call_cap'], 6)
            snapshot.reset_mock()
            path.write_text(dumps(dataset) + '\n')
            self.assertEqual(ev.main(args), 1)
            snapshot.assert_not_called()
        with self.assertRaisesRegex(ev.EvalError, 'dataset hash'):
            ev.cases_from(path, expected_hash=manifest['dataset_sha256'])


if __name__ == '__main__':
    unittest.main()
