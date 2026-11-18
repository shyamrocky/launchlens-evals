"""Synthetic final-round regressions; no private saved data, credentials or network."""
from copy import deepcopy
from decimal import Decimal
from io import StringIO
import csv
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from evals import final_round as fr, runner as r, experiments as ex, tracing as tr
import test_runner as fixtures

CANARY = 'OFFLINE_SYNTHETIC_SEALED_CANARY'


class FinalRoundTests(unittest.TestCase):
    def setUp(self):
        fixtures.RunnerTests.setUp(self)
        source = fr.ROOT
        self.snapshot_path = self.root / 'synthetic-snapshot.json'
        self.snapshot_path.write_text(r.dumps(self.snapshot))
        dataset = fixtures.synthetic_dataset()
        for c in dataset['cases']:
            if c['sealed']: c['pmm_note'] = CANARY + ' ' + c['case_id']
        d = self.root / 'evals/cases/golden_v1.json'; d.parent.mkdir(parents=True)
        d.write_text(r.dumps(dataset))
        parent = dict(self.manifest, snapshot_hash=r.sha(self.snapshot_path.read_bytes()), dataset_sha256=r.sha(d.read_bytes()))
        pp = self.root / 'evals/manifest.json'; pp.write_text(r.dumps(parent))
        (self.root / 'evals/prompts').mkdir(); (self.root / 'evals/experiments').mkdir()
        for path, _ in fr.PROMPTS.values():
            (self.root / path).write_bytes((source / path).read_bytes())
        for label in fr.ORDER:
            path = 'evals/experiments/' + label + '.json'
            m = json.loads((source / path).read_bytes())
            m.update(parent_manifest_sha256=r.sha(pp.read_bytes()), snapshot_hash=parent['snapshot_hash'], dataset_sha256=parent['dataset_sha256'])
            (self.root / path).write_text(r.dumps(m))
        for owner, field, value in [(fr,'ROOT',self.root),(ex,'ROOT',self.root),
                                    (fr,'PARENT_HASH',r.sha(pp.read_bytes())),
                                    (fr,'SNAPSHOT_HASH',parent['snapshot_hash']),
                                    (fr,'DATASET_HASH',parent['dataset_sha256'])]:
            p = patch.object(owner,field,value);p.start();self.addCleanup(p.stop)
        self.parent, self.manifests, self.cases = fr.load_round()
        self.auth = fr.authorization(self.parent,self.manifests,self.cases)
        self.fake = fixtures.FakeProvider()
        self.exporters=[];self.clients=[]

    def tracer(self, path):
        client=Mock()
        exporter=tr.TraceExporter(path,key='OFFLINE_SYNTHETIC_SECRET',project=tr.PROJECT,
                                 factory=Mock(return_value=client),capacity=64)
        self.exporters.append(exporter);self.clients.append(client)
        self.addCleanup(lambda:exporter.close(timeout=2))
        return exporter

    def execute(self, provider=None):
        return fr.run_round(self.snapshot_path,live=True,approval=self.auth,
                            wire_factory=provider or self.fake,tracer_factory=self.tracer)

    def rows(self,label,suffix=''):
        with (self.root / ('evals/results/'+label+suffix+'.csv')).open(newline='') as f:
            return list(csv.DictReader(f))

    def test_dry_run_prepares_33_without_writes_keys_or_tracing(self):
        with patch.object(tr,'configured') as tracing,patch.object(r,'read_selected_keys') as keys,patch.object(r,'private_write') as write:
            result=fr.run_round(self.snapshot_path)
            self.assertEqual(result['prepared'],{'drift_baseline_v1':3,'final_v1':30})
            self.assertEqual(result['execution_order'],['drift_baseline_v1','final_v1'])
            self.assertEqual(result['calls_made'],0)
            self.assertEqual(result['combined_call_cap'],33)
            self.assertEqual(result['combined_reservation_usd'],'4.866048')
            tracing.assert_not_called();keys.assert_not_called();write.assert_not_called()
        self.assertFalse((self.root/'evals/outputs').exists())

    def test_request_parity_and_existing_production_checks(self):
        for label in fr.ORDER:
            case=self.cases[label][0]
            _,payload=r.prepare_request(self.snapshot,case['user_notes'],self.parent)
            wire=r.wire_request(payload,self.parent)
            _,candidate=fr.prepare(self.snapshot,case,self.manifests[label],self.parent)
            self.assertEqual(r.differences(candidate,wire),set() if label=='drift_baseline_v1' else {'$.messages[0].content'})
            if label=='final_v1':
                payload['messages'][0]['content']=candidate['messages'][0]['content']
                with self.assertRaisesRegex(r.EvalError,'Production prompt'):r.wire_request(payload,self.parent)
        self.assertNotIn('final_v1',ex.RUNS)
        self.assertEqual(r.SMOKE_CAP,6)
        with self.assertRaises(r.EvalError):
            r.cases_from(self.root/'evals/cases/golden_v1.json',case_ids=['A-01'])

    def test_manifest_guardrails_and_prompt_tampering_refused(self):
        path=self.root/'evals/experiments/final_v1.json';original=path.read_bytes();m=json.loads(original)
        for key,value in {'call_cap':31,'combined_call_cap':34,'reservation_usd':'5','temperature':1,
                          'tracing_required':False,'automatic_retries':True,'sealed_allowed':False,
                          'execution_order':['final_v1','drift_baseline_v1'],'candidate_prompt_hash':'0'*64,
                          'case_ids':m['case_ids'][:-1]}.items():
            with self.subTest(field=key):
                bad=dict(m);bad[key]=value;path.write_text(r.dumps(bad))
                with self.assertRaises(r.EvalError):fr.load_round()
        path.write_bytes(original)
        prompt=self.root/fr.PROMPTS['final_v1'][0];prompt.write_bytes(prompt.read_bytes()+b' ')
        with self.assertRaisesRegex(r.EvalError,'prompt hash'):fr.load_round()

    def test_source_hashes_and_sealed_drift_refused(self):
        p=self.root/'evals/cases/golden_v1.json';original=p.read_bytes();p.write_bytes(original+b' ')
        with self.assertRaisesRegex(r.EvalError,'dataset hash'):fr.load_round()
        p.write_bytes(original)
        p=self.root/'evals/experiments/drift_baseline_v1.json';original_manifest=p.read_bytes();m=json.loads(original_manifest);m['case_ids']=['A-01','E-07','A-02'];p.write_text(r.dumps(m))
        with self.assertRaises(r.EvalError):fr.load_round()
        p.write_bytes(original_manifest)
        self.snapshot_path.write_text('{}')
        with self.assertRaisesRegex(r.EvalError,'Snapshot hash'):fr.run_round(self.snapshot_path)

    def test_authorization_before_artifacts_and_credentials(self):
        bad=deepcopy(self.auth);bad['combined_call_cap']=34
        with patch.object(r,'read_selected_keys') as keys, self.assertRaises(r.EvalError):
            fr.run_round(self.snapshot_path,live=True,approval=bad)
        keys.assert_not_called();self.assertFalse((self.root/'evals/outputs').exists())

    def test_cap_and_reservation_hard_stop_before_dispatch(self):
        budget=fr.Budget()
        for _ in range(3):budget.claim('drift_baseline_v1');budget.settle('drift_baseline_v1',Decimal(0))
        with self.assertRaises(r.EvalError):budget.claim('drift_baseline_v1')
        for _ in range(30):budget.claim('final_v1');budget.settle('final_v1',Decimal(0))
        self.assertEqual(budget.calls,33)
        with self.assertRaises(r.EvalError):budget.claim('final_v1')
        budget=fr.Budget();budget.known=fr.TOTAL_RESERVATION
        with self.assertRaises(r.EvalError):budget.claim('drift_baseline_v1')
        budget=fr.Budget();budget.per_run['final_v1'][1]=Decimal(fr.RESERVATIONS['final_v1'])
        with self.assertRaises(r.EvalError):budget.claim('final_v1')

    def test_order_33_attempts_exclusive_labels_and_durable_rows(self):
        result=self.execute()
        self.assertEqual(result['calls_made'],33);self.assertEqual(result['completed_runs'],list(fr.ORDER))
        self.assertEqual(len(self.fake.calls),33)
        notes=[json.loads(w['messages'][1]['content'])['writer_brief']['user_notes_data_only'] for w in self.fake.calls]
        self.assertEqual(notes[:3],[c['user_notes'] for c in self.cases['drift_baseline_v1']])
        self.assertEqual(notes[3:],[c['user_notes'] for c in self.cases['final_v1']])
        self.assertEqual([x['attempt_no'] for x in self.rows('drift_baseline_v1')],['1']*3)
        self.assertEqual(len(self.rows('final_v1')),24);self.assertEqual(len(self.rows('final_v1','_sealed')),6)
        with self.assertRaisesRegex(r.EvalError,'reserved'):self.execute()
        self.assertEqual(len(self.fake.calls),33)

    def test_sealed_canaries_no_checks_reports_or_trace_content(self):
        def response(wire):
            envelope=json.loads(fixtures.reply(wire).body)
            note=json.loads(wire['messages'][1]['content'])['writer_brief']['user_notes_data_only']
            if CANARY in note:
                p=json.loads(envelope['choices'][0]['message']['content']);p['linkedin']['content']['body']=CANARY
                envelope['choices'][0]['message']['content']=r.dumps(p)
            return fixtures.WireResponse(200,r.dumps(envelope).encode(),{})
        with patch('sys.stdout',new_callable=StringIO) as stdout:
            summary=self.execute(fixtures.FakeProvider(response))
        self.assertNotIn(CANARY,stdout.getvalue()+r.dumps(summary))
        for cid in r.SEALED_IDS:
            self.assertFalse((self.root/'evals/outputs/final_v1/sealed'/(cid+'.checks.json')).exists())
        original=Path.open
        def protected(path,*a,**kw):
            if 'sealed' in path.parts or path.name.endswith('_sealed.csv'):
                raise AssertionError('Reporting opened sealed content')
            return original(path,*a,**kw)
        with patch.object(Path,'open',protected):
            report=fr.report();self.assertNotIn(CANARY,r.dumps(report))
        self.assertEqual(report['sealed']['calls'],6)
        self.assertEqual(report['combined']['calls'],33)
        for client in self.clients:
            for call in client.request_with_retries.call_args_list:
                batch=json.loads(call.kwargs['request_kwargs']['data']);root,child=batch['post']
                self.assertEqual(child['name'],'Writer')
                if root['extra']['metadata']['case_id'] in r.SEALED_IDS:
                    self.assertEqual(root['inputs'],{});self.assertNotIn('linkedin_post',root['outputs'])
                    self.assertNotIn(CANARY,r.dumps(batch))

    def test_unknown_usage_stops_round_without_retry(self):
        def response(wire):
            envelope=json.loads(fixtures.reply(wire).body);envelope.pop('usage')
            return fixtures.WireResponse(200,r.dumps(envelope).encode(),{})
        provider=fixtures.FakeProvider(response);result=self.execute(provider)
        self.assertEqual(len(provider.calls),1);self.assertEqual(result['stop_reason'],'usage_unknown_reservation_retained')
        self.assertEqual(result['unknown_cost_reservation_usd'],'0.147456')
        self.assertEqual(len(self.rows('drift_baseline_v1')),1)
        self.assertFalse((self.root/'evals/results/final_v1.csv').exists())

    def test_failed_timeout_and_unparseable_attempts_retained(self):
        # One failure per isolated synthetic round; no automatic second attempt.
        for status in ('timeout','transport_error','content_fail_unparseable'):
            with self.subTest(status=status):
                def behavior(wire):
                    if status=='timeout':raise TimeoutError('OFFLINE SYNTHETIC')
                    if status=='transport_error':raise OSError('OFFLINE SYNTHETIC')
                    return fixtures.reply(wire,content='not-json')
                provider=fixtures.FakeProvider(behavior)
                result=self.execute(provider)
                rows=self.rows('drift_baseline_v1')
                self.assertEqual(rows[0]['run_status'],status);self.assertEqual(rows[0]['attempt_no'],'1')
                if status!='content_fail_unparseable':self.assertEqual(len(provider.calls),1)
                else:self.assertEqual(len(provider.calls),33)
                # Independent round fixtures rather than any product retry path.
                import shutil
                shutil.rmtree(self.root/'evals/outputs');shutil.rmtree(self.root/'evals/results')

    def test_tracing_delivery_failure_does_not_retry_or_change_writer(self):
        def failing(path):
            exporter=self.tracer(path)
            self.clients[-1].request_with_retries.side_effect=TimeoutError('OFFLINE SYNTHETIC')
            return exporter
        result=fr.run_round(self.snapshot_path,live=True,approval=self.auth,
                            wire_factory=self.fake,tracer_factory=failing)
        self.assertEqual(result['calls_made'],33);self.assertEqual(len(self.fake.calls),33)
        self.assertEqual({x['trace_status'] for x in fr.attempt_rows('final_v1')},{'trace failed'})

    def test_packet_51_and_reveal_requires_working_join(self):
        self.execute()
        baseline=self.root/'evals/results/baseline_v1.csv'
        baseline.write_bytes((self.root/'evals/results/final_v1.csv').read_bytes())
        with self.assertRaises((r.EvalError,TypeError)):fr.blind_packet(sealed=True)
        original=Path.open
        def protected(path,*args,**kwargs):
            mode=args[0] if args else kwargs.get('mode','r')
            if path.name.endswith('-mapping.json') and 'r' in mode:raise AssertionError('Mapping reopened')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',protected):packet=fr.blind_packet()
        self.assertEqual(packet['posts'],51);self.assertEqual(packet['labels'],'U001–U051')
        text=(self.root/'evals/outputs/final_v1/blind-scoring.md').read_text()
        self.assertEqual(text.count('## U'),51)
        with self.assertRaises(r.EvalError):fr.blind_packet()

    def test_sealed_release_requires_join_bindings_then_builds_12_posts(self):
        self.execute()
        for suffix in ('','_sealed'):
            (self.root/('evals/results/baseline_v1'+suffix+'.csv')).write_bytes(
                (self.root/('evals/results/final_v1'+suffix+'.csv')).read_bytes())
        fr.blind_packet()
        mapping=self.root/'evals/outputs/final_v1/blind-scoring-mapping.json'
        source=self.root/'evals/results/final_v1_blind_scores.csv'
        source.write_text('OFFLINE SYNTHETIC owner-approved score source')
        document={'schema':'launchlens-final-working-join-v1','status':'owner_approved_unblinded',
                  'scoring_finished_at':'2026-11-18T12:00:00-08:00',
                  'dataset_hash':self.parent['dataset_sha256'],
                  'final_prompt_hash':fr.PROMPTS['final_v1'][1],
                  'source_sha256':r.sha(source.read_bytes()),'mapping_sha256':r.sha(mapping.read_bytes()),
                  'labels':[f'U{i:03d}' for i in range(1,52)]}
        join='evals/results/synthetic-working-join.json';path=self.root/join
        path.write_text(r.dumps(document))
        approval={'owner_instruction':'reveal sealed','working_join_sha256':r.sha(path.read_bytes()),
                  'final_prompt_hash':fr.PROMPTS['final_v1'][1]}
        with self.assertRaises(r.EvalError):fr.blind_packet(sealed=True,join_path=join,approval={})
        original=source.read_bytes();source.write_text('OFFLINE SYNTHETIC changed source')
        with self.assertRaises(r.EvalError):fr.blind_packet(sealed=True,join_path=join,approval=approval)
        source.write_bytes(original)
        packet=fr.blind_packet(sealed=True,join_path=join,approval=approval)
        self.assertEqual(packet['posts'],12);self.assertEqual(packet['labels'],'V001–V012')
        text=(self.root/'evals/outputs/final_v1/sealed-blind-scoring.md').read_text()
        self.assertEqual(text.count('## V'),12)
        with self.assertRaises(r.EvalError):fr.blind_packet(sealed=True,join_path=join,approval=approval)
