"""
SantaLitu - Servidor de Preces (API simples)
=============================================
Serve os JSONs de preces via HTTP para o frontend.
Roda junto com o http-server do frontend.

Uso:
  python preces_server.py          # porta 8082
  python preces_server.py 9090     # porta customizada
"""

import os
import sys
import json
import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "preces_data")

class PrecesHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache')

        path = self.path.strip('/')

        # /preces/2026-02-22 -> retorna JSON
        if path.startswith('preces/'):
            date_str = path.replace('preces/', '')
            json_path = os.path.join(DATA_DIR, f"preces_{date_str}.json")

            if os.path.exists(json_path):
                self.end_headers()
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.wfile.write(f.read().encode('utf-8'))
            else:
                self.end_headers()
                self.wfile.write(json.dumps({"error": "not_found", "data": date_str}).encode('utf-8'))

        # /preces -> lista todos os JSONs disponíveis
        elif path == 'preces':
            self.end_headers()
            files = []
            if os.path.exists(DATA_DIR):
                for f in sorted(os.listdir(DATA_DIR)):
                    if f.endswith('.json'):
                        date = f.replace('preces_', '').replace('.json', '')
                        files.append(date)
            self.wfile.write(json.dumps({"available": files}).encode('utf-8'))

        else:
            self.end_headers()
            self.wfile.write(json.dumps({"status": "SantaLitu Preces API", "endpoints": ["/preces", "/preces/YYYY-MM-DD"]}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.end_headers()

    def log_message(self, format, *args):
        print(f"  [API] {args[0]}")

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    server = HTTPServer(('0.0.0.0', port), PrecesHandler)
    print(f"SantaLitu Preces API rodando em http://127.0.0.1:{port}")
    print(f"Endpoints: /preces, /preces/YYYY-MM-DD")
    print(f"Data dir: {DATA_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
