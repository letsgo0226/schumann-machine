"""Pure-stdlib offline safety regression tests (run identically on Linux/Windows)."""
from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from operator_contract import (Rejected, canonical, make_report, request_for,
                               validate_request, validate_report, save_new, verify_files)

WINDOWS_RESULT = {
    'python_version': '3.11.9', 'powershell_available': True,
    'powerbi_desktop_detected': False, 'interactive_desktop_verified': False,
}
MEDIA_RESULT = {
    'media_sha256': 'a'*64, 'media_bytes': 100_000,
    'duration_seconds': 3.0, 'audio_peak_dbfs': -20.0,
    'frame_luma_stdev': 31.0, 'synthetic_only': True,
}


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.w = request_for('windows.compatibility')
        self.l = request_for('linux.synthetic_video')

    def test_windows_roundtrip(self):
        r = make_report(self.w, WINDOWS_RESULT)
        self.assertTrue(validate_report(self.w, r)['accepted'])
        self.assertFalse(r['software_compatibility_resolved'])

    def test_linux_roundtrip(self):
        self.assertTrue(validate_report(self.l, make_report(self.l, MEDIA_RESULT))['accepted'])

    def test_cross_os_type_mismatch(self):
        with self.assertRaises(Rejected):
            validate_report(self.l, make_report(self.w, WINDOWS_RESULT))

    def test_unknown_operator(self):
        with self.assertRaises(Rejected): request_for('university.login')

    def test_request_extra_field(self):
        bad = dict(self.w, school_password='example')
        with self.assertRaises(Rejected): validate_request(bad)

    def test_request_unauthorized_budget(self):
        with self.assertRaises(Rejected): validate_request(dict(self.w, execution_budget=2))

    def test_bool_budget_rejected(self):
        with self.assertRaises(Rejected): validate_request(dict(self.w, execution_budget=True))

    def test_rights_escalation(self):
        r = make_report(self.w, WINDOWS_RESULT)
        r['course_recording_authorized'] = True
        with self.assertRaises(Rejected): validate_report(self.w, r)

    def test_native_verification_escalation(self):
        r = make_report(self.w, WINDOWS_RESULT)
        r['native_cvoc_verified'] = True
        with self.assertRaises(Rejected): validate_report(self.w, r)

    def test_cross_verification_escalation(self):
        r = make_report(self.l, MEDIA_RESULT)
        r['cross_component_verified'] = True
        with self.assertRaises(Rejected): validate_report(self.l, r)

    def test_capability_false_claim(self):
        bad = dict(WINDOWS_RESULT, interactive_desktop_verified=True)
        with self.assertRaises(Rejected): make_report(self.w, bad)

    def test_tampered_result_digest(self):
        r = make_report(self.w, WINDOWS_RESULT)
        r['result']['powerbi_desktop_detected'] = True
        with self.assertRaises(Rejected): validate_report(self.w, r)

    def test_bad_synthetic_media(self):
        with self.assertRaises(Rejected): make_report(self.l, dict(MEDIA_RESULT, audio_peak_dbfs=-120.0))

    def test_nan_rejected(self):
        with self.assertRaises(Rejected): canonical({'x': float('nan')})

    def test_unknown_report_field(self):
        r = make_report(self.w, WINDOWS_RESULT)
        r['cookie'] = 'leak'
        with self.assertRaises(Rejected): validate_report(self.w, r)

    def test_files_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            save_new(p/'request.json', self.w)
            save_new(p/'report.json', make_report(self.w, WINDOWS_RESULT))
            self.assertTrue(verify_files(p/'request.json', p/'report.json')['accepted'])
            with self.assertRaises(FileExistsError): save_new(p/'request.json', self.w)

    def test_files_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            save_new(p/'request.json', self.l)
            r=make_report(self.l, MEDIA_RESULT)
            save_new(p/'report.json', r)
            x=json.loads((p/'report.json').read_text())
            x['result']['media_bytes'] += 1
            (p/'report.json').write_text(json.dumps(x))
            with self.assertRaises(Rejected): verify_files(p/'request.json', p/'report.json')


if __name__ == '__main__':
    unittest.main()
