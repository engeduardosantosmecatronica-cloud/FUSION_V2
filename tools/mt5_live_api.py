from __future__ import annotations

import json
import sys
import threading
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import fusion_frontend_data as fusion_data

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / 'config' / 'fusion_config.yaml'
SNAPSHOT_DIR = ROOT / 'runtime' / 'market_data' / 'latest_candles'
HTTP_PORT = 5000
HOST = '127.0.0.1'

try:
    import yaml
except ImportError:
    yaml = None

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


def normalize_symbol(value: str) -> str:
    symbol = (value or '').strip().upper().replace('/', '').replace('-', '').replace('_', '').replace(' ', '')
    if symbol in {'XAUUSD', 'GOLD'}:
        return 'GOLD'
    return symbol


def norm_tf(value: str) -> str:
    return (value or '').strip().upper()


def load_config() -> dict:
    if yaml is None or not CONFIG_PATH.exists():
        return {}
    try:
        return yaml.safe_load(CONFIG_PATH.read_text(encoding='utf-8', errors='replace')) or {}
    except Exception:
        return {}


CONFIG = load_config()
BROKER_SETTINGS = CONFIG.get('broker', {}) if isinstance(CONFIG, dict) else {}
SYMBOL_CONTRACTS = CONFIG.get('contracts', {}).get('symbols', {}) if isinstance(CONFIG, dict) else {}

MT5_TIMEFRAMES = {
    'M1': getattr(mt5, 'TIMEFRAME_M1', 1),
    'M5': getattr(mt5, 'TIMEFRAME_M5', 5),
    'M15': getattr(mt5, 'TIMEFRAME_M15', 15),
    'M30': getattr(mt5, 'TIMEFRAME_M30', 30),
    'H1': getattr(mt5, 'TIMEFRAME_H1', 16385),
    'H4': getattr(mt5, 'TIMEFRAME_H4', 16388),
    'D1': getattr(mt5, 'TIMEFRAME_D1', 16408),
}


def snapshot_path(symbol: str, tf: str) -> Path:
    s = normalize_symbol(symbol)
    t = norm_tf(tf)
    candidates = [SNAPSHOT_DIR / f'{s}_{t}.json']
    if s == 'GOLD':
        candidates.append(SNAPSHOT_DIR / f'XAUUSD_{t}.json')
    elif s == 'XAUUSD':
        candidates.append(SNAPSHOT_DIR / f'GOLD_{t}.json')
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return {}


def read_snapshot(symbol: str, tf: str, limit: int) -> dict:
    path = snapshot_path(symbol, tf)
    if not path.exists():
        return {
            'schema': 'fusion.terminal.latest_candles.v1',
            'symbol': normalize_symbol(symbol),
            'timeframe': norm_tf(tf),
            'count': 0,
            'candles': [],
            'path': str(path),
        }
    payload = read_json(path)
    candles = payload.get('candles') if isinstance(payload, dict) else []
    if not isinstance(candles, list):
        candles = []
    out = []
    for row in candles[-limit:]:
        if not isinstance(row, dict):
            continue
        out.append({
            'symbol': normalize_symbol(symbol),
            'timeframe': norm_tf(tf),
            'time': row.get('time') or row.get('timestamp') or row.get('date') or '',
            'open': float(row.get('open', 0) or 0),
            'high': float(row.get('high', 0) or 0),
            'low': float(row.get('low', 0) or 0),
            'close': float(row.get('close', 0) or 0),
            'volume': float(row.get('volume', row.get('tick_volume', 0)) or 0),
            'source': row.get('source', 'snapshot_fallback'),
        })
    return {
        'schema': 'fusion.terminal.latest_candles.v1',
        'generated_at': payload.get('generated_at', ''),
        'symbol': normalize_symbol(symbol),
        'broker_symbol': payload.get('broker_symbol', normalize_symbol(symbol)),
        'timeframe': norm_tf(tf),
        'source': 'snapshot_fallback',
        'count': len(out),
        'candles': out,
        'path': str(path),
    }


