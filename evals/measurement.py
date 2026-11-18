"""M1: versioned, deterministic measurement only; no repair or admission decision."""
import re

from launchlens.linkedin_drafting import CTA

VERSION = 'm1-v2-hook-body'
FIELDS = ('hook', 'body')


def m1(content, *, sealed=False):
    if sealed:
        return {'version': VERSION, 'status': 'deferred_sealed'}
    if type(content) is not dict or any(type(content.get(field)) is not str for field in FIELDS):
        return {'version': VERSION, 'status': 'not_evaluated'}
    result = {'version': VERSION, 'status': 'measured'}
    for field in FIELDS:
        result[field] = {'exact_cta': CTA in content[field],
                         'hashtag': bool(re.search(r'#\w+', content[field]))}
    result['formatting_pass'] = not any(result[field][flag] for field in FIELDS
                                        for flag in ('exact_cta', 'hashtag'))
    return result


def trace_flags(value, *, sealed=False):
    """Allowlist measurement data; never let arbitrary text become trace metadata."""
    if sealed:
        return {'version': VERSION, 'status': 'deferred_sealed'}
    if type(value) is not dict or value.get('version') != VERSION:
        return {'version': VERSION, 'status': 'not_evaluated'}
    if value.get('status') != 'measured':
        return {'version': VERSION, 'status': 'not_evaluated'}
    result = {'version': VERSION, 'status': 'measured'}
    for field in FIELDS:
        item = value.get(field)
        if type(item) is not dict or any(type(item.get(k)) is not bool for k in ('exact_cta', 'hashtag')):
            return {'version': VERSION, 'status': 'not_evaluated'}
        result[field] = {k: item[k] for k in ('exact_cta', 'hashtag')}
    result['formatting_pass'] = not any(result[f][k] for f in FIELDS for k in ('exact_cta', 'hashtag'))
    return result


def package_checks(package, inputs, *, sealed=False):
    """Existing format validators, independently per format; no semantic judging."""
    if sealed:
        return {'status': 'deferred_sealed'}
    from launchlens.content_contracts import validate_draft
    from launchlens.linkedin_drafting import admit_output, evidence_records, LINK, FORBIDDEN, draft_require
    from launchlens.package_content import FORMATS, check_field_claims, text_fields
    from launchlens.voice_policy import validate_tone_structure
    records = evidence_records(inputs)
    result = {}
    for name in FORMATS:
        draft = package.get(name) if type(package) is dict else None
        checks = {}
        def shape():
            return validate_draft(draft, format_name=name, evidence_records=records)
        try: shape(); checks['structure_and_reference_validity'] = 'pass'
        except Exception as error:
            checks['structure_and_reference_validity'] = {'result':'fail','diagnostic':getattr(error,'diagnostic',{'rule':'check_failed'})}
            result[name] = checks
            continue
        def admission():
            if name == 'linkedin':
                admit_output(draft, inputs)
                return
            refs = {claim for ref in draft['claim_references'] for claim in ref['claim_ids']}
            draft_require(refs == set(inputs['draft_constraints']['allowed_claim_ids']), 'objective_claim_coverage','claim_references')
            for path, text in text_fields(draft['content']):
                draft_require(not LINK.search(text),'prohibited_link','content.'+path)
                if not (name == 'campaign_brief' and path.startswith('restrictions_and_unknowns.')):
                    draft_require(not FORBIDDEN.search(text),'prohibited_wording','content.'+path)
        operations = {'admission': admission,
                      'field_citation_coverage': lambda: check_field_claims(draft,name),
                      'tone_structure': lambda: validate_tone_structure(draft,name,inputs['tone_policy'],inputs['draft_constraints']['exact_cta'])}
        for key, operation in operations.items():
            try: operation(); checks[key] = 'pass'
            except Exception as error:
                checks[key] = {'result':'fail','diagnostic':getattr(error,'diagnostic',{'rule':'check_failed'})}
        result[name] = checks
    return result


def measure_saved_baseline(root, manifest, snapshot):
    """Explicit Stage b operation; never called by imports or dry runs."""
    from pathlib import Path
    import csv
    import json
    from evals import runner as r
    from evals.scores import working_ids
    from launchlens.package_content import normalize_package, prepare_package_input
    root = Path(root)
    target = root / 'evals/results/baseline_v1_measurements_m1_v2.json'
    r.require(not target.exists(), 'Baseline measurement version already exists')
    with (root/'evals/results/baseline_v1.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    r.require(len(rows) == 24 and {row['case_id'] for row in rows} == working_ids(), 'Invalid baseline working set')
    result = []
    for row in rows:
        cid = row['case_id']
        r.require(cid not in r.SEALED_IDS, 'Sealed baseline measurement forbidden')
        if row['run_status'] != 'returned':
            result.append({'case_id':cid,'m1':m1(None),'formats':{'status':'not_run_output_unavailable'}})
            continue
        path = root / row['raw_output_path']
        r.require(path == root/'evals/outputs/baseline_v1/working'/(cid+'.bin') and not path.is_symlink(),
                  'Invalid working baseline source')
        response = r.strict_json(path.read_bytes())
        package, _ = normalize_package(r.strict_json(response['choices'][0]['message']['content']))
        case = r.cases_from(root/manifest['dataset_file'],case_ids=[cid],expected_hash=manifest['dataset_sha256'])[0]
        state, _ = r.prepare_request(snapshot,case['user_notes'],manifest)
        result.append({'case_id':cid,'m1':m1(package['linkedin']['content']),
                       'formats':package_checks(package,prepare_package_input(state))})
    document = {'schema':'launchlens-working-measurements-v1','run_label':'baseline_v1',
                'measurement_version':VERSION,'rows':result,'sealed':'not opened or checked'}
    r.private_write(target, document)
    return document
