#!/usr/bin/env python3
"""Windows hosted-runner capability report; no application launch or login."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil

from operator_contract import make_report, request_for, save_new


def inspect():
    if platform.system() != 'Windows':
        raise RuntimeError('Windows operator requires Windows; refusing to simulate OS')
    candidates = [
        Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Microsoft Power BI Desktop' / 'bin' / 'PBIDesktop.exe',
        Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Microsoft Power BI Desktop' / 'bin' / 'PBIDesktop.exe',
    ]
    return {
        'python_version': platform.python_version(),
        'powershell_available': bool(shutil.which('pwsh') or shutil.which('powershell')),
        'powerbi_desktop_detected': bool(shutil.which('PBIDesktop.exe') or any(p.is_file() for p in candidates)),
        'interactive_desktop_verified': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('artifacts/windows_operator'))
    args = parser.parse_args()
    request = request_for('windows.compatibility')
    report = make_report(request, inspect())
    save_new(args.output_dir / 'request.json', request)
    save_new(args.output_dir / 'report.json', report)
    print(json.dumps({'status': 'WINDOWS_PROBE_REPORTED', 'capabilities': report['result'],
                      'native_cvoc_verified': False}, sort_keys=True))


if __name__ == '__main__':
    main()
