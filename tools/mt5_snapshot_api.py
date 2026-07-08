from __future__ import annotations

import json, socketserver, struct, threading, zlib
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR = ROOT / 'runtime' / 'market_data' / 'latest_candles'
HTTP_PORT = 5000
TCP_HOST = '127.0.0.1'
TCP_PORT = 45678
MAGIC = b'FUSMT5'
VERSION = 1
DEFAULT_LIMIT = 500
TF_CODE = {1:'M1',5:'M5',15:'M15',30:'M30',60:'H1',240:'H4',1440:'D1'}
TF_LABEL = {v:k for k,v in TF_CODE.items()}


def norm_symbol(v: str) -> str:
    s = (v or '').strip().upper().replace('/', '')
    return 'GOLD' if s == 'XAUUSD' else s


def norm_tf(v: str) -> str:
    return (v or '').strip().upper()


def snapshot_path(symbol: str, tf: str) -> Path:
    s = norm_symbol(symbol)
    t = norm_tf(tf)
    cands = [SNAPSHOT_DIR / f'{s}_{t}.json']
    if s == 'GOLD':
        cands.append(SNAPSHOT_DIR / f'XAUUSD_{t}.json')
    elif s == 'XAUUSD':
        cands.append(SNAPSHOT_DIR / f'GOLD_{t}.json')
    for p in cands:
        if p.exists():
            return p
    return cands[0]


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return {}


def read_candle_time(row: dict) -> str:
    return str(row.get('time') or row.get('timestamp') or row.get('date') or '')


def serialize_candle(symbol: str, tf: str, row: dict) -> dict:
    return {
        'symbol': norm_symbol(symbol),
        'timeframe': norm_tf(tf),
        'time': row.get('time') or row.get('timestamp') or row.get('date') or '',
        'open': float(row.get('open', 0) or 0),
        'high': float(row.get('high', 0) or 0),
        'low': float(row.get('low', 0) or 0),
        'close': float(row.get('close', 0) or 0),
        'volume': float(row.get('volume', row.get('tick_volume', 0)) or 0),
        'source': row.get('source', 'mt5_live'),
    }


class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.live_candles = {}
        self.ticks = {}
        self.selection = {'symbol': '', 'timeframe': '', 'limit': DEFAULT_LIMIT}
        self.clients = set()

    def upsert_candle(self, symbol: str, tf: str, candle: dict):
        key = (norm_symbol(symbol), norm_tf(tf))
        with self.lock:
            self.live_candles.setdefault(key, {})[read_candle_time(candle)] = serialize_candle(symbol, tf, candle)

    def upsert_tick(self, symbol: str, tick: dict):
        with self.lock:
            self.ticks[norm_symbol(symbol)] = tick

    def get_tick(self, symbol: str):
        with self.lock:
            return self.ticks.get(norm_symbol(symbol))

    def get_live(self, symbol: str, tf: str):
        key = (norm_symbol(symbol), norm_tf(tf))
        with self.lock:
            rows = list(self.live_candles.get(key, {}).values())
        return sorted(rows, key=lambda x: x.get('time', ''))

    def set_selection(self, symbol: str, tf: str, limit: int = DEFAULT_LIMIT):
        sel = {'symbol': norm_symbol(symbol), 'timeframe': norm_tf(tf), 'limit': max(1, int(limit or DEFAULT_LIMIT))}
        with self.lock:
            self.selection = sel
            clients = list(self.clients)
        for c in clients:
            c.request_stream(sel)
        return sel

    def add_client(self, client):
        with self.lock:
            self.clients.add(client)
            sel = dict(self.selection)
        if sel['symbol'] and sel['timeframe']:
            client.request_stream(sel)

    def remove_client(self, client):
        with self.lock:
            self.clients.discard(client)


STORE = Store()

def crc32(payload: bytes) -> int:
    return zlib.crc32(payload) & 0xFFFFFFFF


def build_frame(payload: bytes) -> bytes:
    return struct.pack('<6sHII', MAGIC, VERSION, len(payload), crc32(payload)) + payload


def enc_u16(v: int) -> bytes:
    return struct.pack('<H', int(v) & 0xFFFF)


def enc_u32(v: int) -> bytes:
    return struct.pack('<I', int(v) & 0xFFFFFFFF)


def enc_i64(v: int) -> bytes:
    return struct.pack('<q', int(v))


def enc_str(v: str) -> bytes:
    d = (v or '').encode('utf-8')
    return enc_u16(len(d)) + d


