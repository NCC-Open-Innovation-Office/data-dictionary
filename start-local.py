#!/usr/bin/env python
"""
Simple script to run both servers for local development.
Includes a reverse proxy so /api/ requests are forwarded to Flask,
eliminating the need for CORS.
"""
import subprocess
import sys
import os
import time
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.request import urlopen, Request
from urllib.error import URLError

API_PORT = 5001
WEB_PORT = 8000

class ProxyHandler(SimpleHTTPRequestHandler):
    """Serves static files and proxies /api/ requests to Flask."""

    def do_request(self, method):
        if self.path.startswith('/api/') or self.path == '/api':
            self.proxy_to_api(method)
        else:
            # Fall through to default handler for GET/HEAD
            if method == 'GET':
                super().do_GET()
            elif method == 'HEAD':
                super().do_HEAD()
            else:
                self.send_error(405)

    def proxy_to_api(self, method):
        url = f'http://127.0.0.1:{API_PORT}{self.path}'
        body = None
        if method in ('POST', 'PUT', 'PATCH'):
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length) if length else None

        headers = {}
        for key in ('Content-Type', 'Accept', 'Authorization'):
            val = self.headers.get(key)
            if val:
                headers[key] = val

        try:
            req = Request(url, data=body, headers=headers, method=method)
            with urlopen(req) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                for h, v in resp.getheaders():
                    if h.lower() not in ('transfer-encoding', 'connection'):
                        self.send_header(h, v)
                self.end_headers()
                self.wfile.write(resp_body)
        except URLError as e:
            self.send_error(502, f'API unreachable: {e}')

    def do_GET(self):
        self.do_request('GET')
    def do_POST(self):
        self.do_request('POST')
    def do_PUT(self):
        self.do_request('PUT')
    def do_PATCH(self):
        self.do_request('PATCH')
    def do_DELETE(self):
        self.do_request('DELETE')
    def do_HEAD(self):
        self.do_request('HEAD')

    def log_message(self, fmt, *args):
        # Keep default logging
        super().log_message(fmt, *args)


def main():
    print("=" * 60)
    print("Starting Data Dictionary - Local Development")
    print("=" * 60)
    print()
    
    # Set the DATABASE environment variable for the API
    os.environ['DATABASE'] = '../data/dictionary.db'
    
    processes = []
    
    try:
        # Start Flask API server
        print(f"Starting Flask API server on port {API_PORT}...")
        api_process = subprocess.Popen(
            [sys.executable, 'app.py'],
            cwd='api',
            env=os.environ.copy()
        )
        processes.append(('API Server', api_process))
        time.sleep(2)
        
        # Start proxying web server for frontend
        print(f"Starting web server on port {WEB_PORT} (proxying /api/ → :{API_PORT})...")
        server = HTTPServer(('0.0.0.0', WEB_PORT), ProxyHandler)
        web_thread = threading.Thread(target=server.serve_forever, daemon=True)
        web_thread.start()
        
        print()
        print("=" * 60)
        print("Data Dictionary is now running!")
        print("=" * 60)
        print()
        print("Public view:  http://localhost:8000/")
        print("Admin view:   http://localhost:8000/admin/")
        print("API:          http://localhost:5001/api")
        print()
        print("Press Ctrl+C to stop all servers")
        print("=" * 60)
        print()
        
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if any process died
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n{name} stopped unexpectedly!")
                    raise KeyboardInterrupt
                    
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All servers stopped.")

if __name__ == '__main__':
    main()
