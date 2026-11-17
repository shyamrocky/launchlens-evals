"""Baseline isolation tests with synthetic notes, responses and blocked sockets."""
from copy import deepcopy
from decimal import Decimal
from io import StringIO
import csv
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from evals import runner as ev
from evals import tracing as tr
from evals import reporting
import test_runner as fixtures

CANARY = 'OFFLINE_SYNTHETIC_SEALED_CONTENT_CANARY'


class BaselineTests(unittest.TestCase):
    def setUp(self):
        fixtures.RunnerTests.setUp(self)
        dataset = fixtures.synthetic_dataset()
        for case in dataset['cases']:
            if case['sealed']:
                case['pmm_note'] = CANARY + ' input ' + case['case_id']
        path = self.root / 'evals/cases/golden_v1.json'
        path.parent.mkdir(parents=True)
        path.write_text(ev.dumps(dataset))
        self.manifest = dict(self.manifest, dataset_sha256=ev.sha(path.read_bytes()))
        self.cases = ev.cases_from(path, mode='baseline', expected_hash=self.manifest['dataset_sha256'])
        patcher = patch.object(ev, 'ROOT', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def approval(self):
        return {'owner_instruction': 'run baseline', 'mode': 'baseline', 'run_label': 'baseline_v1',
                'manifest_hash': ev.sha(ev.dumps(self.manifest).encode()),
                'cases_hash': ev.sha(ev.dumps(self.cases).encode()), 'call_cap': 30,
                'reservation_usd': '4.423680', 'dataset_hash': self.manifest['dataset_sha256'],
                'sealed_ids': sorted(ev.SEALED_IDS)}

    def exporter(self):
        client = Mock()
        exporter = tr.TraceExporter(self.root / 'synthetic-traces.jsonl', key='OFFLINE_SYNTHETIC_SECRET',
                                    project=tr.PROJECT, factory=Mock(return_value=client), capacity=64)
        self.addCleanup(lambda: exporter.close(timeout=2))
        return exporter, client

    def execute(self, provider=None, tracer=None):
        return ev.run_evaluation(self.manifest, self.snapshot, self.cases, 'baseline_v1', mode='baseline',
                                 live=True, approval=self.approval(), call_cap=30,
                                 wire_factory=provider or fixtures.FakeProvider(), tracer=tracer,
                                 storage_root=self.root)

    def read_rows(self, suffix=''):
        with (self.root / ('evals/results/baseline_v1' + suffix + '.csv')).open(newline='') as f:
            return list(csv.DictReader(f))

    def test_baseline_only_cap_full_selection_hash_and_dry_run(self):
        with patch.object(tr, 'configured') as configured:
            result = ev.run_evaluation(self.manifest, self.snapshot, self.cases, 'baseline_v1', mode='baseline',
                                       storage_root=self.root)
            self.assertEqual(result['call_cap'], 30)
            self.assertEqual(result['cases_prepared'], 30)
            self.assertEqual(result['maximum_reservation_usd'], '4.423680')
            self.assertEqual(result['calls_made'], 0)
            configured.assert_not_called()
        self.assertFalse((self.root / 'evals/results').exists())
        variants = [dict(run_label='other', mode='baseline'), dict(run_label='baseline_v1', mode='working'),
                    dict(run_label='baseline_v1', mode='baseline', call_cap=6),
                    dict(run_label='baseline_v1', mode='baseline', call_cap=31),
                    dict(run_label='baseline_v1', mode='baseline', retry_of='other')]
        for options in variants:
            label = options.pop('run_label')
            with self.subTest(label=label, options=options), self.assertRaises(ev.EvalError):
                ev.run_evaluation(self.manifest, self.snapshot, self.cases, label, storage_root=self.root, **options)
        for cases in (self.cases[:-1], self.cases[::-1], self.cases + [self.cases[0]]):
            with self.assertRaises(ev.EvalError):
                ev.run_evaluation(self.manifest, self.snapshot, cases, 'baseline_v1', mode='baseline')
        altered = deepcopy(self.cases)
        altered[0]['user_notes'] += ' altered'
        with self.assertRaises(ev.EvalError):
            ev.run_evaluation(self.manifest, self.snapshot, altered, 'baseline_v1', mode='baseline')
        path = self.root / self.manifest['dataset_file']
        for kwargs in ({'case_ids': ['N-01'], 'expected_hash': self.manifest['dataset_sha256']}, {}):
            with self.assertRaises(ev.EvalError):
                ev.cases_from(path, mode='baseline', **kwargs)
        path.write_text(path.read_text() + '\n')
        with self.assertRaisesRegex(ev.EvalError, 'hash differs'):
            ev.run_evaluation(self.manifest, self.snapshot, self.cases, 'baseline_v1', mode='baseline')

    def test_sealed_routing_canaries_reports_console_and_metadata_only_traces(self):
        def reply(wire):
            note = json.loads(wire['messages'][1]['content'])['writer_brief']['user_notes_data_only']
            envelope = json.loads(fixtures.reply(wire).body)
            package = json.loads(envelope['choices'][0]['message']['content'])
            package['linkedin']['content']['body'] = CANARY if CANARY in note else 'OFFLINE SYNTHETIC WORKING POST'
            envelope['choices'][0]['message']['content'] = ev.dumps(package)
            return fixtures.WireResponse(200, ev.dumps(envelope).encode(), {})
        provider = fixtures.FakeProvider(reply)
        exporter, client = self.exporter()
        with patch('sys.stdout', new_callable=StringIO) as stdout, patch('sys.stderr', new_callable=StringIO) as stderr:
            summary = self.execute(provider, exporter)
        self.assertNotIn(CANARY, stdout.getvalue() + stderr.getvalue() + ev.dumps(summary))
        self.assertEqual(summary['calls_made'], 30)
        self.assertEqual(len(provider.calls), 30)
        working, sealed = self.read_rows(), self.read_rows('_sealed')
        self.assertEqual(len(working), 24)
        self.assertEqual(len(sealed), 6)
        self.assertFalse(ev.SEALED_IDS.intersection(row['case_id'] for row in working))
        self.assertEqual({row['case_id'] for row in sealed}, ev.SEALED_IDS)
        self.assertTrue(all(CANARY in row['linkedin_post'] for row in sealed))
        self.assertTrue(all(CANARY not in row['linkedin_post'] for row in working))
        self.assertTrue(all('/sealed/' in row['raw_output_path'] for row in sealed))
        self.assertTrue(all('/working/' in row['raw_output_path'] for row in working))
        self.assertEqual(len(self.read_rows('_sealed_metrics')), 6)
        original = (self.root / 'evals/results/baseline_v1.csv').read_bytes()
        self.assertTrue(exporter.wait(2))
        for call in client.request_with_retries.call_args_list:
            batch = json.loads(call.kwargs['request_kwargs']['data'])
            root, child = batch['post']
            cid = root['extra']['metadata']['case_id']
            self.assertEqual(child['name'], 'Writer')
            if cid in ev.SEALED_IDS:
                self.assertNotIn(CANARY, json.dumps(batch))
                for run in (root, child):
                    self.assertEqual(run['inputs'], {})
                    self.assertEqual(set(run['outputs']), {'status', 'usage_metadata'})
                    self.assertEqual(run['extra']['metadata']['input_capture'], 'sealed_metadata_only')
        with self.assertRaisesRegex(ValueError, 'Sealed content reports'):
            tr.resolved_rows(self.root / 'evals/results/baseline_v1_sealed.csv', exporter.sidecar)
        # Reporting cannot touch sealed content even transiently. Metrics-only file is allowed.
        original_open = Path.open
        def guard(path, *args, **kwargs):
            if path.name == 'baseline_v1_sealed.csv' or 'sealed' in path.parts:
                raise AssertionError('Reporter opened sealed content')
            return original_open(path, *args, **kwargs)
        # Link the real synthetic status events to the default report sidecar location.
        sidecar = self.root / 'evals/outputs/baseline_v1/trace-status.jsonl'
        sidecar.write_bytes(exporter.sidecar.read_bytes())
        with patch.object(Path, 'open', guard), \
                patch.object(reporting, 'code_checks', return_value={'synthetic': 'checked'}) as checks:
            report = reporting.baseline_report(self.root, manifest=self.manifest, snapshot=self.snapshot)
        self.assertEqual(checks.call_count, 24)
        self.assertTrue(all(call.args[0]['case_id'] not in ev.SEALED_IDS for call in checks.call_args_list))
        self.assertNotIn(CANARY, json.dumps(report))
        self.assertNotIn('linkedin_post', report['sealed'])
        self.assertEqual(report['sealed']['calls'], 6)
        self.assertEqual(report['totals']['calls'], 30)
        self.assertEqual(report['sealed']['trace_status_counts'], {'delivered': 6})
        self.assertEqual((self.root / 'evals/results/baseline_v1.csv').read_bytes(), original)
        with self.assertRaises(ev.EvalError):
            self.execute(provider, exporter)
        self.assertEqual(len(provider.calls), 30)

    def test_baseline_errors_are_kept_unknown_usage_reserved_and_no_retries(self):
        calls = 0
        def behavior(wire):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ConnectionError('OFFLINE SYNTHETIC')
            if calls == 2:
                raise TimeoutError('OFFLINE SYNTHETIC')
            if calls == 3:
                response = json.loads(fixtures.reply(wire).body)
                response['usage'] = {}
                return fixtures.WireResponse(200, ev.dumps(response).encode(), {})
            if calls == 4:
                return fixtures.reply(wire, content='OFFLINE SYNTHETIC invalid JSON')
            return fixtures.reply(wire)
        exporter, _ = self.exporter()
        provider = fixtures.FakeProvider(behavior)
        summary = self.execute(provider, exporter)
        rows = self.read_rows() + self.read_rows('_sealed')
        self.assertEqual(summary['calls_made'], 30)
        self.assertEqual(len(provider.calls), 30)
        self.assertEqual(len(rows), 30)
        self.assertTrue(all(row['attempt_no'] == '1' for row in rows))
        self.assertEqual(summary['stop_reason'], 'completed')
        self.assertEqual(summary['unknown_cost_reservation_usd'], '0.442368')
        self.assertLessEqual(Decimal(summary['accounted_and_reserved_usd']), Decimal('4.423680'))
        statuses = {row['case_id']: row['run_status'] for row in rows}
        self.assertEqual(statuses['N-01'], 'transport_error')
        self.assertEqual(statuses['N-02'], 'timeout')
        self.assertEqual(statuses['N-04'], 'content_fail_unparseable')
        with self.assertRaisesRegex(ev.EvalError, 'Baseline retries'):
            ev.validate_retry(self.root / 'evals/results', self.root / 'evals/outputs', 'baseline_v1', [], self.manifest)

    def test_baseline_approval_is_separate_and_dry_cli_is_safe(self):
        for field, value in [('owner_instruction', 'run smoke test'), ('mode', 'working'),
                             ('dataset_hash', '0' * 64), ('sealed_ids', []), ('call_cap', 6),
                             ('reservation_usd', '0.884736')]:
            auth = self.approval(); auth[field] = value
            with self.subTest(field=field), self.assertRaises(ev.EvalError):
                ev.check_approval(auth, self.manifest, self.cases, 'baseline_v1', 30, 'baseline')
        with patch.object(ev, 'load_manifest', return_value=self.manifest), \
                patch.object(ev, 'load_snapshot', return_value=self.snapshot), \
                patch.object(tr, 'configured') as configured, \
                patch('sys.stdout', new_callable=StringIO) as output:
            code = ev.main(['--snapshot', 'synthetic-unused.json', '--mode', 'baseline',
                            '--run-label', 'baseline_v1', '--trace'])
            self.assertEqual(code, 0)
            summary = json.loads(output.getvalue())
            self.assertEqual(summary['calls_made'], 0)
            self.assertEqual(summary['cases_prepared'], 30)
            self.assertNotIn(CANARY, output.getvalue())
            configured.assert_not_called()

    def test_smoke_and_other_runs_cannot_access_sealed_or_baseline_cap(self):
        path = self.root / self.manifest['dataset_file']
        for cid in ev.SEALED_IDS:
            with self.assertRaises(ev.EvalError):
                ev.cases_from(path, mode='smoke', case_ids=['N-01', 'N-02', 'N-03', 'N-04', cid])
            case = next(c for c in self.cases if c['case_id'] == cid)
            for sealed in (True, False):
                changed = dict(case, sealed=sealed)
                with self.assertRaises(ev.EvalError):
                    ev.run_evaluation(self.manifest, self.snapshot, [changed], 'synthetic-other')
        with self.assertRaises(ev.EvalError):
            ev.run_evaluation(self.manifest, self.snapshot, [self.cases[0]], 'synthetic-other', call_cap=30)
        dry = ev.run_evaluation(self.manifest, self.snapshot, [self.cases[0]], 'synthetic-other')
        self.assertEqual(dry['call_cap'], 6)

    def test_local_persistence_failure_stops_baseline_without_replay(self):
        exporter, _ = self.exporter()
        provider = fixtures.FakeProvider()
        original = ev.private_write
        def fail_raw(path, data):
            if Path(path).suffix == '.bin':
                raise OSError('OFFLINE SYNTHETIC storage failure')
            return original(path, data)
        with patch.object(ev, 'private_write', side_effect=fail_raw):
            summary = self.execute(provider, exporter)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(summary['calls_made'], 1)
        self.assertEqual(summary['stop_reason'], 'local_persistence_failed')
        self.assertEqual(self.read_rows()[0]['error_message'], 'local_persistence_failed')


if __name__ == '__main__':
    unittest.main()
