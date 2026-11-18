"""Independent synthetic M1/score fixtures, no real owner data or saved responses."""
from io import StringIO
import csv,json
from pathlib import Path
import unittest
from unittest.mock import Mock,patch

from evals import measurement as m
from evals import scores
from evals import tracing as tr
from evals import runner as r
from launchlens.linkedin_drafting import CTA
import test_runner as fixtures


class MeasurementScoreTests(unittest.TestCase):
    setUp=fixtures.RunnerTests.setUp

    def raw_scores(self):
        rows=[]
        for cid in sorted(scores.working_ids()):
            rows.append({'case_id':cid,'slice':'normal' if cid.startswith('N-') else 'pressure',
                         'contract_citation':'pass','factual_support':'pass','compliance':'pass',
                         'failure_category':'none','severity':'none',
                         'notes':'  OFFLINE SYNTHETIC, “quoted”\nsecond line 🍒  '})
        stream=StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=scores.FIELDS)
        writer.writeheader();writer.writerows(rows)
        return stream.getvalue().encode(),rows

    def test_m1_exact_cta_and_hashtags_in_both_fields(self):
        for field in ('hook','body'):
            for text,key in [(CTA,'exact_cta'),('OFFLINE SYNTHETIC #tag','hashtag'),('#タグ','hashtag')]:
                content={'hook':'Synthetic hook','body':'Synthetic body'};content[field]=text
                result=m.m1(content)
                self.assertEqual(result['version'],m.VERSION)
                self.assertTrue(result[field][key]);self.assertFalse(result['formatting_pass'])
        self.assertTrue(m.m1({'hook':'A question?','body':'Tell us what you think about flavor inspiration?'})['formatting_pass'])
        self.assertTrue(m.m1({'hook':'# alone','body':'No tags'})['formatting_pass'])
        self.assertEqual(m.m1(None)['status'],'not_evaluated')
        self.assertEqual(m.m1({'hook':[],'body':'Synthetic'})['status'],'not_evaluated')
        self.assertEqual(m.m1(Mock(),sealed=True)['status'],'deferred_sealed')

    def test_m1_trace_flags_cannot_smuggle_text_or_sealed_content(self):
        value=m.m1({'hook':CTA,'body':'OFFLINE SYNTHETIC #tag'})
        value['secret']='OFFLINE SYNTHETIC PRIVATE VALUE'
        clean=m.trace_flags(value)
        self.assertNotIn('PRIVATE VALUE',json.dumps(clean))
        self.assertTrue(clean['hook']['exact_cta'])
        value['hook']['exact_cta']='OFFLINE SYNTHETIC PRIVATE VALUE'
        self.assertEqual(m.trace_flags(value)['status'],'not_evaluated')
        self.assertEqual(m.trace_flags(value,sealed=True)['status'],'deferred_sealed')
        row={'run_label':'synthetic','case_id':'A-01','run_status':'returned','model':self.manifest['model'],
             'm1_flags':json.dumps(value),'linkedin_post':'OFFLINE SEALED CANARY','prompt_file':'synthetic',
             'prompt_hash':'synthetic','error_message':''}
        packet=tr.trace_records(tr.ticket(),row,{'case_id':'A-01','sealed':True,'user_notes':'OFFLINE SEALED NOTE'},self.manifest)
        self.assertNotIn('CANARY',json.dumps(packet));self.assertNotIn('SEALED NOTE',json.dumps(packet))
        self.assertEqual(packet['post'][0]['extra']['metadata']['m1_flags']['status'],'deferred_sealed')

    def test_owner_import_preserves_csv_bytes_order_and_every_value(self):
        raw,rows=self.raw_scores();source=self.root/'synthetic-owner.csv';source.write_bytes(raw)
        summary=scores.import_scores(source,root=self.root)
        self.assertTrue(summary['byte_identical_csv']);self.assertTrue(summary['all_field_values_preserved'])
        self.assertFalse(summary['feedback_uploaded'])
        with self.assertRaises(r.EvalError):scores.import_scores(self.root/'.env')
        self.assertEqual((self.root/'evals/results/baseline_v1_owner_scores.csv').read_bytes(),raw)
        doc=json.loads((self.root/'evals/results/baseline_v1_owner_scores.json').read_bytes())
        self.assertEqual(doc['rows'],rows)
        self.assertEqual(doc['fields'],list(scores.FIELDS))
        self.assertEqual(scores.parse_scores(b'\xef\xbb\xbf'+raw),rows)
        self.assertEqual(source.read_bytes(),raw)
        with self.assertRaises(r.EvalError):scores.import_scores(source,root=self.root)

    def test_owner_import_refuses_sealed_duplicates_and_changed_labels(self):
        raw,rows=self.raw_scores()
        for change in ('sealed','duplicate','score','slice','missing'):
            records=[dict(row) for row in rows]
            if change=='sealed':records[0]['case_id']='A-01'
            elif change=='duplicate':records[0]['case_id']=records[1]['case_id']
            elif change=='score':records[0]['compliance']='PASS'
            elif change=='slice':records[0]['slice']='invalid'
            else:records.pop()
            stream=StringIO();writer=csv.DictWriter(stream,fieldnames=scores.FIELDS)
            writer.writeheader();writer.writerows(records)
            with self.subTest(change=change),self.assertRaises(r.EvalError):scores.parse_scores(stream.getvalue().encode())

    def test_four_format_checks_defer_sealed_before_reading_any_content(self):
        self.assertEqual(m.package_checks(Mock(),Mock(),sealed=True),{'status':'deferred_sealed'})
        from launchlens.package_content import prepare_package_input
        result=m.package_checks({},prepare_package_input(self.snapshot))
        self.assertEqual(set(result),{'campaign_brief','linkedin','email','blog','ads'})
        self.assertTrue(all(v['structure_and_reference_validity']['result']=='fail' for v in result.values()))

    def test_four_format_checks_pass_and_isolate_a_single_format_regression(self):
        from copy import deepcopy
        from launchlens.offline_fixtures import package_cases
        from launchlens.package_content import prepare_package_input
        package=package_cases()['initial_package'];inputs=prepare_package_input(self.snapshot)
        checks=m.package_checks(package,inputs)
        self.assertTrue(all(value=='pass' for result in checks.values() for value in result.values()))
        changed=deepcopy(package);changed['email']['content']['cta']='Visit https://example.invalid'
        after=m.package_checks(changed,inputs)
        self.assertEqual(after['email']['admission']['result'],'fail')
        for name in ('campaign_brief','linkedin','blog','ads'):
            self.assertEqual(after[name],checks[name])

    def test_saved_baseline_measurement_uses_only_working_files_and_preserves_attempts(self):
        from copy import deepcopy
        from launchlens.offline_fixtures import package_cases
        dataset=fixtures.synthetic_dataset()
        dataset_path=self.root/'evals/cases/golden_v1.json';dataset_path.parent.mkdir(parents=True)
        dataset_path.write_text(r.dumps(dataset))
        manifest=dict(self.manifest,dataset_sha256=r.sha(dataset_path.read_bytes()))
        results=self.root/'evals/results';results.mkdir()
        raw_dir=self.root/'evals/outputs/baseline_v1/working';raw_dir.mkdir(parents=True)
        path=results/'baseline_v1.csv'
        with path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=r.COLUMNS);writer.writeheader()
            for cid in sorted(scores.working_ids()):
                package=deepcopy(package_cases()['initial_package'])
                if cid=='N-01':package['linkedin']['content']['hook']=CTA
                raw=raw_dir/(cid+'.bin')
                raw.write_text(r.dumps({'choices':[{'message':{'content':r.dumps(package)}}]}))
                row=dict.fromkeys(r.COLUMNS,'');row.update(case_id=cid,run_status='returned',raw_output_path=raw.relative_to(self.root).as_posix())
                writer.writerow(row)
        before=path.read_bytes()
        sealed=results/'baseline_v1_sealed.csv';sealed.write_text('OFFLINE SEALED CANARY')
        original_open=Path.open
        def guard(source,*args,**kwargs):
            if source.name=='baseline_v1_sealed.csv' or 'sealed' in source.parts:
                raise AssertionError('Sealed content touched')
            return original_open(source,*args,**kwargs)
        with patch.object(Path,'open',guard):
            document=m.measure_saved_baseline(self.root,manifest,self.snapshot)
        self.assertEqual(len(document['rows']),24)
        self.assertEqual(sum(not row['m1']['formatting_pass'] for row in document['rows']),1)
        self.assertEqual(path.read_bytes(),before)
        with self.assertRaises(r.EvalError):m.measure_saved_baseline(self.root,manifest,self.snapshot)

    def test_feedback_plan_requires_unblinding_and_preserves_source_labels(self):
        from uuid import uuid4
        raw,rows=self.raw_scores();source=self.root/'synthetic-scores.csv';source.write_bytes(raw)
        document={'schema':'launchlens-owner-scores-v1','run_label':'baseline_v1',
                  'source_sha256':r.sha(raw),'rows':rows}
        attempts=[{'case_id':row['case_id'],'run_label':'baseline_v1','attempt_no':'1',
                   'langsmith_trace_id':str(uuid4()),'trace_status':'delivered'} for row in rows]
        with self.assertRaises(r.EvalError):scores.feedback_plan(document,source,attempts)
        plan=scores.feedback_plan(document,source,attempts,unblinded=True)
        self.assertEqual(len(plan),120)
        self.assertTrue(all(item['stop_after_attempt']==1 for item in plan))
        self.assertEqual(plan[0]['key'],'contract');self.assertEqual(plan[0]['value'],'pass')
        self.assertEqual(plan[0]['score'],1)
        self.assertEqual(plan,scores.feedback_plan(document,source,attempts,unblinded=True))
        self.assertTrue(all('comment' not in item and 'notes' not in item for item in plan))
        self.assertEqual(source.read_bytes(),raw)
        with self.assertRaises(r.EvalError):scores.feedback_plan(document,source,attempts+[{'case_id':'A-01'}],unblinded=True)
        attempts[0]['trace_status']='pending'
        with self.assertRaises(r.EvalError):scores.feedback_plan(document,source,attempts,unblinded=True)


if __name__=='__main__':unittest.main()
