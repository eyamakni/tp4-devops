"""Validation hors cluster : rendu Kustomize et comportement HTTP reel."""
import importlib.util
import json
import pathlib
import subprocess
import threading
import unittest
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('demo', ROOT / 'apps/demo/base/app.py')
        cls.app = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.app)
        cls.server = cls.app.ThreadingHTTPServer(('127.0.0.1', 0), cls.app.Handler)
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_http_and_metrics(self):
        for path, expected in [('/',200),('/healthz',200),('/error',500),('/unknown',404)]:
            try:
                response = urllib.request.urlopen(self.url + path)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                self.assertEqual(response.code, expected)
                self.assertEqual(json.load(response)['status'], expected)
        with urllib.request.urlopen(self.url + '/metrics') as response:
            metrics = response.read().decode()
        self.assertIn('tp4_http_requests_total{route="/error",status="500"} 1', metrics)
        self.assertIn('tp4_http_requests_total{route="/other",status="404"} 1', metrics)
        self.assertNotIn('route="/healthz"', metrics)
        self.assertIn('tp4_http_request_duration_seconds_count{route="/"} 1', metrics)

    def test_kustomize_and_dashboard(self):
        for path in ['apps/demo/overlays/dev', 'observability']:
            result = subprocess.run(['kubectl','kustomize',path], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('kind:',result.stdout)
        dash = json.loads((ROOT/'observability/dashboards/tp4-gitops.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(dash['panels']),12)

if __name__ == '__main__':
    unittest.main(verbosity=2)
