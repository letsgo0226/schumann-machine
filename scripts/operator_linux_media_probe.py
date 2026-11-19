#!/usr/bin/env python3
"""Create and probe local ORIGINAL synthetic clip. Never accepts remote URLs."""
import argparse
import json
import platform
from pathlib import Path
import subprocess
from cvoc_media_evidence import summarize, validate as validate_media
from operator_contract import make_report, request_for, save_new


def build_synthetic(path):
    if platform.system() != 'Linux':
        raise RuntimeError('Synthetic media operator only runs on Linux')
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError('refusing to overwrite synthetic clip')
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin', '-n',
        '-f', 'lavfi', '-i', 'testsrc2=size=192x108:rate=10',
        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
        '-t', '3', '-c:v', 'mpeg4', '-q:v', '5', '-c:a', 'aac', '-b:a', '96k',
        str(path),
    ], check=True, timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/linux_operator'))
    args = parser.parse_args()
    request = request_for('linux.synthetic_video')
    path = args.output_dir / 'synthetic.mp4'
    build_synthetic(path)
    evidence = summarize(path)  # existing fail-closed synthetic MP4 technical analyzer
    validate_media(evidence, path)
    result = {
        'media_sha256': evidence['input_digest_sha256'],
        'media_bytes': evidence['media_bytes'],
        'duration_seconds': evidence['duration_seconds'],
        'audio_peak_dbfs': evidence['audio_max_dbfs'],
        'frame_luma_stdev': evidence['video_luma_stdev'],
        'synthetic_only': True,
    }
    report = make_report(request, result)
    save_new(args.output_dir / 'request.json', request)
    save_new(args.output_dir / 'report.json', report)
    print(json.dumps({'status': 'LINUX_SYNTHETIC_MP4_REPORTED',
                      'media_sha256': result['media_sha256'],
                      'native_cvoc_verified': False}, sort_keys=True))


if __name__ == '__main__':
    main()