class Store:
    def __init__(self):
        self.lock = threading.RLock()
        self.selection = {'symbol': '', 'timeframe': '', 'limit': 500}

    def set_selection(self, symbol: str, tf: str, limit: int = 500) -> dict:
        sel = {'symbol': normalize_symbol(symbol), 'timeframe': norm_tf(tf), 'limit': max(1, int(limit or 500))}
        with self.lock:
            self.selection = sel
        return sel

    def get_selection(self) -> dict:
        with self.lock:
            return dict(self.selection)


STORE = Store()
MT5_READY = False
MT5_LOCK = threading.RLock()


def initialize_mt5() -> bool:
    global MT5_READY
    if mt5 is None:
        return False
    with MT5_LOCK:
        if MT5_READY:
            return True
        terminal_path = str(BROKER_SETTINGS.get('terminal_path') or '').strip()
        try:
            if terminal_path and Path(terminal_path).exists():
                MT5_READY = bool(mt5.initialize(path=terminal_path))
            else:
                MT5_READY = bool(mt5.initialize())
        except TypeError:
            MT5_READY = bool(mt5.initialize())
        return MT5_READY


def broker_symbol_for(symbol: str) -> str:
    symbol = normalize_symbol(symbol)
    contract = SYMBOL_CONTRACTS.get(symbol, {}) if isinstance(SYMBOL_CONTRACTS, dict) else {}
    if isinstance(contract, dict) and contract.get('broker_symbol'):
        return str(contract['broker_symbol']).upper()
    if symbol == 'GOLD':
        return 'GOLD'
    if symbol == 'XAUUSD':
        return 'GOLD'
    return symbol


def visible_symbols() -> set[str]:
    if not initialize_mt5() or mt5 is None:
        return set()
    try:
        items = mt5.symbols_get() or []
    except Exception:
        return set()
    return {str(item.name).upper() for item in items if getattr(item, 'visible', True)}


def resolve_symbol(symbol: str) -> str:
    broker_symbol = broker_symbol_for(symbol)
    visible = visible_symbols()
    if broker_symbol in visible:
        return broker_symbol
    compact = broker_symbol.replace('-', '')
    if compact in visible:
        return compact
    return broker_symbol


def read_live_candles(symbol: str, tf: str, limit: int) -> tuple[list[dict], str, str]:
    if not initialize_mt5() or mt5 is None:
        return [], 'mt5_not_ready', resolve_symbol(symbol)
    timeframe = MT5_TIMEFRAMES.get(norm_tf(tf))
    if timeframe is None:
        return [], f'invalid_timeframe:{tf}', resolve_symbol(symbol)
    broker_symbol = resolve_symbol(symbol)
    try:
        if not mt5.symbol_select(broker_symbol, True):
            return [], f'symbol_select_failed:{broker_symbol}', broker_symbol
        rates = mt5.copy_rates_from_pos(broker_symbol, timeframe, 0, max(limit, 50))
    except Exception:
        return [], f'mt5_error:{broker_symbol}', broker_symbol
    if rates is None or len(rates) == 0:
        return [], f'no_rates:{broker_symbol}', broker_symbol
    rows = []
    for row in rates[-limit:]:
        rows.append({
            'symbol': normalize_symbol(symbol),
            'timeframe': norm_tf(tf),
            'time': datetime.fromtimestamp(int(row['time'])).strftime('%Y-%m-%d %H:%M:%S'),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['tick_volume']) if hasattr(row, 'dtype') and row.dtype.names and 'tick_volume' in row.dtype.names else 0.0,
            'source': 'mt5_direct',
        })
    return rows, 'mt5_direct', broker_symbol


def read_tick(symbol: str) -> dict | None:
    if not initialize_mt5() or mt5 is None:
        return None
    broker_symbol = resolve_symbol(symbol)
    try:
        if not mt5.symbol_select(broker_symbol, True):
            return None
        tick = mt5.symbol_info_tick(broker_symbol)
    except Exception:
        return None
    if tick is None:
        return None
    ts = int(getattr(tick, 'time', 0) or 0)
    return {
        'symbol': normalize_symbol(symbol),
        'broker_symbol': broker_symbol,
        'timestamp': ts,
        'time': datetime.fromtimestamp(ts).isoformat(timespec='seconds') if ts else '',
        'bid': float(getattr(tick, 'bid', 0.0) or 0.0),
        'ask': float(getattr(tick, 'ask', 0.0) or 0.0),
        'last': float(getattr(tick, 'last', 0.0) or 0.0),
        'volume': float(getattr(tick, 'volume', 0.0) or 0.0),
        'spread': round((float(getattr(tick, 'ask', 0.0) or 0.0) - float(getattr(tick, 'bid', 0.0) or 0.0)) * 10000, 1),
    }



