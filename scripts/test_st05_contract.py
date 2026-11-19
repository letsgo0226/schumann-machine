"""Read-only ST05 safety checks; full Xvfb browser test runs in Actions."""
import unittest
from st05_browser_av_probe import html, x11


class TestST05Contract(unittest.TestCase):
    def test_data_only(self):
        with self.assertRaises(ValueError):
            html('https://example.org/video.webm')

    def test_data_uri(self):
        page = html('data:video/webm;base64,dGVzdA==')
        self.assertIn('MediaRecorder', page)
        self.assertIn('createMediaElementSource(video)', page)
        self.assertNotIn('fetch(', page)

    def test_x11_address(self):
        self.assertEqual(x11(':99'), ':99+0,0')

    def test_reject_non_x11(self):
        with self.assertRaises(ValueError):
            x11('https://example.org')

    def test_reject_control_characters(self):
        with self.assertRaises(ValueError):
            x11(':99\nanything')

    def test_no_credential_or_remote_url_arguments(self):
        import ast
        from pathlib import Path
        tree=ast.parse(Path(__file__).with_name('st05_browser_av_probe.py').read_text())
        names=[node.args[0].value for node in ast.walk(tree)
               if isinstance(node,ast.Call)
               and isinstance(node.func,ast.Attribute)
               and node.func.attr=='add_argument'
               and node.args and isinstance(node.args[0],ast.Constant)
               and isinstance(node.args[0].value,str)]
        self.assertEqual(names,['--output-dir'])


if __name__ == '__main__':
    unittest.main()
