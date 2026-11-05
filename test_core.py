import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import requests
from core import trace_url, parse_trace, probe, fetch_locations, probe_many


class Handler(BaseHTTPRequestHandler):
    mode = 'ok'

    def do_GET(self):
        responses = {
            'ok': (200, b'ip=192.0.2.1\ncolo=ICN\nloc=KR\ntls=TLSv1.3\n'),
            'html': (200, b'<html>challenge</html>'),
            'redirect': (302, b''),
            'blocked': (403, b'Forbidden'),
            'large': (200, b'x' * 70000),
        }
        status, body = responses[self.mode]
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_url_normalization(self):
        self.assertEqual(trace_url(' Example.COM/a?q=x#y '), 'https://example.com/cdn-cgi/trace')
        self.assertEqual(trace_url('http://[::1]:8000/'), 'http://[::1]:8000/cdn-cgi/trace')

    def test_bad_urls(self):
        for value in ['', 'ftp://host', 'https://a:bad', 'https://user:pass@host', 'two sites']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                trace_url(value)

    def test_trace_validation(self):
        self.assertEqual(parse_trace('ip=192.0.2.1\ncolo=NRT\nextra=a=b')['extra'], 'a=b')
        for value in ['colo=ICN', '<html>colo=ICN</html>', 'ip=a\ncolo=invalid']:
            with self.assertRaises(ValueError):
                parse_trace(value)

    def test_actual_http(self):
        Handler.mode = 'ok'
        result = probe(self.url)
        self.assertEqual(result.colo, 'ICN')
        self.assertFalse(result.error)
        self.assertGreater(result.elapsed_ms, 0)

    def test_failure_responses(self):
        for mode in ['html', 'redirect', 'blocked', 'large']:
            Handler.mode = mode
            with self.subTest(mode=mode):
                result = probe(self.url)
                self.assertTrue(result.error)
                self.assertFalse(result.colo)

    def test_location_fallback(self):
        with patch('core.requests.get', side_effect=requests.Timeout):
            locations, note = fetch_locations()
        self.assertIn('ICN', locations)
        self.assertNotIn('ZZZ', locations)

    def test_cancellation(self):
        Handler.mode = 'ok'
        cancelled = threading.Event()
        cancelled.set()
        self.assertEqual(list(probe_many([self.url] * 10, cancelled)), [])

    def test_transport_error(self):
        with patch('core.requests.get', side_effect=requests.Timeout('timed out')):
            self.assertIn('timed out', probe('example.com').error)


if __name__ == '__main__':
    unittest.main()