def infer_timeframe_from_magic(magic: int) -> str:
    text = str(int(magic or 0))
    for suffix, tf in [('1440', 'D1'), ('240', 'H4'), ('60', 'H1'), ('30', 'M30'), ('15', 'M15'), ('5', 'M5')]:
        if text.endswith(suffix):
            return tf
    return ''


def infer_strategy_from_magic(magic: int) -> str:
    text = str(int(magic or 0))
    if not text or text == '0':
        return ''
    first = text[0]
    if first in {'1', '2', '3', '4', '5', '6'}:
        return f'S{first}'
    return ''


def position_to_payload(pos) -> dict:
    pos_type = int(getattr(pos, 'type', 0) or 0)
    magic = int(getattr(pos, 'magic', 0) or 0)
    opened_ts = int(getattr(pos, 'time', 0) or 0)
    return {
        'ticket': int(getattr(pos, 'ticket', 0) or 0),
        'symbol': normalize_symbol(str(getattr(pos, 'symbol', '') or '')),
        'broker_symbol': str(getattr(pos, 'symbol', '') or ''),
        'direction': 'BUY' if pos_type == 0 else 'SELL',
        'lots': float(getattr(pos, 'volume', 0.0) or 0.0),
        'entry_price': float(getattr(pos, 'price_open', 0.0) or 0.0),
        'current_price': float(getattr(pos, 'price_current', 0.0) or 0.0),
        'sl': float(getattr(pos, 'sl', 0.0) or 0.0),
        'tp': float(getattr(pos, 'tp', 0.0) or 0.0),
        'profit': float(getattr(pos, 'profit', 0.0) or 0.0),
        'swap': float(getattr(pos, 'swap', 0.0) or 0.0),
        'magic_number': magic,
        'strategy': infer_strategy_from_magic(magic),
        'timeframe': infer_timeframe_from_magic(magic),
        'opened_at': datetime.fromtimestamp(opened_ts).isoformat(timespec='seconds') if opened_ts else '',
        'comment': str(getattr(pos, 'comment', '') or ''),
        'trailing_active': False,
    }


def read_open_orders() -> list[dict]:
    if not initialize_mt5() or mt5 is None:
        return []
    try:
        positions = mt5.positions_get() or []
    except Exception:
        return []
    return [position_to_payload(pos) for pos in positions]


def find_position(ticket: int):
    if not initialize_mt5() or mt5 is None:
        return None
    try:
        positions = mt5.positions_get(ticket=int(ticket)) or []
    except Exception:
        return None
    return positions[0] if positions else None


def close_position(ticket: int, partial: bool = False, lots: float | None = None) -> dict:
    pos = find_position(ticket)
    if pos is None or mt5 is None:
        return {'ok': False, 'ticket': ticket, 'message': 'Posicao nao encontrada no MT5'}
    symbol = str(getattr(pos, 'symbol', '') or '')
    pos_type = int(getattr(pos, 'type', 0) or 0)
    volume_open = float(getattr(pos, 'volume', 0.0) or 0.0)
    volume = float(lots or volume_open) if partial else volume_open
    if volume <= 0 or volume > volume_open:
        return {'ok': False, 'ticket': ticket, 'message': f'Volume invalido: {volume}'}
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {'ok': False, 'ticket': ticket, 'message': f'Tick indisponivel para {symbol}'}
    order_type = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = float(tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask)
    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'position': int(ticket),
        'symbol': symbol,
        'volume': volume,
        'type': order_type,
        'price': price,
        'deviation': 30,
        'magic': int(getattr(pos, 'magic', 0) or 0),
        'comment': 'fusion_frontend_close',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None:
        return {'ok': False, 'ticket': ticket, 'message': 'order_send retornou None'}
    retcode = int(getattr(result, 'retcode', 0) or 0)
    ok = retcode in {getattr(mt5, 'TRADE_RETCODE_DONE', 10009), getattr(mt5, 'TRADE_RETCODE_PLACED', 10008)}
    return {'ok': ok, 'ticket': ticket, 'retcode': retcode, 'message': str(getattr(result, 'comment', '') or ('Ordem enviada' if ok else 'Falha ao fechar posicao'))}


