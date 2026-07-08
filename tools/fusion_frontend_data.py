from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / 'config'
RUNTIME_CONTROL_PATH = CONFIG_DIR / 'fusion_runtime_control.json'
FUSION_CONFIG_PATH = CONFIG_DIR / 'fusion_config.yaml'
MARKET_BRIEFING_PATH = CONFIG_DIR / 'market_briefing_today.json'
LOG_DIR = ROOT / 'logs'
MODEL_DIRS = [ROOT / 'models', ROOT / 'models_research', ROOT / 'models_principal', ROOT / 'models_experts']
COMMON_FILES_DIR = Path(os.environ.get('FUSION_MT5_COMMON_FILES', Path.home() / 'AppData' / 'Roaming' / 'MetaQuotes' / 'Terminal' / 'Common' / 'Files'))
SIGNAL_PANEL_PATHS = [
    ROOT / 'runtime' / 'mt5_files' / 'fusion_signal_panel.csv',
]

SIGNAL_RE = re.compile(r"SINAL\s+(BUY|SELL):\s+([A-Z0-9]+)\s+([A-Z0-9]+)\s+\|\s+p_buy:\s+([0-9.]+)\s+\|\s+p_sell:\s+([0-9.]+)")
TIMING_RE = re.compile(r"\[TIMING\]\s+([^|]+)\|\s+analise\s+([A-Z0-9]+)\s+([A-Z0-9]+)\s+\|\s+([0-9.]+)s\s+\|\s+status=([^\s|]+)\s+\|\s+signal=([0-9]+)")
FILTER_RE = re.compile(r"STRATEGY(\d+)\s+([A-Z0-9]+)\s+([A-Z0-9]+)\s+(?:BUY|SELL)?\s*([a-zA-Z0-9_]+)\s+(block|shadow):\s*(.*)")
NO_ORDER_RE = re.compile(r"S(\d+)\s+([A-Z0-9]+)\s+([A-Z0-9]+)\s+(BUY|SELL)\s+tentativa_sem_ordem:\s*(.*)")
ORDER_RE = re.compile(r"(ORDEM|ORDER).*?(BUY|SELL).*?([A-Z0-9]+)", re.IGNORECASE)

FILTER_NAMES = [
    'risk_engine', 'portfolio_correlation', 'portfolio_exposure', 'session_context',
    'timeframe_consensus', 'market_regime', 'macro_flow', 'market_structure',
    'candle_price_confirmation', 'ema_alignment', 'opportunity_engine', 'volatility_engine',
    'entry_timing', 'context_engine', 'context_brain', 'execution_engine',
    'manual_approval', 'allow_new_orders', 'mt5_autotrading', 'spread',
    'confidence', 'signal_strength', 'market_briefing', 'ema_lower_timeframes_direction',
]



def symbol_file_candidates(prefix: str, symbol: str) -> list[Path]:
    clean_symbol = (symbol or '').upper().strip()
    names = []
    if clean_symbol:
        names.extend([
            f'{prefix}{clean_symbol}.csv',
            f'{prefix}{clean_symbol.lower()}.csv',
        ])
    if prefix.endswith('_'):
        names.append(f'{prefix[:-1]}.csv')
    candidates = []
    for folder in [COMMON_FILES_DIR, ROOT / 'runtime' / 'mt5_files', ROOT / 'mt5_files']:
        for name in names:
            candidates.append(folder / name)
    return candidates

def now_iso() -> str:
    return datetime.now().isoformat(timespec='seconds')


def safe_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return {} if default is None else default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def safe_yaml(path: Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding='utf-8', errors='replace')) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(merged.get(key), value)
        return merged
    if override is None:
        return base
    return override