def build_history_request(symbol: str, tf: str, from_time: int = 0, limit: int = DEFAULT_LIMIT) -> bytes:
    payload = bytearray()
    payload += b'\x11'
    payload += enc_str(norm_symbol(symbol))
    payload += enc_u16(TF_LABEL.get(norm_tf(tf), 0))
    payload += enc_i64(from_time)
    payload += enc_u32(limit)
    return build_frame(bytes(payload))


def parse_u16(buf: bytes, off: int):
    return struct.unpack_from('<H', buf, off)[0], off + 2


def parse_u32(buf: bytes, off: int):
    return struct.unpack_from('<I', buf, off)[0], off + 4


def parse_i64(buf: bytes, off: int):
    return struct.unpack_from('<q', buf, off)[0], off + 8


def parse_f64(buf: bytes, off: int):
    return struct.unpack_from('<d', buf, off)[0], off + 8


def parse_str(buf: bytes, off: int):
    ln, off = parse_u16(buf, off)
    return buf[off:off + ln].decode('utf-8', errors='replace'), off + ln


def frame_from_buffer(buf: bytearray):
    header = struct.calcsize('<6sHII')
    if len(buf) < header:
        return None
    magic, version, plen, csum = struct.unpack('<6sHII', buf[:header])
    if magic != MAGIC or version != VERSION:
        buf.clear()
        return None
    end = header + plen
    if len(buf) < end:
        return None
    payload = bytes(buf[header:end])
    del buf[:end]
    if crc32(payload) != csum:
        return b''
    return payload


def iso_time(ts: int) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec='seconds')


class BridgeSession:
    def __init__(self, sock):
        self.sock = sock
        self.buf = bytearray()
        self.lock = threading.RLock()
        self.alive = True
        self.selection = None

    def close(self):
        with self.lock:
            self.alive = False
        try:
            self.sock.close()
        except OSError:
            pass

    def send(self, frame: bytes):
        with self.lock:
            if self.alive:
                try:
                    self.sock.sendall(frame)
                except OSError:
                    self.alive = False

    def request_stream(self, sel: dict):
        self.selection = sel
        self.send(build_history_request(sel['symbol'], sel['timeframe'], 0, sel['limit']))

    def handle_payload(self, payload: bytes):
        if not payload:
            return
        mtype = payload[0]
        off = 1
        if mtype == 1:
            if self.selection:
                self.request_stream(self.selection)
            return
        if mtype == 2:
            return
        if mtype == 16:
            symbol, off = parse_str(payload, off)
            tf_code, off = parse_u16(payload, off)
            ts, off = parse_i64(payload, off)
            bid, off = parse_f64(payload, off)
            ask, off = parse_f64(payload, off)
            last, off = parse_f64(payload, off)
            vol, off = parse_f64(payload, off)
            STORE.upsert_tick(symbol, {'symbol': norm_symbol(symbol), 'timeframe': TF_CODE.get(tf_code, str(tf_code)), 'timestamp': ts, 'bid': bid, 'ask': ask, 'last': last, 'volume': vol, 'spread': round((ask - bid) * 10000, 1)})
            return
        if mtype == 4:
            symbol, off = parse_str(payload, off)
            tf_code, off = parse_u16(payload, off)
            ts, off = parse_i64(payload, off)
            o, off = parse_f64(payload, off)
            h, off = parse_f64(payload, off)
            l, off = parse_f64(payload, off)
            c, off = parse_f64(payload, off)
            tv, off = parse_f64(payload, off)
            _, off = parse_u32(payload, off)
            STORE.upsert_candle(symbol, TF_CODE.get(tf_code, str(tf_code)), {'time': iso_time(ts), 'open': o, 'high': h, 'low': l, 'close': c, 'volume': tv, 'tick_volume': tv, 'source': 'mt5_socket'})

    def run(self):
        try:
            while self.alive:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                self.buf.extend(chunk)
                while True:
                    payload = frame_from_buffer(self.buf)
                    if payload is None:
                        break
                    if payload == b'':
                        continue
                    self.handle_payload(payload)
        finally:
            self.close()
            STORE.remove_client(self)

class MT5BridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class MT5BridgeHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.session = BridgeSession(self.request)
        STORE.add_client(self.session)

    def handle(self):
        self.session.run()

    def finish(self):
        self.session.close()