def update_position(ticket: int, payload: dict) -> dict:
    pos = find_position(ticket)
    if pos is None or mt5 is None:
        return {'ok': False, 'ticket': ticket, 'message': 'Posicao nao encontrada no MT5'}
    symbol = str(getattr(pos, 'symbol', '') or '')
    sl = payload.get('sl')
    tp = payload.get('tp')
    request = {
        'action': mt5.TRADE_ACTION_SLTP,
        'position': int(ticket),
        'symbol': symbol,
        'sl': float(sl) if sl not in (None, '') else float(getattr(pos, 'sl', 0.0) or 0.0),
        'tp': float(tp) if tp not in (None, '') else float(getattr(pos, 'tp', 0.0) or 0.0),
        'magic': int(getattr(pos, 'magic', 0) or 0),
        'comment': 'fusion_frontend_update',
    }
    result = mt5.order_send(request)
    if result is None:
        return {'ok': False, 'ticket': ticket, 'message': 'order_send retornou None'}
    retcode = int(getattr(result, 'retcode', 0) or 0)
    ok = retcode in {getattr(mt5, 'TRADE_RETCODE_DONE', 10009), getattr(mt5, 'TRADE_RETCODE_PLACED', 10008)}
    return {'ok': ok, 'ticket': ticket, 'retcode': retcode, 'message': str(getattr(result, 'comment', '') or ('Ordem atualizada' if ok else 'Falha ao atualizar posicao'))}

def build_performance_payload() -> dict:
    base = fusion_data.get_performance()
    orders = read_open_orders()
    signals = fusion_data.get_live_signals({}, 500)
    blocked = len([s for s in signals if s.get('status') == 'bloqueado'])
    executed = len(orders)
    total_profit = sum(float(o.get('profit') or 0.0) for o in orders)

    def grouped(key: str, label: str) -> list[dict]:
        groups: dict[str, list[dict]] = {}
        for order in orders:
            groups.setdefault(str(order.get(key) or ''), []).append(order)
        out = []
        for name, items in sorted(groups.items()):
            profit = sum(float(i.get('profit') or 0.0) for i in items)
            wins = len([i for i in items if float(i.get('profit') or 0.0) >= 0])
            out.append({
                label: name or '-',
                'profit': round(profit, 2),
                'win_rate': wins / len(items) if items else 0,
                'total_orders': len(items),
                'avg_points': 0,
                'drawdown': abs(min(0.0, profit)) / 100.0,
            })
        return out

    by_symbol = grouped('symbol', 'symbol')
    by_timeframe = grouped('timeframe', 'timeframe')
    by_strategy = grouped('strategy', 'strategy')
    base.update({
        'by_symbol': by_symbol,
        'by_timeframe': by_timeframe,
        'by_strategy': by_strategy,
        'totals': {
            'total_signals': len(signals),
            'signals_blocked': blocked,
            'signals_executed': executed,
            'total_profit': round(total_profit, 2),
            'win_rate': len([o for o in orders if float(o.get('profit') or 0.0) >= 0]) / len(orders) if orders else 0,
            'drawdown': abs(min(0.0, total_profit)) / 100.0,
        },
    })
    return base

def parse_audit_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)
    except Exception:
        return None


def symbol_point(symbol: str) -> float:
    if not initialize_mt5() or mt5 is None:
        return 0.0001
    broker_symbol = resolve_symbol(symbol)
    try:
        info = mt5.symbol_info(broker_symbol)
    except Exception:
        info = None
    point = float(getattr(info, 'point', 0.0) or 0.0) if info is not None else 0.0
    if point > 0:
        return point
    if symbol.upper().endswith('JPY'):
        return 0.001
    if symbol.upper() in {'BTCUSD', 'ETHUSD', 'GOLD'}:
        return 0.01
    return 0.0001


