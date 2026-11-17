"""Synthetic, socket-blocked tracing regressions. No real credential or saved run."""
from copy import deepcopy
import json
from pathlib import Path
from threading import Event
import time
import unittest
from unittest.mock import Mock, patch

from evals import runner as ev
from evals import tracing as tr
import test_runner as fixtures
from test_runner import FakeProvider, approval, rows


class TraceTests(unittest.TestCase):
    setUp = fixtures.RunnerTests.setUp

    def exporter(self, *, client=None, factory=None, capacity=16, project=tr.PROJECT):
        client = client or Mock()
        factory = factory or Mock(return_value=client)
        exporter = tr.TraceExporter(self.root / ('trace-' + str(time.monotonic_ns()) + '.jsonl'),
                                    key='OFFLINE_SYNTHETIC_TRACE_SECRET', project=project,
                                    secrets=('OFFLINE_SYNTHETIC_PROVIDER_SECRET',),
                                    factory=factory, capacity=capacity)
        self.addCleanup(lambda: exporter.close(timeout=2))
        return exporter, client, factory

    def execute(self, name, exporter=None, provider=None, trace=False):
        return ev.run_evaluation(self.manifest, self.snapshot, [self.case], name,
                                 live=True, call_cap=1, approval=approval(self.manifest, [self.case], name),
                                 wire_factory=provider or FakeProvider(), storage_root=self.root,
                                 tracer=exporter, trace=trace)

    def test_hierarchy_metadata_trace_id_and_append_only_join(self):
        exporter, client, factory = self.exporter()
        provider = FakeProvider()
        self.execute('synthetic-trace', exporter, provider)
        csv_path = self.root / 'evals/results/synthetic-trace.csv'
        original = csv_path.read_bytes()
        row = rows(self.root, 'synthetic-trace')[0]
        self.assertEqual(row['trace_status'], 'pending')
        self.assertTrue(row['langsmith_trace_id'])
        self.assertTrue(exporter.wait(2))
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(client.request_with_retries.call_count, 1)
        args, kwargs = client.request_with_retries.call_args
        self.assertEqual(args, ('POST', '/runs/batch'))
        self.assertEqual(kwargs['stop_after_attempt'], 1)
        payload = json.loads(kwargs['request_kwargs']['data'])
        root, child = payload['post']
        self.assertEqual(root['id'], row['langsmith_trace_id'])
        self.assertEqual(child['parent_run_id'], root['id'])
        self.assertEqual(root['run_type'], 'chain')
        self.assertEqual(child['run_type'], 'llm')
        self.assertEqual(child['name'], 'Writer')
        self.assertEqual(child['trace_id'], root['id'])
        self.assertTrue(child['dotted_order'].startswith(root['dotted_order'] + '.'))
        self.assertLessEqual(child['start_time'], child['end_time'])
        for run in (root, child):
            self.assertEqual(run['session_name'], tr.PROJECT)
            meta = run['extra']['metadata']
            for field in tr.METADATA:
                expected = int(row[field]) if field in ('input_tokens', 'output_tokens') else row[field]
                if field == 'latency_ms':
                    expected = float(expected)
                if field in ('temperature', 'attempt_no'):
                    expected = int(expected)
                self.assertEqual(meta[field], expected, field)
            self.assertEqual(meta['dataset_version'], 'v1')
            self.assertEqual(meta['dataset_hash'], self.manifest['dataset_sha256'])
            self.assertEqual(set(run['inputs']), {'pmm_note'})
            self.assertEqual(set(run['outputs']), {'linkedin_post', 'status', 'usage_metadata'})
            self.assertEqual(run['outputs']['usage_metadata']['input_tokens'], int(row['input_tokens']))
        joined = tr.resolved_rows(csv_path, exporter.sidecar)
        self.assertEqual(joined[0]['trace_status'], 'delivered')
        self.assertEqual(csv_path.read_bytes(), original)
        self.assertEqual(len(provider.calls), 1)

    def test_client_failure_never_changes_writer_or_attempt_rows(self):
        for stage in ('factory', 'delivery'):
            with self.subTest(stage=stage):
                client = Mock()
                factory = Mock(return_value=client)
                if stage == 'factory':
                    factory.side_effect = RuntimeError('OFFLINE_SYNTHETIC_TRACE_SECRET')
                else:
                    client.request_with_retries.side_effect = TimeoutError('OFFLINE_SYNTHETIC_PROVIDER_SECRET')
                exporter, _, _ = self.exporter(client=client, factory=factory)
                provider = FakeProvider()
                self.execute('synthetic-' + stage, exporter, provider)
                csv_path = self.root / ('evals/results/synthetic-' + stage + '.csv')
                original = csv_path.read_bytes()
                self.assertTrue(exporter.wait(2))
                row = tr.resolved_rows(csv_path, exporter.sidecar)[0]
                self.assertEqual(row['run_status'], 'returned')
                self.assertEqual(row['trace_status'], 'trace failed')
                self.assertEqual(len(provider.calls), 1)
                self.assertEqual(factory.call_count, 1)
                self.assertEqual(csv_path.read_bytes(), original)
                events = exporter.sidecar.read_text()
                self.assertNotIn('OFFLINE_SYNTHETIC_TRACE_SECRET', events)
                self.assertNotIn('OFFLINE_SYNTHETIC_PROVIDER_SECRET', events)

    def test_slow_worker_and_queue_pressure_do_not_block_writer(self):
        entered, release = Event(), Event()
        client = Mock()
        def blocked(*args, **kwargs):
            entered.set()
            release.wait(3)
            return Mock()
        client.request_with_retries.side_effect = blocked
        exporter, _, _ = self.exporter(client=client, capacity=1)
        self.addCleanup(release.set)
        provider = FakeProvider()
        self.execute('synthetic-first', exporter, provider)
        self.assertTrue(entered.wait(1))
        self.execute('synthetic-second', exporter, provider)
        self.execute('synthetic-overflow', exporter, provider)
        self.assertFalse(release.is_set())
        self.assertEqual(len(provider.calls), 3)
        csv_path = self.root / 'evals/results/synthetic-overflow.csv'
        self.assertEqual(tr.resolved_rows(csv_path, exporter.sidecar)[0]['trace_status'], 'trace failed')
        self.assertIn('queue_full', exporter.sidecar.read_text())
        release.set()
        self.assertTrue(exporter.wait(2))
        self.assertEqual(client.request_with_retries.call_count, 2)

    def test_payload_allowlist_and_secret_redaction(self):
        identity = tr.ticket()
        row = dict.fromkeys(ev.COLUMNS, '')
        row.update(run_label='synthetic', case_id='N-01', run_status='returned',
                   error_message='', input_tokens=12, output_tokens=5, cost_usd='0.000027',
                   model=self.manifest['model'], temperature=0, latency_ms=10, attempt_no=1,
                   prompt_file=self.manifest['prompt_file'], prompt_hash=self.manifest['prompt_hash'],
                   raw_output_path='OFFLINE_SYNTHETIC_PRIVATE_PATH',
                   linkedin_post='OFFLINE_SYNTHETIC_TRACE_SECRET')
        row['headers'] = {'Authorization': 'OFFLINE_SYNTHETIC_PROVIDER_SECRET'}
        case = deepcopy(self.case)
        case['user_notes'] = 'OFFLINE_SYNTHETIC_PROVIDER_SECRET'
        case['private_snapshot'] = 'OFFLINE_SYNTHETIC_PRIVATE_DATA'
        manifest = dict(self.manifest, private_evidence='OFFLINE_SYNTHETIC_PRIVATE_DATA')
        payload = tr.trace_records(identity, row, case, manifest,
                                   secrets=('OFFLINE_SYNTHETIC_TRACE_SECRET', 'OFFLINE_SYNTHETIC_PROVIDER_SECRET'))
        wire = json.dumps(payload)
        for excluded in ('OFFLINE_SYNTHETIC_TRACE_SECRET', 'OFFLINE_SYNTHETIC_PROVIDER_SECRET',
                         'OFFLINE_SYNTHETIC_PRIVATE_PATH', 'OFFLINE_SYNTHETIC_PRIVATE_DATA',
                         'headers', 'Authorization', 'runtime', 'env'):
            self.assertNotIn(excluded, wire)
        self.assertIn('[REDACTED]', wire)

    def test_configuration_submission_failures_and_dry_run(self):
        exporter, client, _ = self.exporter(project='OFFLINE_SYNTHETIC_WRONG_PROJECT')
        self.execute('synthetic-project', exporter)
        self.assertTrue(exporter.wait(1))
        self.assertEqual(rows(self.root, 'synthetic-project')[0]['trace_status'], 'trace failed')
        client.request_with_retries.assert_not_called()
        with patch.object(tr, 'configured', side_effect=RuntimeError('OFFLINE_SYNTHETIC')):
            self.execute('synthetic-config', trace=True)
        self.assertEqual(rows(self.root, 'synthetic-config')[0]['trace_status'], 'trace failed')
        with patch.object(tr, 'configured') as configured:
            result = ev.run_evaluation(self.manifest, self.snapshot, [self.case], 'synthetic-dry',
                                       trace=True, storage_root=self.root)
            self.assertEqual(result['calls_made'], 0)
            configured.assert_not_called()
        exporter, _, _ = self.exporter()
        with patch.object(exporter, 'submit', side_effect=RuntimeError('OFFLINE_SYNTHETIC')):
            self.execute('synthetic-submit', exporter)
        path = self.root / 'evals/results/synthetic-submit.csv'
        self.assertEqual(tr.resolved_rows(path, exporter.sidecar)[0]['trace_status'], 'trace failed')

    def test_enabled_disabled_wire_parity_and_failed_writer_trace(self):
        first, second = FakeProvider(), FakeProvider()
        self.execute('synthetic-disabled', provider=first)
        exporter, client, _ = self.exporter()
        self.execute('synthetic-enabled', exporter, second)
        self.assertEqual(first.calls, second.calls)
        self.assertEqual(rows(self.root, 'synthetic-disabled')[0]['trace_status'], 'disabled')
        self.assertTrue(exporter.wait(2))
        provider = FakeProvider(behavior=lambda wire: (_ for _ in ()).throw(TimeoutError()))
        self.execute('synthetic-timeout', exporter, provider)
        self.assertTrue(exporter.wait(2))
        row = rows(self.root, 'synthetic-timeout')[0]
        self.assertEqual(row['run_status'], 'timeout')
        root, child = json.loads(client.request_with_retries.call_args.kwargs['request_kwargs']['data'])['post']
        self.assertEqual(child['error'], 'provider_timeout')
        self.assertEqual(root['extra']['metadata']['cost_usd'], '')
        self.assertEqual(len(provider.calls), 1)

    def test_sdk_client_disables_enrichment_batching_and_transport_retries(self):
        with patch('langsmith.Client') as client:
            tr.client_factory('OFFLINE_SYNTHETIC_TRACE_SECRET')
        kwargs = client.call_args.kwargs
        self.assertTrue(kwargs['omit_traced_runtime_info'])
        self.assertFalse(kwargs['auto_batch_tracing'])
        self.assertFalse(kwargs['prefer_profile_auth'])
        self.assertEqual(kwargs['retry_config'].total, 0)
        self.assertEqual(kwargs['timeout_ms'], (2000, 5000))
        self.assertEqual(kwargs['api_url'], 'https://api.smith.langchain.com')


if __name__ == '__main__':
    unittest.main()
