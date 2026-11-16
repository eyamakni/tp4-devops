import json, os, threading, time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

counts = defaultdict(int)
durations = defaultdict(float)
lock = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        start = time.perf_counter()
        path = urlsplit(self.path).path
        if path == '/metrics':
            with lock:
                lines = ['# HELP tp4_http_requests_total Requests excluding probes and metrics.',
                         '# TYPE tp4_http_requests_total counter']
                for (route, status), count in sorted(counts.items()):
                    lines.append(f'tp4_http_requests_total{{route="{route}",status="{status}"}} {count}')
                lines += ['# HELP tp4_http_request_duration_seconds Response preparation duration.',
                          '# TYPE tp4_http_request_duration_seconds summary']
                for route, duration in sorted(durations.items()):
                    n = sum(v for (r, _), v in counts.items() if r == route)
                    lines += [f'tp4_http_request_duration_seconds_sum{{route="{route}"}} {duration}',
                              f'tp4_http_request_duration_seconds_count{{route="{route}"}} {n}']
            body = ('\n'.join(lines) + '\n').encode()
            status, content_type = 200, 'text/plain; version=0.0.4; charset=utf-8'
        else:
            status = 500 if path == '/error' else (200 if path in ['/', '/healthz'] else 404)
            body = json.dumps({'application':'tp4-demo', 'version':os.getenv('APP_VERSION','v1'),
                               'hostname':os.getenv('HOSTNAME','local'), 'status':status}).encode()
            content_type = 'application/json'
            if path != '/healthz':
                route = path if path in ['/', '/error'] else '/other'
                with lock:
                    counts[(route, str(status))] += 1
                    durations[route] += time.perf_counter() - start
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        if urlsplit(self.path).path not in ['/healthz','/metrics']:
            super().log_message(fmt, *args)

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.getenv('PORT','8080'))), Handler).serve_forever()