def close_at_or_after(rates, target: datetime) -> float | None:
    if rates is None or len(rates) == 0:
        return None
    target_ts = int(target.timestamp())
    best = None
    for row in rates:
        ts = int(row['time'])
        if ts >= target_ts:
            return float(row['close'])
        best = row
    return float(best['close']) if best is not None else None


def enrich_block_audit_row(row: dict) -> dict:
    symbol = str(row.get('symbol') or '')
    direction = str(row.get('direction') or '').upper()
    blocked_at = parse_audit_datetime(str(row.get('timestamp') or ''))
    if not symbol or direction not in {'BUY', 'SELL'} or blocked_at is None or not initialize_mt5() or mt5 is None:
        return row

    broker_symbol = resolve_symbol(symbol)
    try:
        mt5.symbol_select(broker_symbol, True)
        start = blocked_at - timedelta(minutes=5)
        end = blocked_at + timedelta(hours=3, minutes=10)
        rates = mt5.copy_rates_range(broker_symbol, MT5_TIMEFRAMES['M1'], start, end)
    except Exception:
        return row
    if rates is None or len(rates) == 0:
        return row

    price0 = close_at_or_after(rates, blocked_at)
    price15 = close_at_or_after(rates, blocked_at + timedelta(minutes=15))
    price60 = close_at_or_after(rates, blocked_at + timedelta(hours=1))
    price180 = close_at_or_after(rates, blocked_at + timedelta(hours=3))
    if price0 is None:
        return row

    point = symbol_point(symbol)
    final_price = price180 if price180 is not None else price60 if price60 is not None else price15
    if final_price is None:
        row.update({
            'price_at_block': round(price0, 6),
            'classification': 'pendente',
            'audit_note': 'aguardando candles posteriores suficientes',
        })
        return row

    raw_points = (final_price - price0) / point if point else 0.0
    result_points = raw_points if direction == 'BUY' else -raw_points
    classification = 'mau bloqueio' if result_points > 0 else 'bom bloqueio' if result_points < 0 else 'neutro'
    row.update({
        'price_at_block': round(price0, 6),
        'price_after_15m': round(price15, 6) if price15 is not None else 0,
        'price_after_1h': round(price60, 6) if price60 is not None else 0,
        'price_after_3h': round(price180, 6) if price180 is not None else 0,
        'result_points': round(result_points, 1),
        'classification': classification,
        'profit_lost': round(max(result_points, 0.0), 2),
        'loss_avoided': round(max(-result_points, 0.0), 2),
        'audit_note': 'calculado_com_mt5_m1',
    })
    return row


def build_block_audit_payload(filters: dict) -> list[dict]:
    try:
        limit = max(1, min(120, int(filters.get('limit') or 80)))
    except ValueError:
        limit = 80
    rows = fusion_data.get_block_audit()[:limit]
    return [enrich_block_audit_row(dict(row)) for row in rows]

def build_filter_performance_payload() -> list[dict]:
    rows = build_block_audit_payload({'limit': '120'})
    grouped: dict[str, dict] = {}
    for row in rows:
        name = str(row.get('filter') or 'unknown')
        item = grouped.setdefault(name, {
            'filter': name,
            'name': name,
            'mode': 'shadow',
            'total_blocks': 0,
            'good_blocks': 0,
            'bad_blocks': 0,
            'profit_lost': 0.0,
            'loss_avoided': 0.0,
            'recommendation': 'monitorar',
            'last_reason': '',
        })
        item['total_blocks'] += 1
        cls = row.get('classification')
        if cls == 'bom bloqueio':
            item['good_blocks'] += 1
        elif cls == 'mau bloqueio':
            item['bad_blocks'] += 1
        item['profit_lost'] += float(row.get('profit_lost') or 0.0)
        item['loss_avoided'] += float(row.get('loss_avoided') or 0.0)
        item['last_reason'] = row.get('reason') or item['last_reason']
    for item in grouped.values():
        item['profit_lost'] = round(item['profit_lost'], 2)
        item['loss_avoided'] = round(item['loss_avoided'], 2)
        if item['bad_blocks'] > item['good_blocks'] * 1.5 and item['bad_blocks'] >= 3:
            item['recommendation'] = 'virar shadow'
        elif item['good_blocks'] > item['bad_blocks'] and item['good_blocks'] >= 3:
            item['recommendation'] = 'manter block'
        else:
            item['recommendation'] = 'monitorar'
    return sorted(grouped.values(), key=lambda x: (x['bad_blocks'], x['profit_lost']), reverse=True)

