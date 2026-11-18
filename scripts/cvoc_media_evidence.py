#!/usr/bin/env python3
"""Read-only synthetic media evidence for a proposed CVOC external operator.

CVOC-ST02 currently accepts only ST30/38/43/44/47 and will REJECT this
schema. This package neither authenticates a course nor grants access to one.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import subprocess

PROTOCOL = 'schumann-cvoc-external-media-v0'
COMPONENT = 'video.synthetic.capture'
MAX_BYTES = 50_000_000
MIN_DURATION = 2.0
MAX_DURATION = 20.0
AUDIO_THRESHOLD_DB = -55.0
VIDEO_VARIANCE_THRESHOLD = 7.0
MAX_REPORT_BYTES = 8_192
REPORT_FIELDS = {
    'protocol', 'component', 'operator_type', 'authorization',
    'source_claim', 'source_verified', 'cvoc_st02_native_verified',
    'cross_component_verified', 'course_authorized', 'input_digest_sha256',
    'media_bytes', 'duration_seconds', 'audio_max_dbfs',
    'video_luma_stdev', 'streams', 'technical_checks_passed',
}
DIGEST = re.compile(r'[0-9a-f]{64}\Z')

class Rejected(ValueError):
    pass


def command(args, *, timeout=45):
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        raise Rejected('media probe failed') from e
    return p.stdout, p.stderr


def media_path(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or p.suffix.lower() != '.mp4':
        raise Rejected('expected a regular .mp4 file, no symlinks')
    size = p.stat().st_size
    if not 20_000 <= size <= MAX_BYTES:
        raise Rejected('MP4 file exceeds bounded size or is empty')
    return p, size


def summarize(mp4):
    mp4, size = media_path(mp4)
    blob, _ = command(['ffprobe', '-v', 'error', '-show_entries',
                       'format=duration:stream=codec_type',
                       '-of', 'json', str(mp4)])
    try:
        details = json.loads(blob)
        duration = float(details['format']['duration'])
        tracks = sorted(s['codec_type'] for s in details['streams'])
    except (KeyError, TypeError, ValueError) as e:
        raise Rejected('malformed ffprobe metadata') from e
    if tracks != ['audio', 'video']:
        raise Rejected('exactly one audio and one video stream required')
    if not math.isfinite(duration) or not MIN_DURATION <= duration <= MAX_DURATION:
        raise Rejected('outside allowed synthetic demo duration')
    _, diagnostic = command(['ffmpeg', '-hide_banner', '-nostdin', '-i', str(mp4),
                             '-map', '0:a:0', '-af', 'volumedetect',
                             '-f', 'null', '-'], timeout=45)
    match = re.search(rb'max_volume:\s*(-?[\d.]+) dB', diagnostic)
    if match is None:
        raise Rejected('audio amplitude unavailable')
    peak = float(match.group(1))
    if not math.isfinite(peak) or peak < AUDIO_THRESHOLD_DB or peak > 1.0:
        raise Rejected('silent or invalid audio signal')
    frame, _ = command(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                        '-nostdin', '-ss', '1', '-i', str(mp4), '-map', '0:v:0',
                        '-vf', 'scale=96:54,format=gray', '-frames:v', '1',
                        '-f', 'rawvideo', '-'], timeout=30)
    if len(frame) != 96 * 54:
        raise Rejected('failed to decode representative frame')
    stdev = statistics.pstdev(frame)
    if stdev < VIDEO_VARIANCE_THRESHOLD:
        raise Rejected('blank or near-uniform representative frame')
    digest = hashlib.sha256()
    with mp4.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(chunk)
    return {
        'protocol': PROTOCOL,
        'component': COMPONENT,
        'operator_type': 'LocalSyntheticMP4 -> UnverifiedMediaEvidence',
        'authorization': 'read-only',
        'source_claim': 'caller-declared-synthetic-only',
        'source_verified': False,
        'cvoc_st02_native_verified': False,
        'cross_component_verified': False,
        'course_authorized': False,
        'input_digest_sha256': digest.hexdigest(),
        'media_bytes': size,
        'duration_seconds': round(duration, 3),
        'audio_max_dbfs': round(peak, 2),
        'video_luma_stdev': round(stdev, 2),
        'streams': ['audio', 'video'],
        'technical_checks_passed': True,
    }


def validate(report, mp4):
    if type(report) is not dict or set(report) != REPORT_FIELDS:
        raise Rejected('unexpected or missing report keys')
    if (report.get('protocol') != PROTOCOL or report.get('component') != COMPONENT or
        report.get('operator_type') != 'LocalSyntheticMP4 -> UnverifiedMediaEvidence' or
        report.get('authorization') != 'read-only' or
        report.get('source_claim') != 'caller-declared-synthetic-only' or
        report.get('source_verified') is not False or
        report.get('cvoc_st02_native_verified') is not False or
        report.get('cross_component_verified') is not False or
        report.get('course_authorized') is not False or
        report.get('technical_checks_passed') is not True or
        report.get('streams') != ['audio', 'video'] or
        not isinstance(report.get('input_digest_sha256'), str) or
        not DIGEST.fullmatch(report['input_digest_sha256']) or
        type(report.get('media_bytes')) is not int or
        type(report.get('duration_seconds')) not in (float, int) or
        type(report.get('audio_max_dbfs')) not in (float, int) or
        type(report.get('video_luma_stdev')) not in (float, int)):
        raise Rejected('report contains unsupported claims or types')
    recomputed = summarize(mp4)
    if report != recomputed:
        raise Rejected('media evidence mismatch; file changed or metadata tampered')
    return {
        'accepted': True,
        'media_technical_checks': True,
        'cvoc_st02_native_verified': False,
        'course_authorized': False,
        'input_digest_sha256': recomputed['input_digest_sha256'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    generate = commands.add_parser('generate')
    generate.add_argument('mp4', type=Path)
    generate.add_argument('report', type=Path)
    verify = commands.add_parser('verify')
    verify.add_argument('mp4', type=Path)
    verify.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'generate':
            if args.report.exists():
                raise Rejected('report exists: refusing to overwrite')
            evidence = summarize(args.mp4)
            encoded = json.dumps(evidence, sort_keys=True, indent=2).encode() + b'\n'
            if len(encoded) > MAX_REPORT_BYTES:
                raise Rejected('report exceeds bounded size')
            args.report.parent.mkdir(parents=True, exist_ok=True)
            with args.report.open('xb') as f:
                f.write(encoded)
            print('SYNTHETIC_EVIDENCE_CREATED', evidence['input_digest_sha256'])
        else:
            if args.report.stat().st_size > MAX_REPORT_BYTES:
                raise Rejected('report too large')
            evidence = json.loads(args.report.read_text(encoding='utf-8'))
            print(json.dumps(validate(evidence, args.mp4), sort_keys=True))
    except (Rejected, OSError, ValueError, TypeError) as exc:
        parser.exit(1, 'REJECTED: ' + str(exc) + '\n')

if __name__ == '__main__':
    main()
