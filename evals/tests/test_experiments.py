"""Manifest-bound experiments, independently authored fixtures and blocked sockets."""
from copy import deepcopy
from io import StringIO
import csv
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from evals import experiments as ex
from evals import runner as r
from evals import tracing as tr
import test_runner as fixtures


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        fixtures.RunnerTests.setUp(self)
        original_root = ex.ROOT
        self.source = original_root
        dataset = fixtures.synthetic_dataset()
        dataset_path = self.root/'evals/cases/golden_v1.json'
        dataset_path.parent.mkdir(parents=True)
        dataset_path.write_text(r.dumps(dataset))
        self.snapshot_path = self.root/'synthetic-snapshot.json'
        self.snapshot_path.write_text(r.dumps(self.snapshot))
        parent = dict(self.manifest, dataset_sha256=r.sha(dataset_path.read_bytes()),
                      snapshot_hash=r.sha(self.snapshot_path.read_bytes()))
        parent_path = self.root/'evals/manifest.json';parent_path.write_text(r.dumps(parent))
        self.parent = parent
        for path in [self.root/'evals/prompts',self.root/'evals/experiments']:
            path.mkdir(parents=True)
        (self.root/parent['prompt_file']).write_bytes((original_root/parent['prompt_file']).read_bytes())
        for label,spec in ex.RUNS.items():
            (self.root/spec['file']).write_bytes((original_root/spec['file']).read_bytes())
            value = json.loads((original_root/'evals/experiments'/(label+'.json')).read_bytes())
            value.update(parent_manifest_sha256=r.sha(parent_path.read_bytes()),
                         dataset_sha256=parent['dataset_sha256'],snapshot_hash=parent['snapshot_hash'])
            (self.root/'evals/experiments'/(label+'.json')).write_text(r.dumps(value))
        patcher = patch.object(ex,'ROOT',self.root);patcher.start();self.addCleanup(patcher.stop)

    def path(self,label):return self.root/'evals/experiments'/(label+'.json')

    def authorization(self,label):
        m,_,cases=ex.load_experiment(self.path(label))
        return {'owner_instruction':'run experiment','mode':'experiment','run_label':label,
                'manifest_hash':r.sha(r.dumps(m).encode()),'cases_hash':r.sha(r.dumps(cases).encode()),
                'candidate_prompt_hash':m['candidate_prompt_hash'],'dataset_hash':m['dataset_sha256'],
                'call_cap':m['call_cap'],'reservation_usd':m['reservation_usd'],'tracing_required':True}

    def exporter(self,label,fail=False):
        client=Mock()
        if fail:client.request_with_retries.side_effect=TimeoutError('OFFLINE SYNTHETIC secret exception')
        exporter=tr.TraceExporter(self.root/(label+'-traces.jsonl'),key='OFFLINE_SYNTHETIC_SECRET',
                                 project=tr.PROJECT,factory=Mock(return_value=client),capacity=64)
        self.addCleanup(lambda:exporter.close(timeout=2))
        return exporter,client

    def rows(self,label):
        with (self.root/'evals/results'/(label+'.csv')).open(newline='') as f:return list(csv.DictReader(f))

    def test_all_manifests_exact_caps_roles_and_dry_default(self):
        for label,count in [('f1_v1',21),('f1_v2',21),('f2_v1',9),('f3_v1',9)]:
            with self.subTest(label=label):
                manifest,parent,cases=ex.load_experiment(self.path(label))
                self.assertEqual(len(cases),count)
                self.assertEqual(manifest['case_ids'][-3:],ex.CONTROLS)
                self.assertFalse(r.SEALED_IDS.intersection(manifest['case_ids']))
                with patch.object(tr,'configured') as configured,patch.object(r,'read_selected_keys') as keys:
                    result=ex.run_experiment(self.path(label),self.snapshot_path)
                    self.assertEqual(result['calls_made'],0)
                    self.assertEqual(result['call_cap'],count)
                    self.assertTrue(result['tracing_required'])
                    configured.assert_not_called();keys.assert_not_called()
        self.assertFalse((self.root/'evals/results').exists())

    def test_candidate_parity_only_system_message_and_unchanged_production_guard(self):
        m,parent,cases=ex.load_experiment(self.path('f1_v1'))
        case=cases[0]
        _,base_payload=r.prepare_request(self.snapshot,case['user_notes'],parent)
        baseline=r.wire_request(base_payload,parent)
        _,candidate=ex.prepare_candidate(self.snapshot,case['user_notes'],m,parent)
        self.assertEqual(r.differences(baseline,candidate),{'$.messages[0].content'})
        self.assertEqual(candidate['messages'][1],baseline['messages'][1])
        self.assertEqual(candidate['temperature'],0)
        self.assertEqual(candidate['max_tokens'],8192)
        self.assertEqual(candidate['max_completion_tokens'],8192)
        altered=deepcopy(base_payload);altered['messages'][0]['content']=candidate['messages'][0]['content']
        with self.assertRaisesRegex(r.EvalError,'Production prompt'):
            r.wire_request(altered,parent)
        self.assertEqual(r.load_package_prompt('package_writer'),baseline['messages'][0]['content'])
        envelope=json.loads(fixtures.reply(candidate).body)
        self.assertIn('linkedin',ex.parse_candidate(envelope,parent['model']))
        for change in ('model','finish','role','tool-call','multiple-choices'):
            bad=deepcopy(envelope)
            if change=='model':bad['model']='OFFLINE SYNTHETIC WRONG MODEL'
            elif change=='finish':bad['choices'][0]['finish_reason']='length'
            elif change=='role':bad['choices'][0]['message']['role']='system'
            elif change=='tool-call':bad['choices'][0]['message']['tool_calls']=[{}]
            else:bad['choices'].append(deepcopy(bad['choices'][0]))
            with self.subTest(response_change=change),self.assertRaises(r.EvalError):
                ex.parse_candidate(bad,parent['model'])

    def test_manifest_prompt_settings_selection_and_hash_tampering_refused(self):
        path=self.path('f2_v1');original=json.loads(path.read_bytes())
        changes={'call_cap':10,'tracing_required':False,'automatic_retries':True,'sealed_allowed':True,
                 'temperature':1,'candidate_prompt_hash':'0'*64,'dataset_sha256':'0'*64,
                 'parent_manifest_sha256':'0'*64,'run_label':'final_v1','candidate_prompt_file':'evals/prompts/baseline_v1.txt',
                 'case_ids':['A-01'],'control_ids':['N-01'],'target_ids':['N-05']}
        for key,value in changes.items():
            with self.subTest(field=key):
                bad=deepcopy(original);bad[key]=value;path.write_text(r.dumps(bad))
                with self.assertRaises(r.EvalError):ex.load_experiment(path)
        path.write_text(r.dumps(original))
        candidate=self.root/original['candidate_prompt_file'];candidate.write_bytes(candidate.read_bytes()+b'changed')
        with self.assertRaises(r.EvalError):ex.load_experiment(path)

    def test_f1_v2_exact_manifest_ancestry_parity_and_production_guard(self):
        manifest,parent,cases=ex.load_experiment(self.path('f1_v2'))
        previous,_,_=ex.load_experiment(self.path('f1_v1'))
        self.assertEqual(r.differences(previous,manifest),
                         {'$.run_label','$.candidate_prompt_file','$.candidate_prompt_hash'})
        baseline=(self.root/parent['prompt_file']).read_bytes()
        candidate=(self.root/manifest['candidate_prompt_file']).read_bytes()
        self.assertEqual(r.sha(candidate),'8432c0521345444b07b36b97bcfb350c6b3956dc942e2d48d5877b6a174fc079')
        self.assertEqual(candidate.replace(ex.F1_V2_BLOCK,b'',1),baseline)
        self.assertEqual(candidate,baseline.replace(b'FORMAT TONE POLICY\n',ex.F1_V2_BLOCK+b'FORMAT TONE POLICY\n',1))
        self.assertEqual(r.sha(baseline),'2198dd6d64f5adca13728b6460db14e0bd5e1ab55468534c3994df3ec890b505')
        self.assertEqual(r.load_package_prompt('package_writer'),baseline.decode())
        _,payload=r.prepare_request(self.snapshot,cases[0]['user_notes'],parent)
        original=r.wire_request(payload,parent)
        _,variant=ex.prepare_candidate(self.snapshot,cases[0]['user_notes'],manifest,parent)
        self.assertEqual(r.differences(original,variant),{'$.messages[0].content'})
        payload['messages'][0]['content']=variant['messages'][0]['content']
        with self.assertRaisesRegex(r.EvalError,'Production prompt'):
            r.wire_request(payload,parent)

    def assert_v2_ancestry_rejects_even_with_test_rebound_hash(self, candidate):
        # Synthetic mutation: independently exercise ancestry beyond hash refusal.
        path=self.path('f1_v2'); manifest=json.loads(path.read_bytes())
        (self.root/manifest['candidate_prompt_file']).write_bytes(candidate)
        with self.assertRaises(r.EvalError):ex.load_experiment(path)
        manifest['candidate_prompt_hash']=r.sha(candidate)
        path.write_text(r.dumps(manifest))
        spec=dict(ex.RUNS['f1_v2'],hash=manifest['candidate_prompt_hash'])
        with patch.dict(ex.RUNS,{'f1_v2':spec}),self.assertRaisesRegex(r.EvalError,'ancestry'):
            ex.load_experiment(path)

    def test_f1_v2_wrong_block_refused_independently_of_hash(self):
        manifest,parent,_=ex.load_experiment(self.path('f1_v2'))
        baseline=(self.root/parent['prompt_file']).read_bytes()
        bad_block=ex.F1_V2_BLOCK.replace(b'not assert launch',b'assert launch',1)
        self.assert_v2_ancestry_rejects_even_with_test_rebound_hash(
            baseline.replace(ex.F1_V2_ANCHOR,bad_block+ex.F1_V2_ANCHOR,1))

    def test_f1_v2_correct_block_wrong_position_refused(self):
        _,parent,_=ex.load_experiment(self.path('f1_v2'))
        baseline=(self.root/parent['prompt_file']).read_bytes()
        self.assert_v2_ancestry_rejects_even_with_test_rebound_hash(baseline+ex.F1_V2_BLOCK)

    def test_f1_v2_one_byte_baseline_change_refused(self):
        manifest,_,_=ex.load_experiment(self.path('f1_v2'))
        candidate=(self.root/manifest['candidate_prompt_file']).read_bytes()
        self.assert_v2_ancestry_rejects_even_with_test_rebound_hash(candidate.replace(b'ROLE',b'role',1))

    def test_existing_experiments_keep_append_only_ancestry(self):
        for label in ('f1_v1','f2_v1','f3_v1'):
            with self.subTest(label=label):
                manifest,parent,_=ex.load_experiment(self.path(label))
                baseline=(self.root/parent['prompt_file']).read_bytes()
                candidate=(self.root/manifest['candidate_prompt_file']).read_bytes()
                self.assertTrue(candidate.startswith(baseline))
                suffix=candidate[len(baseline):]
                relocated=baseline.replace(b'FORMAT TONE POLICY\n',suffix+b'FORMAT TONE POLICY\n',1)
                self.assertFalse(ex.approved_ancestry(relocated,baseline,label))
                self.assertFalse(ex.approved_ancestry(baseline,baseline,label))
                self.assertFalse(ex.approved_ancestry(candidate,baseline,'f1_v2'))

    def test_f1_v2_guardrail_tampering_refused(self):
        path=self.path('f1_v2');original=json.loads(path.read_bytes())
        changes={'case_ids':['A-01'],'target_ids':['A-01'],'sealed_allowed':True,
                 'tracing_required':False,'automatic_retries':True,'call_cap':22,
                 'reservation_usd':'9.000000','temperature':1}
        for key,value in changes.items():
            with self.subTest(field=key):
                bad=dict(original);bad[key]=value;path.write_text(r.dumps(bad))
                with self.assertRaises(r.EvalError):ex.load_experiment(path)
        path.write_text(r.dumps(original))
        with patch.object(tr,'configured') as configured,patch.object(r,'read_selected_keys') as keys:
            result=ex.run_experiment(path,self.snapshot_path)
            self.assertEqual(result['calls_made'],0)
            self.assertEqual(result['call_cap'],21)
            self.assertEqual(result['reservation_usd'],'3.096576')
            self.assertTrue(result['tracing_required'])
            configured.assert_not_called();keys.assert_not_called()
        self.assertFalse((self.root/'evals/results').exists())

    def test_authorization_required_before_credentials_or_artifacts(self):
        auth=self.authorization('f2_v1')
        for field,value in [('owner_instruction','run smoke test'),('manifest_hash','0'*64),('cases_hash','0'*64),
                            ('candidate_prompt_hash','0'*64),('call_cap',30),('tracing_required',False)]:
            bad=dict(auth);bad[field]=value
            with self.subTest(field=field),patch.object(r,'read_selected_keys') as keys:
                with self.assertRaises(r.EvalError):
                    ex.run_experiment(self.path('f2_v1'),self.snapshot_path,live=True,approval=bad)
                keys.assert_not_called()
        self.assertFalse((self.root/'evals/results').exists())

    def test_single_attempt_rows_m1_trace_metadata_and_no_overwrite(self):
        label='f3_v1';exporter,client=self.exporter(label)
        def reply(wire):
            value=json.loads(fixtures.reply(wire).body)
            candidate=json.loads(value['choices'][0]['message']['content'])
            from launchlens.linkedin_drafting import CTA
            candidate['linkedin']['content']['hook']=CTA
            candidate['linkedin']['content']['body']='OFFLINE SYNTHETIC #tag'
            value['choices'][0]['message']['content']=r.dumps(candidate)
            return fixtures.WireResponse(200,r.dumps(value).encode(),{})
        provider=fixtures.FakeProvider(reply)
        summary=ex.run_experiment(self.path(label),self.snapshot_path,live=True,approval=self.authorization(label),
                                  wire_factory=provider,tracer=exporter)
        self.assertEqual(summary['calls_made'],9);self.assertEqual(len(provider.calls),9)
        rows=self.rows(label);self.assertEqual(len(rows),9)
        self.assertTrue(all(row['attempt_no']=='1' for row in rows))
        self.assertEqual(sum(row['case_role']=='control' for row in rows),3)
        self.assertTrue(all(row['run_status']=='returned' for row in rows))
        before=(self.root/'evals/results'/(label+'.csv')).read_bytes()
        self.assertTrue(exporter.wait(2))
        for call in client.request_with_retries.call_args_list:
            root,child=json.loads(call.kwargs['request_kwargs']['data'])['post']
            self.assertEqual(child['parent_run_id'],root['id'])
            for trace in [root,child]:
                meta=trace['extra']['metadata']
                self.assertEqual(meta['fix_id'],'F3')
                self.assertEqual(meta['candidate_prompt_hash'],ex.RUNS[label]['hash'])
                self.assertEqual(meta['candidate_prompt_file'],ex.RUNS[label]['file'])
                self.assertEqual(meta['run_label'],label)
                self.assertIn(meta['case_role'],{'target','control'})
                self.assertTrue(meta['m1_flags']['hook']['exact_cta'])
                self.assertTrue(meta['m1_flags']['body']['hashtag'])
                self.assertFalse(meta['m1_flags']['formatting_pass'])
                self.assertIn('pmm_note',trace['inputs']);self.assertIn('linkedin_post',trace['outputs'])
        self.assertEqual((self.root/'evals/results'/(label+'.csv')).read_bytes(),before)
        with self.assertRaises(r.EvalError):
            ex.run_experiment(self.path(label),self.snapshot_path,live=True,approval=self.authorization(label),
                              wire_factory=provider,tracer=exporter)
        self.assertEqual(len(provider.calls),9)

    def test_trace_failure_does_not_block_any_writer_attempt(self):
        label='f1_v1';exporter,client=self.exporter(label,fail=True);provider=fixtures.FakeProvider()
        summary=ex.run_experiment(self.path(label),self.snapshot_path,live=True,approval=self.authorization(label),
                                  wire_factory=provider,tracer=exporter)
        self.assertEqual(summary['calls_made'],21);self.assertEqual(len(provider.calls),21)
        self.assertTrue(exporter.wait(2))
        rows=tr.resolved_rows(self.root/'evals/results'/(label+'.csv'),exporter.sidecar)
        self.assertTrue(all(row['run_status']=='returned' and row['trace_status']=='trace failed' for row in rows))
        self.assertEqual(client.request_with_retries.call_count,21)

    def test_failed_attempts_retained_no_retry_and_unknown_usage_stops(self):
        for label,behavior,status in [
            ('f1_v1',lambda wire:(_ for _ in ()).throw(TimeoutError('OFFLINE SYNTHETIC')),'timeout'),
            ('f2_v1',lambda wire:(_ for _ in ()).throw(ConnectionError('OFFLINE SYNTHETIC')),'transport_error'),
            ('f3_v1',lambda wire:fixtures.reply(wire,content='OFFLINE SYNTHETIC invalid JSON'),'content_fail_unparseable')]:
            exporter,_=self.exporter(label);provider=fixtures.FakeProvider(behavior)
            summary=ex.run_experiment(self.path(label),self.snapshot_path,live=True,approval=self.authorization(label),
                                      wire_factory=provider,tracer=exporter)
            rows=self.rows(label)
            self.assertTrue(all(row['run_status']==status for row in rows))
            self.assertEqual(len(provider.calls),len(rows))
            self.assertTrue(all(json.loads(row['m1_flags'])['status']=='not_evaluated' for row in rows))
            if status in {'timeout','transport_error'}:
                self.assertEqual(len(rows),1)
                self.assertEqual(summary['unknown_cost_reservation_usd'],'0.147456')
                self.assertEqual(summary['stop_reason'],'usage_unknown_reservation_retained')
            else:self.assertEqual(len(rows),9)


if __name__=='__main__':unittest.main()