def read_request_json(handler: BaseHTTPRequestHandler) -> dict:
    try:
        size = int(handler.headers.get('Content-Length', '0') or '0')
    except ValueError:
        size = 0
    if size <= 0:
        return {}
    try:
        return json.loads(handler.rfile.read(size).decode('utf-8', errors='replace'))
    except json.JSONDecodeError:
        return {}


def fusion_response_for_get(path: str, q: dict, mt5_health: dict | None = None):
    filters = {k: v[0] for k, v in q.items() if v}
    if path == '/api/fusion/status':
        status = fusion_data.get_system_status(mt5_health or {})
        orders = read_open_orders()
        status['open_orders'] = len(orders)
        status['last_order'] = orders[-1] if orders else None
        return status
    if path == '/api/fusion/signals':
        return fusion_data.get_live_signals(filters)
    if path == '/api/fusion/filters':
        perf = build_filter_performance_payload()
        known = {item['name']: item for item in perf}
        base = fusion_data.get_filter_status()
        merged = []
        for item in base:
            merged.append({**item, **known.get(item.get('name'), {})})
        for name, item in known.items():
            if not any(x.get('name') == name for x in merged):
                merged.append(item)
        return merged
    if path == '/api/fusion/runtime':
        return fusion_data.get_runtime_control()
    if path == '/api/fusion/logs':
        return fusion_data.get_logs(filters)
    if path == '/api/fusion/briefing':
        return fusion_data.get_market_briefing()
    if path == '/api/fusion/orders':
        return read_open_orders()
    if path == '/api/fusion/alerts':
        return fusion_data.get_alerts()
    if path == '/api/fusion/models':
        return fusion_data.get_models()
    if path == '/api/fusion/performance':
        return build_performance_payload()
    if path == '/api/fusion/filter-performance':
        return build_filter_performance_payload()
    if path == '/api/fusion/block-audit':
        return build_block_audit_payload(filters)
    if path == '/api/fusion/chart-overlays':
        return fusion_data.get_chart_overlays(filters.get('symbol', ''), filters.get('timeframe') or filters.get('tf', ''))
    if path == '/api/fusion/signal-panel':
        return fusion_data.get_signal_panel(filters.get('symbol', ''), filters.get('timeframe') or filters.get('tf', ''))
    if path == '/api/fusion/decision-timeline':
        signals = fusion_data.get_live_signals({}, 1)
        return {'signal': signals[0] if signals else None, 'filters_applied': fusion_data.get_filter_status()[:8], 'decision': signals[0]['decision'] if signals else 'WAIT'}
    return None
def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict | list):
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(body)))
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
    handler.end_headers()
    handler.wfile.write(body)


