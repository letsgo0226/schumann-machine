"""Offline tests of synthetic MP4 evidence; no secrets, URL or network access."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('cvoc_media_evidence.py')
spec = importlib.util.spec_from_file_location('cvoc_media_evidence', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class TestSyntheticMedia(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.valid = self.make_video('normal.mp4', video='testsrc2=size=192x108:rate=10',
                                     audio='sine=frequency=440:sample_rate=44100')
        self.report = module.summarize(self.valid)

    def make_video(self, name, video, audio):
        output = self.root / name
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                        '-f', 'lavfi', '-i', video, '-f', 'lavfi', '-i', audio,
                        '-t', '3', '-c:v', 'mpeg4', '-q:v', '5',
                        '-c:a', 'aac', '-b:a', '96k', str(output)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=30)
        return output

    def test_valid_evidence(self):
        self.assertTrue(module.validate(self.report, self.valid)['accepted'])
        self.assertFalse(self.report['cvoc_st02_native_verified'])
        self.assertFalse(self.report['course_authorized'])

    def test_tamper_digest(self):
        altered = dict(self.report, input_digest_sha256='0' * 64)
        with self.assertRaises(module.Rejected): module.validate(altered, self.valid)

    def test_claim_escalation(self):
        altered = dict(self.report, course_authorized=True)
        with self.assertRaises(module.Rejected): module.validate(altered, self.valid)

    def test_unknown_component(self):
        altered = dict(self.report, component='st38-sk-ledger')
        with self.assertRaises(module.Rejected): module.validate(altered, self.valid)

    def test_unknown_extra_fields(self):
        altered = dict(self.report, session_cookie='no')
        with self.assertRaises(module.Rejected): module.validate(altered, self.valid)

    def test_changed_media(self):
        with self.valid.open('ab') as f: f.write(b'modified')
        with self.assertRaises(module.Rejected): module.validate(self.report, self.valid)

    def test_silent_audio(self):
        silent = self.make_video('silent.mp4', 'testsrc2=size=192x108:rate=10',
                                 'anullsrc=channel_layout=stereo:sample_rate=44100')
        with self.assertRaises(module.Rejected): module.summarize(silent)

    def test_black_frame(self):
        black = self.make_video('black.mp4', 'color=c=black:size=192x108:rate=10',
                                'sine=frequency=440:sample_rate=44100')
        with self.assertRaises(module.Rejected): module.summarize(black)

    def test_type_rejection(self):
        changed = dict(self.report, media_bytes=True)
        with self.assertRaises(module.Rejected): module.validate(changed, self.valid)

    def test_schema_separate_from_cvoc_st02(self):
        self.assertNotEqual(self.report['protocol'], 'cvoc-integration-v0')
        self.assertNotIn(self.report['component'],
                         {'st30-tape','st38-sk-ledger','st43-pocket','st44-continuity','st47-state'})

if __name__ == '__main__':
    unittest.main()
