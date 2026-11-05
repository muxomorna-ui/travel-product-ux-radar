import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from prepare_release import prepare


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / '2026-11-03-daily'
        self.src.mkdir()
        self.out = Path(self.tmp.name) / 'staging'
        self.write('execution.json', {'status': 'failed', 'finished_at': '2026-11-03',
                                     'exit_code': 0, 'errors': ['Agent validation failed']})
        self.write('manifest.json', {'run_id': self.src.name, 'analysis_generated_at': '2026-11-03T10:00:00+03:00'})
        self.write('validation.json', {'passed': False, 'checks': [
            {'name': 'validate-browser.cjs', 'passed': False, 'detail': 'SIGABRT'}]})
        self.write('run.json', {'facts': []})
        html = '<script id="report-data" type="application/json">{"facts":[]}</script>'
        html += "<script>function categoryLabels(){const labels={...D.brand_categories.labels,...(['air','rail'].includes(active)?{tickets:'Продажи билетов'}:{})};return labels}</script>"
        for name in ('index.html', 'report.html'):
            (self.src / name).write_text(html)

    def write(self, name, data):
        (self.src / name).write_text(json.dumps(data))

    def run_prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return prepare(self.src, self.out, '2026-11-03')

    def test_launcher_crash_still_requires_browser(self):
        result = self.run_prepare()
        self.assertTrue(result['browser_required'])
        self.assertTrue(result['producer_browser_launch_failed'])
        self.assertIn("if(['air','rail'].includes(active))delete labels.tours;", (self.out / 'index.html').read_text())

    def test_alternative_browser_check_name_requires_browser(self):
        self.write('validation.json', {'passed': False, 'checks': [
            {'name': 'real browser validation', 'passed': False,
             'detail': 'Headless Chrome SIGABRT; CUA browser host unavailable.'}]})
        self.assertTrue(self.run_prepare()['browser_required'])

    def test_running_producer_is_blocked(self):
        self.write('execution.json', {'status': 'running'})
        with self.assertRaisesRegex(ValueError, 'still running'):
            self.run_prepare()

    def test_actual_site_error_is_blocked(self):
        self.write('validation.json', {'passed': False, 'checks': [
            {'name': 'validate-browser.cjs', 'passed': False, 'detail': 'Export/feed mismatch'}]})
        with self.assertRaisesRegex(ValueError, 'validation failed'):
            self.run_prepare()

    def test_data_mismatch_is_blocked(self):
        self.write('run.json', {'facts': ['different']})
        with self.assertRaisesRegex(ValueError, 'mismatch'):
            self.run_prepare()


if __name__ == '__main__':
    unittest.main()
