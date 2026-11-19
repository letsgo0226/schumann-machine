#!/usr/bin/env python3
"""Strict, read-only proof-of-concept boundary for two external Schumann operators.

This is NOT CVOC-ST02/ST04 native verification, identity attestation, or
permission to access Microsoft 365, university video or production software.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

REQUEST_PROTOCOL = 'schumann-external-operator-request-v0'
REPORT_PROTOCOL = 'schumann-external-operator-report-v0'
MAX_JSON_BYTES = 8192
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
VERSION = re.compile(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\Z')
KINDS = {
    'windows.compatibility': {
        'platform': 'Windows', 'input_type': 'LocalRunnerEnvironment',
        'output_type': 'UnverifiedWindowsCapabilities', 'fixture': 'local-capability-probe-v1',
    },
    'linux.synthetic_video': {
        'platform': 'Linux', 'input_type': 'LocallyGeneratedSyntheticMP4',
        'output_type': 'UnverifiedSyntheticMediaEvidence', 'fixture': 'generated-av-pattern-v1',
    },
}


class Rejected(ValueError):
    pass


def canonical(obj):
    try:
        result = json.dumps(obj, ensure_ascii=True, sort_keys=True,
                            separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise Rejected('non-canonical JSON value') from exc
    if len(result) > MAX_JSON_BYTES:
        raise Rejected('JSON record exceeds size budget')
    return result


def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def request_for(kind):
    if kind not in KINDS:
        raise Rejected('operator is not allowlisted')
    spec = KINDS[kind]
    return {
        'protocol': REQUEST_PROTOCOL,
        'operator': kind,
        'input_type': spec['input_type'],
        'output_type': spec['output_type'],
        'runner_os': spec['platform'],
        'fixture': spec['fixture'],
        'authorization': 'synthetic-read-only',
        'execution_budget': 1,
    }


def validate_request(req):
    if type(req) is not dict or type(req.get('operator')) is not str:
        raise Rejected('request must be a well-typed object')
    expected = request_for(req['operator'])
    if req != expected or any(type(req[k]) is not type(v) for k, v in expected.items()):
        raise Rejected('request contains unsupported fields, values or authorization')
    return expected


def _valid_result(kind, r):
    if type(r) is not dict:
        raise Rejected('result must be an object')
    if kind == 'windows.compatibility':
        expected = {'python_version', 'powershell_available',
                    'powerbi_desktop_detected', 'interactive_desktop_verified'}
        if set(r) != expected:
            raise Rejected('Windows result schema mismatch')
        if type(r['python_version']) is not str or not VERSION.fullmatch(r['python_version']):
            raise Rejected('invalid Python version')
        if any(type(r[k]) is not bool for k in expected - {'python_version'}):
            raise Rejected('Windows capability booleans required')
        if r['interactive_desktop_verified'] is not False:
            raise Rejected('GUI session must not be claimed verified')
    elif kind == 'linux.synthetic_video':
        expected = {'media_sha256', 'media_bytes', 'duration_seconds',
                    'audio_peak_dbfs', 'frame_luma_stdev', 'synthetic_only'}
        if set(r) != expected:
            raise Rejected('Linux media result schema mismatch')
        if type(r['media_sha256']) is not str or not HEX64.fullmatch(r['media_sha256']):
            raise Rejected('invalid media SHA-256')
        if type(r['media_bytes']) is not int or not 20_000 <= r['media_bytes'] <= 50_000_000:
            raise Rejected('invalid media size')
        for k in ('duration_seconds', 'audio_peak_dbfs', 'frame_luma_stdev'):
            if type(r[k]) not in (float, int) or not math.isfinite(r[k]):
                raise Rejected('invalid metric')
        if not (2 <= r['duration_seconds'] <= 20 and
                -55 <= r['audio_peak_dbfs'] <= 1 and
                7 <= r['frame_luma_stdev'] <= 128):
            raise Rejected('synthetic media technical bounds failed')
        if r['synthetic_only'] is not True:
            raise Rejected('synthetic-only evidence is required')
    else:
        raise Rejected('operator is not allowlisted')
    return r


def make_report(req, result):
    validate_request(req)
    _valid_result(req['operator'], result)
    report = {
        'protocol': REPORT_PROTOCOL,
        'operator': req['operator'],
        'runner_os': req['runner_os'],
        'request_sha256': sha(req),
        'result_sha256': sha(result),
        'result': result,
        'technical_prototype_only': True,
        'native_cvoc_verified': False,
        'cross_component_verified': False,
        'course_recording_authorized': False,
        'software_compatibility_resolved': False,
        'login_performed': False,
    }
    validate_report(req, report)
    return report


def validate_report(req, report):
    validate_request(req)
    if type(report) is not dict:
        raise Rejected('report must be an object')
    expected_fields = {'protocol', 'operator', 'runner_os', 'request_sha256',
                       'result_sha256', 'result', 'technical_prototype_only',
                       'native_cvoc_verified', 'cross_component_verified',
                       'course_recording_authorized', 'software_compatibility_resolved',
                       'login_performed'}
    if set(report) != expected_fields:
        raise Rejected('unknown or missing report fields')
    if (report['protocol'] != REPORT_PROTOCOL or
            report['operator'] != req['operator'] or
            report['runner_os'] != req['runner_os'] or
            report['technical_prototype_only'] is not True or
            any(report[k] is not False for k in (
                'native_cvoc_verified', 'cross_component_verified',
                'course_recording_authorized', 'software_compatibility_resolved',
                'login_performed'))):
        raise Rejected('unauthorized or unsupported claims')
    _valid_result(req['operator'], report['result'])
    if report['request_sha256'] != sha(req) or report['result_sha256'] != sha(report['result']):
        raise Rejected('request or result digest mismatch')
    canonical(report)
    return {'accepted': True, 'technical_contract_valid': True,
            'native_cvoc_verified': False, 'course_recording_authorized': False,
            'operator': req['operator'], 'report_digest_sha256': sha(report)}


def save_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + '\n')


def verify_files(req_path, report_path):
    if Path(req_path).stat().st_size > MAX_JSON_BYTES or Path(report_path).stat().st_size > MAX_JSON_BYTES:
        raise Rejected('oversized input')
    req = json.loads(Path(req_path).read_text(encoding='utf-8'))
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    return validate_report(req, report)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('request', type=Path)
    cli.add_argument('report', type=Path)
    args = cli.parse_args()
    try:
        print(json.dumps(verify_files(args.request, args.report), sort_keys=True))
    except (OSError, ValueError, TypeError) as exc:
        cli.exit(1, 'REJECTED: ' + str(exc) + '\n')