def merge_candles(snapshot: dict, live_rows: list[dict]) -> dict:
    merged = {}
    for row in snapshot.get('candles', []):
        if isinstance(row, dict):
            merged[read_candle_time(row)] = serialize_candle(snapshot.get('symbol', ''), snapshot.get('timeframe', ''), row)
    for row in live_rows:
        if isinstance(row, dict):
            merged[read_candle_time(row)] = row
    ordered = sorted(merged.values(), key=lambda x: x.get('time', ''))
    limit = int(snapshot.get('count') or len(ordered) or DEFAULT_LIMIT)
    out = dict(snapshot)
    out['candles'] = ordered[-limit:]
    out['count'] = len(out['candles'])
    return out


def health_payload():
    return {'status': 'ok', 'service': 'fusion_mt5_snapshot_api', 'stream': STORE.selection}


def read_snapshot(symbol: str, tf: str, limit: int) -> dict:
    path = snapshot_path(symbol, tf)
    if not path.exists():
        return {'schema': 'fusion.terminal.latest_candles.v1', 'symbol': norm_symbol(symbol), 'timeframe': norm_tf(tf), 'count': 0, 'candles': [], 'path': str(path)}
    payload = read_json(path)
    candles = payload.get('candles') if isinstance(payload, dict) else []
    if not isinstance(candles, list):
        candles = []
    out = [serialize_candle(symbol, tf, row) for row in candles[-limit:] if isinstance(row, dict)]
    return {'schema': 'fusion.terminal.latest_candles.v1', 'generated_at': payload.get('generated_at', ''), 'symbol': norm_symbol(symbol), 'broker_symbol': payload.get('broker_symbol', norm_symbol(symbol)), 'timeframe': norm_tf(tf), 'source': 'MT5', 'count': len(out), 'candles': out, 'path': str(path)}

class ApiHandler(BaseHTTPRequestHandler):
    server_version = 'FusionMT5SnapshotAPI/2.0'

    def write_json(self, status: int, payload: dict | list):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/health':
            return self.write_json(200, health_payload())
        if parsed.path == '/api/live':
            q = parse_qs(parsed.query)
            symbol = q.get('symbol', [''])[0]
            tf = q.get('tf', [''])[0]
            live = STORE.get_live(symbol, tf)
            return self.write_json(200, {'symbol': norm_symbol(symbol), 'timeframe': norm_tf(tf), 'tick': STORE.get_tick(symbol), 'current_candle': live[-1] if live else None, 'live_count': len(live), 'stream': STORE.selection})
        if parsed.path != '/api/candles':
            return self.write_json(404, {'error': 'not_found', 'path': parsed.path})
        q = parse_qs(parsed.query)
        symbol = q.get('symbol', [''])[0]
        tf = q.get('tf', [''])[0]
        try:
            limit = max(1, int(q.get('limit', ['200'])[0]))
        except ValueError:
            limit = 200
        snap = read_snapshot(symbol, tf, limit)
        return self.write_json(200, merge_candles(snap, STORE.get_live(symbol, tf)))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/stream':
            return self.write_json(404, {'error': 'not_found', 'path': parsed.path})
        try:
            size = int(self.headers.get('Content-Length', '0') or '0')
        except ValueError:
            size = 0
        try:
            data = json.loads(self.rfile.read(size).decode('utf-8', errors='replace') if size else '{}')
        except json.JSONDecodeError:
            return self.write_json(400, {'error': 'invalid_json'})
        symbol = str(data.get('symbol') or '').strip()
        tf = str(data.get('timeframe') or data.get('tf') or '').strip()
        if not symbol or not tf:
            return self.write_json(400, {'error': 'missing_symbol_or_timeframe'})
        sel = STORE.set_selection(symbol, tf, int(data.get('limit') or DEFAULT_LIMIT))
        return self.write_json(200, {'status': 'ok', 'stream': sel})

    def log_message(self, fmt, *args):
        return

if __name__ == '__main__':
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    threading.Thread(target=lambda: MT5BridgeServer((TCP_HOST, TCP_PORT), MT5BridgeHandler).serve_forever(), daemon=True).start()
    print(f'Fusion MT5 Socket Bridge em tcp://{TCP_HOST}:{TCP_PORT}')
    print(f'Fusion MT5 Snapshot API em http://{TCP_HOST}:{HTTP_PORT}')
    ThreadingHTTPServer((TCP_HOST, HTTP_PORT), ApiHandler).serve_forever()
