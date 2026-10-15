"""Temporary loopback preview; Ctrl+C stops it. No remote hosting."""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from pathlib import Path
root=Path(__file__).resolve().parent/'dist'
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(root)))
print(f'Local: http://127.0.0.1:{server.server_port}/',flush=True)
try:server.serve_forever()
except KeyboardInterrupt:pass
finally:server.server_close()
