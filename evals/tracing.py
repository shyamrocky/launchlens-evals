"""Evaluation-only, best-effort tracing. No imports read credentials or use network.

Trace bodies contain selected public case data, never the prepared Writer request.
The attempt CSV is immutable; delivery events are appended to a private sidecar.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import csv
import json
import os
from pathlib import Path
from queue import Queue, Full
import re
import time
from threading import Event, Lock, Thread
from uuid import uuid4

PROJECT = 'launchlens-evals'
METADATA = ('run_label', 'case_id', 'prompt_file', 'prompt_hash', 'model',
            'temperature', 'run_status', 'input_tokens', 'output_tokens',
            'cost_usd', 'latency_ms', 'error_message', 'attempt_no')
SAFE_ERRORS = {'', 'provider_timeout', 'provider_or_transport_failure',
               'output_cannot_be_parsed_or_extracted', 'local_persistence_failed'}


def now():
    return datetime.now(timezone.utc)


def clean(value, secrets=()):
    """Sanitize even allowed text; never serialize arbitrary objects or exceptions."""
    if type(value) is dict:
        return {k: clean(v, secrets) for k, v in value.items()
                if not re.search(r'key|secret|password|header|authorization|credential|env', k, re.I)}
    if type(value) is list:
        return [clean(v, secrets) for v in value]
    if type(value) is str:
        for secret in secrets:
            if secret:
                value = value.replace(secret, '[REDACTED]')
        value = re.sub(r'(?i)(?:bearer\s+\S+|(?:authorization|x-api-key)\s*:\s*[^\n]+)', '[REDACTED]', value)
        value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[EMAIL]', value)
        value = re.sub(r'(?:/Users/|/home/|/private/)[^\s]+', '[PRIVATE_PATH]', value)
        return value
    return value if value is None or type(value) in (int, float, bool) else '[OMITTED]'


def client_factory(key):
    # Raw batch ingestion bypasses SDK trace enrichment and implicit batching.
    from langsmith import Client
    from urllib3.util.retry import Retry
    return Client(api_url='https://api.smith.langchain.com', api_key=key,
                  auto_batch_tracing=False, omit_traced_runtime_info=True,
                  retry_config=Retry(total=0), timeout_ms=(2000, 5000),
                  tracing_sampling_rate=1.0, prefer_profile_auth=False)


def ticket():
    return {'id': str(uuid4()), 'child_id': str(uuid4()), 'start': now()}


def trace_records(identity, row, case, manifest, *, secrets=(), llm_start=None, llm_end=None):
    """Only this allowlist is exported, not state, payload, response or CSV paths."""
    ended = now()
    start = identity['start']
    child_start = llm_start or start
    child_end = llm_end or ended
    metadata = {k: row[k] for k in METADATA if k in row}
    metadata['error_message'] = row.get('error_message', '') if row.get('error_message', '') in SAFE_ERRORS else 'operation_failed'
    from evals.measurement import trace_flags
    flags = row.get('m1_flags')
    if type(flags) is str:
        try: flags = json.loads(flags)
        except (ValueError, TypeError): flags = None
    sealed = case.get('sealed', False) or case['case_id'] in {'A-01','E-01','E-06','KF-03','KF-04','N-05'}
    metadata.update(fix_id=row.get('fix_id', 'baseline'),
                    candidate_prompt_file=row.get('candidate_prompt_file') or row.get('prompt_file', ''),
                    candidate_prompt_hash=row.get('candidate_prompt_hash') or row.get('prompt_hash', ''),
                    case_role=row.get('case_role') or ('control' if case['case_id'] in {'N-12','N-14','E-04'} else 'target'),
                    m1_flags=trace_flags(flags,sealed=sealed))
    metadata.update(dataset_version='v1', dataset_hash=manifest['dataset_sha256'],
                    ls_provider='nebius', ls_model_name=manifest['model'],
                    input_capture='public_case_note_only', cost_source='configured_profile_rates')
    for field in ('input_tokens', 'output_tokens'):
        if metadata.get(field) not in ('', None):
            metadata[field] = int(metadata[field])
    if metadata.get('cost_usd') not in ('', None):
        metadata['total_cost'] = float(metadata['cost_usd'])
    if sealed:
        metadata.update(sealed=True, input_capture='sealed_metadata_only')
    inputs = {} if sealed else {'pmm_note': case['user_notes']}
    outputs = {'status': row['run_status']}
    if not sealed:
        outputs['linkedin_post'] = row.get('linkedin_post', '')
    if all(metadata.get(k) not in ('', None) for k in ('input_tokens', 'output_tokens')):
        outputs['usage_metadata'] = {k: metadata[k] for k in ('input_tokens', 'output_tokens')}
        outputs['usage_metadata']['total_tokens'] = metadata['input_tokens'] + metadata['output_tokens']
    root_order = start.strftime('%Y%m%dT%H%M%S%fZ') + identity['id']
    common = {'trace_id': identity['id'], 'session_name': PROJECT,
              'inputs': inputs, 'outputs': outputs, 'extra': {'metadata': metadata},
              'error': metadata['error_message'] or None}
    root = {**common, 'id': identity['id'], 'name': row['run_label'] + ' / ' + row['case_id'],
            'run_type': 'chain', 'start_time': start.isoformat(), 'end_time': ended.isoformat(),
            'dotted_order': root_order}
    child = {**common, 'id': identity['child_id'], 'parent_run_id': identity['id'],
             'name': 'Writer', 'run_type': 'llm', 'start_time': child_start.isoformat(),
             'end_time': child_end.isoformat(),
             'dotted_order': root_order + '.' + child_start.strftime('%Y%m%dT%H%M%S%fZ') + identity['child_id']}
    return clean({'post': [root, child]}, secrets)


class TraceExporter:
    """One queued batch per case, one delivery attempt. Writer never waits on HTTP."""
    def __init__(self, sidecar, *, key, project, secrets=(), factory=client_factory, capacity=16):
        self.sidecar = Path(sidecar)
        self.key = key
        self.secrets = tuple(secrets) + (key,)
        self.factory = factory
        self.ready = bool(key) and project == PROJECT
        self.statuses = {}
        self.queue = Queue(maxsize=capacity)
        self.lock = Lock()
        self.idle = Event()
        self.idle.set()
        fd = os.open(self.sidecar, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        self.worker = Thread(target=self._deliver, name='eval-traces', daemon=True)
        self.worker.start()

    def _event(self, identity, row, status, reason=''):
        # Fixed status/reason vocabulary only. No exception/provider strings.
        event = {'case_id': row['case_id'], 'attempt_no': row['attempt_no'],
                 'langsmith_trace_id': identity['id'], 'trace_status': status,
                 'reason': reason, 'timestamp': now().isoformat()}
        self.statuses[identity['id']] = status
        try:
            with self.lock, self.sidecar.open('a') as stream:
                stream.write(json.dumps(event, separators=(',', ':')) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            self.statuses[identity['id']] = 'trace failed'

    def submit(self, identity, row, case, manifest, *, llm_start=None, llm_end=None):
        if not self.ready:
            self._event(identity, row, 'trace failed', 'configuration_failed')
            return 'trace failed'
        try:
            payload = trace_records(identity, row, case, manifest, secrets=self.secrets,
                                    llm_start=llm_start, llm_end=llm_end)
            self.idle.clear()
            self.queue.put_nowait((identity, deepcopy(row), payload))
            return 'pending'
        except Full:
            self._event(identity, row, 'trace failed', 'queue_full')
        except Exception:
            self._event(identity, row, 'trace failed', 'payload_failed')
        return 'trace failed'

    def _deliver(self):
        client = None
        while True:
            item = self.queue.get()
            if item is None:
                self.queue.task_done()
                return
            identity, row, payload = item
            try:
                if client is None:
                    client = self.factory(self.key)
                response = client.request_with_retries(
                    'POST', '/runs/batch', stop_after_attempt=1,
                    request_kwargs={'data': json.dumps(payload, allow_nan=False).encode(),
                                    'headers': {'Content-Type': 'application/json'}})
                response.close()
                self._event(identity, row, 'delivered')
            except Exception:
                self._event(identity, row, 'trace failed', 'delivery_failed')
            finally:
                self.queue.task_done()
                if self.queue.unfinished_tasks == 0:
                    self.idle.set()

    def wait(self, timeout=10):
        """Optional post-run observer only; never called from Writer execution."""
        deadline = time.monotonic() + timeout
        while self.queue.unfinished_tasks:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(0.01, remaining))
        return True

    def close(self, timeout=0):
        if self.wait(timeout):
            self.queue.put_nowait(None)


def configured(sidecar):
    """Explicit tracing opt-in calls this; environment only, never read .env."""
    return TraceExporter(sidecar, key=os.environ.get('LANGSMITH_API_KEY', ''),
                         project=os.environ.get('LANGSMITH_PROJECT', ''),
                         secrets=(os.environ.get('NEBIUS_API_KEY', ''),))


def resolved_rows(results, sidecar):
    """Join delivery events for reporting without rewriting the attempt CSV."""
    if Path(results).name.endswith('_sealed.csv'):
        raise ValueError('Sealed content reports are forbidden; use the metrics-only file')
    with Path(results).open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    events = {}
    if Path(sidecar).exists():
        with Path(sidecar).open() as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                    if event['trace_status'] in {'delivered', 'trace failed'}:
                        events[event['langsmith_trace_id']] = event['trace_status']
                except (ValueError, KeyError, TypeError):
                    continue  # An interrupted final append is not successful delivery.
    for row in rows:
        row['trace_status'] = events.get(row.get('langsmith_trace_id'), row.get('trace_status') or 'disabled')
    return rows