def latest_fusion_log() -> Path | None:
    files = sorted(LOG_DIR.glob('fusion_*.log'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def tail_lines(path: Path | None, max_lines: int = 1200) -> list[str]:
    if not path or not path.exists():
        return []
    try:
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        return lines[-max_lines:]
    except Exception:
        return []


def parse_log_ts(line: str) -> str:
    raw = line[:19]
    try:
        return datetime.strptime(raw, '%Y-%m-%d %H:%M:%S').isoformat()
    except Exception:
        return now_iso()


def get_runtime_control() -> dict:
    base = safe_yaml(FUSION_CONFIG_PATH)
    runtime = safe_json(RUNTIME_CONTROL_PATH, {})
    if not isinstance(runtime, dict):
        runtime = {}
    data = deep_merge(base, runtime)
    if not isinstance(data, dict):
        data = {}
    data.setdefault('_meta', {})
    data['_meta'].update({
        'source': str(RUNTIME_CONTROL_PATH),
        'base_source': str(FUSION_CONFIG_PATH),
        'loaded_at': now_iso(),
        'exists': RUNTIME_CONTROL_PATH.exists(),
        'base_exists': FUSION_CONFIG_PATH.exists(),
        'mode': 'fusion_config_yaml_plus_runtime_json',
    })
    return data


def update_runtime_control(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError('payload must be object')
    clean = dict(payload)
    clean.pop('_meta', None)
    write_json(RUNTIME_CONTROL_PATH, clean)
    return get_runtime_control()


def set_path_value(payload: dict, path: str, value: Any) -> dict:
    cur = payload
    parts = [p for p in str(path).split('.') if p]
    for key in parts[:-1]:
        if not isinstance(cur.get(key), dict):
            cur[key] = {}
        cur = cur[key]
    if parts:
        cur[parts[-1]] = value
    return payload


def patch_runtime_control(path: str, value: Any) -> dict:
    data = get_runtime_control()
    data.pop('_meta', None)
    set_path_value(data, path, value)
    write_json(RUNTIME_CONTROL_PATH, data)
    return get_runtime_control()


def get_logs(filters: dict | None = None, limit: int = 250) -> list[dict]:
    filters = filters or {}
    lines = tail_lines(latest_fusion_log(), max_lines=max(1500, limit * 5))
    out = []
    for i, line in enumerate(reversed(lines)):
        lower = line.lower()
        typ = 'timing' if '[timing]' in lower else 'sinal' if 'sinal ' in lower else 'bloqueio' if ' block:' in lower or 'tentativa_sem_ordem' in lower else 'warning' if 'warning' in lower else 'erro' if 'error' in lower or 'erro' in lower else 'info'
        severity = 'error' if typ == 'erro' else 'warn' if typ in {'warning', 'bloqueio'} else 'info'
        symbol = None
        timeframe = None
        m = SIGNAL_RE.search(line) or TIMING_RE.search(line) or FILTER_RE.search(line) or NO_ORDER_RE.search(line)
        if m:
            groups = m.groups()
            # signal groups: direction,symbol,tf...
            if len(groups) >= 3:
                for g in groups:
                    if isinstance(g, str) and re.fullmatch(r'[A-Z]{3,6}[A-Z0-9]*', g or ''):
                        if symbol is None:
                            symbol = g
                        elif timeframe is None:
                            timeframe = g
                            break
        item = {
            'id': f'log_{i}',
            'timestamp': parse_log_ts(line),
            'type': typ,
            'symbol': symbol,
            'timeframe': timeframe,
            'message': line,
            'severity': severity,
        }
        if filters.get('type') and item['type'] != filters['type']:
            continue
        if filters.get('symbol') and item.get('symbol') not in (None, filters['symbol']):
            continue
        if filters.get('timeframe') and item.get('timeframe') not in (None, filters['timeframe']):
            continue
        if filters.get('search') and filters['search'].lower() not in line.lower():
            continue
        out.append(item)
        if len(out) >= limit:
            break
    return out


def get_live_signals(filters: dict | None = None, limit: int = 120) -> list[dict]:
    filters = filters or {}
    lines = tail_lines(latest_fusion_log(), max_lines=2500)
    signals = []
    blocked = {}
    latest_timing = {}
    for idx, line in enumerate(lines):
        ts = parse_log_ts(line)
        m = SIGNAL_RE.search(line)
        if m:
            direction, symbol, tf, p_buy, p_sell = m.groups()
            p_buy_f = float(p_buy)
            p_sell_f = float(p_sell)
            key = (symbol, tf, direction, len(signals))
            signals.append({
                'id': f'{symbol}_{tf}_{idx}',
                'symbol': symbol,
                'timeframe': tf,
                'decision': direction,
                'p_buy': p_buy_f,
                'p_sell': p_sell_f,
                'confidence': max(p_buy_f, p_sell_f),
                'edge': abs(p_buy_f - p_sell_f),
                'strategy': '',
                'status': 'liberado',
                'reason': '',
                'timestamp': ts,
            })
            continue
        m = NO_ORDER_RE.search(line)
        if m:
            strat, symbol, tf, direction, reason = m.groups()
            blocked[(symbol, tf, direction)] = reason
            for s in reversed(signals):
                if s['symbol'] == symbol and s['timeframe'] == tf and s['decision'] == direction:
                    s['status'] = 'bloqueado'
                    s['reason'] = reason
                    s['strategy'] = f'S{strat}'
                    break
            continue
        m = TIMING_RE.search(line)
        if m:
            _, symbol, tf, duration, status, signal_code = m.groups()
            latest_timing[(symbol, tf)] = (ts, duration, status, signal_code)
    for s in signals:
        key = (s['symbol'], s['timeframe'])
        if key in latest_timing:
            s['analysis_duration_s'] = float(latest_timing[key][1])
            s['raw_status'] = latest_timing[key][2]
        if filters.get('symbol') and s['symbol'] != filters['symbol']:
            s['_skip'] = True
        if filters.get('timeframe') and s['timeframe'] != filters['timeframe']:
            s['_skip'] = True
        if filters.get('direction') and filters['direction'] != 'ALL' and s['decision'] != filters['direction']:
            s['_skip'] = True
        if filters.get('status') and s['status'] != filters['status']:
            s['_skip'] = True
        if filters.get('min_confidence') and s['confidence'] < float(filters['min_confidence']):
            s['_skip'] = True
    return [s for s in reversed(signals) if not s.pop('_skip', False)][:limit]


def get_filter_status() -> list[dict]:
    runtime = get_runtime_control()
    modes = runtime.get('filters', {}) if isinstance(runtime.get('filters'), dict) else {}
    lines = tail_lines(latest_fusion_log(), max_lines=3000)
    stats = {name: {'total_blocks': 0, 'shadow': 0, 'last_reason': ''} for name in FILTER_NAMES}
    for line in lines:
        m = FILTER_RE.search(line)
        if not m:
            continue
        _, _, _, name, mode, details = m.groups()
        stats.setdefault(name, {'total_blocks': 0, 'shadow': 0, 'last_reason': ''})
        if mode == 'block':
            stats[name]['total_blocks'] += 1
        else:
            stats[name]['shadow'] += 1
        stats[name]['last_reason'] = details[:180]
    out = []
    for name in sorted(set(FILTER_NAMES) | set(k.replace('_mode', '') for k in modes.keys())):
        mode = modes.get(f'{name}_mode', modes.get(name, 'shadow'))
        st = stats.get(name, {})
        total = int(st.get('total_blocks', 0))
        shadow = int(st.get('shadow', 0))
        out.append({
            'name': name,
            'mode': mode if mode in {'block', 'shadow', 'off'} else 'shadow',
            'total_blocks': total,
            'good_blocks': 0,
            'bad_blocks': 0,
            'profit_lost': 0,
            'loss_avoided': 0,
            'recommendation': 'monitorar' if total or shadow else 'sem dados recentes',
            'last_reason': st.get('last_reason', ''),
            'shadow_events': shadow,
        })
    return out


def update_filter_mode(filter_name: str, mode: str) -> dict:
    if mode not in {'block', 'shadow', 'off'}:
        raise ValueError('invalid mode')
    return patch_runtime_control(f'filters.{filter_name}_mode', mode)


def get_system_status(mt5_health: dict | None = None) -> dict:
    log = latest_fusion_log()
    lines = tail_lines(log, 500)
    last_cycle = None
    last_duration = None
    last_signal = None
    for line in reversed(lines):
        if last_cycle is None and '[LOOP]' in line:
            last_cycle = parse_log_ts(line)
        if last_duration is None and 'loop.batch_process' in line:
            m = re.search(r'\|\s*([0-9.]+)s\s*\|', line)
            if m:
                last_duration = float(m.group(1)) * 1000
        if last_signal is None:
            sm = SIGNAL_RE.search(line)
            if sm:
                direction, symbol, tf, *_ = sm.groups()
                last_signal = {'symbol': symbol, 'timeframe': tf, 'direction': direction, 'ts': parse_log_ts(line)}
        if last_cycle and last_duration and last_signal:
            break
    runtime = get_runtime_control()
    raw_symbols = runtime.get('symbols', [])
    if isinstance(raw_symbols, dict):
        monitored_symbols = raw_symbols.get('include') or raw_symbols.get('monitored') or raw_symbols.get('enabled') or []
    elif isinstance(raw_symbols, list):
        monitored_symbols = raw_symbols
    else:
        monitored_symbols = []
    raw_timeframes = runtime.get('timeframes') or runtime.get('monitor_timeframes') or []
    monitored_timeframes = raw_timeframes if isinstance(raw_timeframes, list) and raw_timeframes else ['M5', 'M15', 'M30', 'H1', 'H4', 'D1']
    return {
        'fusion': {'status': 'online' if log and log.exists() else 'offline', 'last_cycle': last_cycle, 'cycle_duration_ms': last_duration or 0},
        'mt5': {'status': 'online' if (mt5_health or {}).get('mt5_ready') else 'offline', 'account': '', 'server': ''},
        'backend': {'status': 'online', 'latency_ms': 0},
        'feed': {'status': 'online' if (mt5_health or {}).get('mt5_ready') else 'offline', 'last_candle': now_iso(), 'candles_per_min': 0},
        'symbols_monitored': monitored_symbols,
        'timeframes_monitored': monitored_timeframes,
        'open_orders': 0,
        'last_signal': last_signal,
        'last_order': None,
        'last_critical_error': None,
        'simulated_latency_ms': 0,
    }


def get_market_briefing() -> dict:
    data = safe_json(MARKET_BRIEFING_PATH, {})
    if not isinstance(data, dict):
        data = {}
    valid_until = data.get('valid_until')
    expired = False
    if valid_until:
        try:
            expired = datetime.fromisoformat(str(valid_until).replace('Z', '+00:00')) < datetime.now().astimezone()
        except Exception:
            expired = False
    data.setdefault('summary', '')
    data.setdefault('risk_regime', '')
    data.setdefault('currency_bias', {})
    data.setdefault('pair_bias', {})
    data.setdefault('asset_bias', {})
    data.setdefault('macro_rules', data.get('rules', []))
    data['is_expired'] = expired
    data['last_updated'] = data.get('date') or ''
    return data


def update_market_briefing(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError('payload must be object')
    write_json(MARKET_BRIEFING_PATH, payload)
    return get_market_briefing()


def read_csv_rows(path: Path) -> list[dict]:
    try:
        with path.open('r', encoding='utf-8', errors='replace', newline='') as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def read_signal_panel_csv(symbol: str = '') -> tuple[list[dict], Path | None]:
    for path in symbol_file_candidates('fusion_signal_panel_', symbol):
        if path.exists():
            return read_csv_rows(path), path
    for path in SIGNAL_PANEL_PATHS:
        if path.exists():
            return read_csv_rows(path), path
    return [], None


def read_trade_zones_csv(symbol: str = '') -> tuple[list[dict], Path | None]:
    for path in symbol_file_candidates('fusion_trade_zones_', symbol):
        if path.exists():
            return read_csv_rows(path), path
    return [], None


def zone_center(row: dict) -> float:
    try:
        return (float(row.get('price1') or 0) + float(row.get('price2') or 0)) / 2.0
    except Exception:
        return 0.0


def signal_status(signal: str, reason: str, alert_signal: str = '') -> str:
    if signal == 'WAIT':
        return 'wait'
    text = (reason or '').lower()
    if 'risk_engine' in text or 'bloque' in text or 'blocked' in text:
        return 'blocked'
    if alert_signal and alert_signal in {'BUY', 'SELL'}:
        return 'allowed'
    return 'shadow' if 'shadow' in text else 'allowed'


def get_signal_panel(symbol: str, timeframe: str) -> dict:
    tf = (timeframe or '').upper()
    rows, panel_path = read_signal_panel_csv(symbol)
    zones, zones_path = read_trade_zones_csv(symbol)
    row = next((r for r in rows if str(r.get('timeframe', '')).upper() == tf), None)
    if not row and tf != 'FINAL':
        row = next((r for r in rows if str(r.get('timeframe', '')).upper() == 'FINAL'), None)
    if not row:
        sigs = get_live_signals({'symbol': symbol, 'timeframe': tf}, 1)
        if sigs:
            sig = sigs[0]
            signal = sig['decision']
            p_buy = sig['p_buy']
            p_sell = sig['p_sell']
            p_wait = max(0.0, 1.0 - p_buy - p_sell)
            reason = sig.get('reason') or 'Fusion log signal'
            alert_signal = ''
        else:
            signal, p_buy, p_sell, p_wait, reason, alert_signal = 'WAIT', 0, 0, 1, 'Sem sinal recente', ''
    else:
        signal = str(row.get('signal') or 'WAIT').upper()
        alert_signal = str(row.get('alert_signal') or '').upper()
        p_buy = float(row.get('p_buy') or 0)
        p_sell = float(row.get('p_sell') or 0)
        p_wait = float(row.get('p_wait') or max(0.0, 1.0 - p_buy - p_sell))
        reason = row.get('alert_reason') or row.get('reason') or ''

    tf_zones = [z for z in zones if str(z.get('timeframe', '')).upper() == tf]
    support_levels = [zone_center(z) for z in tf_zones if str(z.get('type', '')).upper() == 'SUPPORT']
    resistance_levels = [zone_center(z) for z in tf_zones if str(z.get('type', '')).upper() == 'RESISTANCE']
    entry = next((zone_center(z) for z in tf_zones if str(z.get('type', '')).upper() == 'ENTRY_ZONE'), 0.0)
    stop_loss = next((zone_center(z) for z in tf_zones if str(z.get('type', '')).upper() == 'SL_ZONE'), 0.0)
    take_profit = next((zone_center(z) for z in tf_zones if str(z.get('type', '')).upper() == 'TP_ZONE'), 0.0)

    confidence = round(max(p_buy, p_sell, p_wait if signal == 'WAIT' else 0) * 100)
    clean_signal = signal if signal in {'BUY', 'SELL', 'WAIT'} else 'WAIT'
    return {
        'symbol': (symbol or '').upper(),
        'timeframe': tf,
        'signal': clean_signal,
        'status': signal_status(clean_signal, reason, alert_signal),
        'confidence': confidence,
        'analysis_time': datetime.now().strftime('%H:%M:%S'),
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit': take_profit,
        'support_levels': support_levels,
        'resistance_levels': resistance_levels,
        'reason': reason,
        'strategy': alert_signal or '',
        'p_buy': p_buy,
        'p_sell': p_sell,
        'p_wait': p_wait,
        'updated_at': now_iso(),
        'source_files': {
            'signal_panel': str(panel_path) if panel_path else '',
            'trade_zones': str(zones_path) if zones_path else '',
        },
    }


def get_alerts() -> list[dict]:
    alerts = []
    status = get_system_status({})
    if status['fusion']['status'] != 'online':
        alerts.append({'id': 'fusion_offline', 'type': 'fusion_no_cycle', 'severity': 'error', 'message': 'Fusion sem log ativo', 'timestamp': now_iso(), 'acknowledged': False})
    for log in get_logs({'type': 'erro'}, 10):
        alerts.append({'id': log['id'], 'type': 'error_log', 'severity': 'error', 'message': log['message'], 'timestamp': log['timestamp'], 'acknowledged': False})
    return alerts


def get_models() -> list[dict]:
    out = []
    for folder in MODEL_DIRS:
        if not folder.exists():
            continue
        for path in list(folder.rglob('*.pkl'))[:200]:
            out.append({
                'id': path.stem,
                'name': path.stem,
                'symbol': '',
                'timeframe': '',
                'path': str(path),
                'version': '',
                'loaded': True,
                'status': 'disponivel',
                'last_prediction': None,
                'avg_confidence': None,
                'error': None,
            })
    return out[:200]


def get_open_orders() -> list[dict]:
    # Filled by frontend as empty until MT5 trade endpoint is added.
    return []


def get_performance() -> dict:
    return {'by_symbol': [], 'by_timeframe': [], 'by_strategy': [], 'totals': {'total_signals': len(get_live_signals({}, 500)), 'signals_blocked': 0, 'signals_executed': 0, 'total_profit': 0, 'win_rate': 0, 'drawdown': 0}}


def get_filter_performance() -> list[dict]:
    return [{'filter': f['name'], 'total_blocks': f['total_blocks'], 'good_blocks': 0, 'bad_blocks': 0, 'profit_lost': 0, 'loss_avoided': 0, 'recommendation': f['recommendation']} for f in get_filter_status()]


def get_block_audit() -> list[dict]:
    rows = []
    lines = tail_lines(latest_fusion_log(), max_lines=4000)
    for idx, line in enumerate(reversed(lines)):
        m = NO_ORDER_RE.search(line)
        if not m:
            continue
        strat, symbol, tf, direction, reason = m.groups()
        filter_name = str(reason).split(':', 1)[0] if reason else 'unknown'
        rows.append({
            'id': f'block_{idx}',
            'timestamp': parse_log_ts(line),
            'symbol': symbol,
            'timeframe': tf,
            'direction': direction,
            'strategy': f'S{strat}',
            'filter': filter_name,
            'reason': reason,
            'price_at_block': 0,
            'price_after_15m': 0,
            'price_after_1h': 0,
            'price_after_3h': 0,
            'result_points': 0,
            'classification': 'pendente',
            'profit_lost': 0.0,
            'loss_avoided': 0.0,
        })
        if len(rows) >= 300:
            break
    return rows


def get_chart_overlays(symbol: str, timeframe: str) -> dict:
    panel = get_signal_panel(symbol, timeframe)
    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'entries': [{'price': panel['entry'], 'direction': panel['signal'], 'ts': panel['updated_at']}] if panel['entry'] else [],
        'exits': [],
        'sl_levels': [{'price': panel['stop_loss']}] if panel['stop_loss'] else [],
        'tp_levels': [{'price': panel['take_profit']}] if panel['take_profit'] else [],
        'support_resistance': [{'price': p, 'type': 'support'} for p in panel['support_levels']] + [{'price': p, 'type': 'resistance'} for p in panel['resistance_levels']],
        'signals': [{'price': panel['entry'], 'direction': panel['signal'], 'blocked': panel['status'] == 'blocked', 'reason': panel['reason'], 'ts': panel['updated_at']}] if panel['signal'] != 'WAIT' else [],
    }