class ApiHandler(BaseHTTPRequestHandler):
    server_version = 'FusionMT5DirectAPI/1.0'

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/health':
            return json_response(self, 200, {
                'status': 'ok',
                'service': 'fusion_mt5_direct_api',
                'mt5_ready': initialize_mt5(),
                'stream': STORE.get_selection(),
            })

        q = parse_qs(parsed.query)
        if parsed.path.startswith('/api/fusion/'):
            payload = fusion_response_for_get(parsed.path, q, {'mt5_ready': initialize_mt5()})
            if payload is None:
                return json_response(self, 404, {'error': 'not_found', 'path': parsed.path})
            return json_response(self, 200, payload)

        symbol = q.get('symbol', [''])[0]
        tf = q.get('tf', [''])[0]
        try:
            limit = max(1, int(q.get('limit', ['200'])[0]))
        except ValueError:
            limit = 200

        if parsed.path == '/api/live':
            candles, source, broker_symbol = read_live_candles(symbol, tf, limit)
            return json_response(self, 200, {
                'symbol': normalize_symbol(symbol),
                'timeframe': norm_tf(tf),
                'broker_symbol': broker_symbol,
                'tick': read_tick(symbol),
                'current_candle': candles[-1] if candles else None,
                'live_count': len(candles),
                'source': source,
                'stream': STORE.get_selection(),
            })

        if parsed.path != '/api/candles':
            return json_response(self, 404, {'error': 'not_found', 'path': parsed.path})

        candles, source, broker_symbol = read_live_candles(symbol, tf, limit)
        if not candles:
            snap = read_snapshot(symbol, tf, limit)
            return json_response(self, 200, snap)

        return json_response(self, 200, {
            'schema': 'fusion.terminal.latest_candles.v1',
            'generated_at': datetime.now().isoformat(timespec='seconds'),
            'symbol': normalize_symbol(symbol),
            'broker_symbol': broker_symbol,
            'timeframe': norm_tf(tf),
            'source': source,
            'count': len(candles),
            'candles': candles,
        })

    def do_POST(self):
        parsed = urlparse(self.path)
        data = read_request_json(self)

        if parsed.path == '/api/fusion/runtime':
            try:
                return json_response(self, 200, fusion_data.update_runtime_control(data))
            except Exception as exc:
                return json_response(self, 400, {'error': str(exc)})
        if parsed.path == '/api/fusion/runtime/patch':
            try:
                return json_response(self, 200, fusion_data.patch_runtime_control(str(data.get('path') or ''), data.get('value')))
            except Exception as exc:
                return json_response(self, 400, {'error': str(exc)})
        if parsed.path == '/api/fusion/filter-mode':
            try:
                return json_response(self, 200, fusion_data.update_filter_mode(str(data.get('filterName') or data.get('filter') or ''), str(data.get('mode') or '')))
            except Exception as exc:
                return json_response(self, 400, {'error': str(exc)})
        if parsed.path == '/api/fusion/briefing':
            try:
                return json_response(self, 200, fusion_data.update_market_briefing(data))
            except Exception as exc:
                return json_response(self, 400, {'error': str(exc)})
        if parsed.path == '/api/fusion/order/close':
            try:
                return json_response(self, 200, close_position(int(data.get('ticket') or 0), bool(data.get('partial')), data.get('lots')))
            except Exception as exc:
                return json_response(self, 400, {'ok': False, 'error': str(exc)})
        if parsed.path == '/api/fusion/order/update':
            try:
                return json_response(self, 200, update_position(int(data.get('ticket') or 0), data))
            except Exception as exc:
                return json_response(self, 400, {'ok': False, 'error': str(exc)})
        if parsed.path.startswith('/api/fusion/'):
            return json_response(self, 200, {'ok': True, 'path': parsed.path, 'received': data})

        if parsed.path != '/api/stream':
            return json_response(self, 404, {'error': 'not_found', 'path': parsed.path})

        symbol = str(data.get('symbol') or '').strip()
        tf = str(data.get('timeframe') or data.get('tf') or '').strip()
        if not symbol or not tf:
            return json_response(self, 400, {'error': 'missing_symbol_or_timeframe'})
        sel = STORE.set_selection(symbol, tf, int(data.get('limit') or 500))
        return json_response(self, 200, {'status': 'ok', 'stream': sel})

    def do_PUT(self):
        self.do_POST()

    def do_PATCH(self):
        self.do_POST()

    def log_message(self, fmt, *args):
        return


def main() -> int:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Fusion MT5 Direct API em http://{HOST}:{HTTP_PORT}', flush=True)
    print('Usando MetaTrader5 Python API direta (sem SocketConnect)', flush=True)
    try:
        ThreadingHTTPServer((HOST, HTTP_PORT), ApiHandler).serve_forever()
    except OSError as exc:
        print(f'Falha ao iniciar API MT5: {exc}', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())















