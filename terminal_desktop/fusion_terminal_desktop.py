from __future__ import annotations

import csv
import json
import math
import threading
import time
import tkinter as tk
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
COLORS = {
    "bg": "#071019",
    "panel": "#0d1722",
    "panel_2": "#101c2b",
    "header": "#152235",
    "border": "#26374d",
    "grid": "#1d2b3d",
    "text": "#d7e2ee",
    "muted": "#8fa4b8",
    "primary": "#38bdf8",
    "up": "#2dd4a7",
    "down": "#fb5a68",
    "buy": "#f3b64c",
    "sell": "#ef4444",
    "warn": "#f59e0b",
}


def latest_file(base: Path, pattern: str) -> Path | None:
    files = sorted(base.glob(pattern), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_jsonl_tail(path: Path | None, tail_bytes: int = 5_000_000) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - tail_bytes))
            if size > tail_bytes:
                handle.readline()
            chunk = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    events = []
    for line in chunk.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def raw_data(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data") or {}
    return data if isinstance(data, dict) else {}


def normalize_symbol(symbol: Any) -> str:
    value = str(symbol or "").upper().replace("/", "")
    return "GOLD" if value == "XAUUSD" else value


def broker_symbol(symbol: str) -> str:
    return "GOLD" if normalize_symbol(symbol) == "GOLD" else normalize_symbol(symbol)


def event_symbol(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return normalize_symbol(data.get("symbol") or candidate.get("symbol"))


def event_timeframe(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return str(data.get("timeframe") or candidate.get("timeframe") or "").upper()


def event_direction(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return str(data.get("direction") or candidate.get("side") or "").upper()


def event_probabilities(event: dict[str, Any]) -> tuple[float, float]:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    try:
        p_buy = float(data.get("p_buy", candidate.get("p_buy", 0.0)) or 0.0)
        p_sell = float(data.get("p_sell", candidate.get("p_sell", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return 0.0, 0.0
    return p_buy, p_sell


def event_reason(event: dict[str, Any]) -> str:
    data = raw_data(event)
    result = data.get("result") or {}
    reason = data.get("reason") or result.get("reason") or result.get("decision") or data.get("status") or ""
    return str(reason or "-")


def normalize_oms(snapshot: dict[str, Any]) -> dict[str, Any]:
    oms = snapshot.get("oms", snapshot)
    return oms if isinstance(oms, dict) else {}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def fmt_price(value: Any) -> str:
    number = safe_float(value, math.nan)
    if not math.isfinite(number):
        return "-"
    return f"{number:.5f}" if abs(number) < 10 else f"{number:.2f}"


def fmt_pnl(value: Any) -> str:
    return f"{safe_float(value):+.2f}"


def latest_ohlc_csv(symbol: str, timeframe: str) -> Path | None:
    tf_dir = ROOT / "data" / "csv" / timeframe.upper()
    symbols = [broker_symbol(symbol), normalize_symbol(symbol)]
    if normalize_symbol(symbol) == "GOLD":
        symbols.extend(["XAUUSD", "GOLD"])
    candidates: list[Path] = []
    for item in dict.fromkeys(symbols):
        candidates.extend(tf_dir.glob(f"**/{item}.csv"))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def read_ohlc(symbol: str, timeframe: str, bars: int = 180) -> list[dict[str, Any]]:
    path = latest_ohlc_csv(symbol, timeframe)
    if not path:
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                try:
                    rows.append(
                        {
                            "time": row.get("time") or row.get("date") or "",
                            "open": float(row.get("open", 0) or 0),
                            "high": float(row.get("high", 0) or 0),
                            "low": float(row.get("low", 0) or 0),
                            "close": float(row.get("close", 0) or 0),
                            "volume": float(row.get("tick_volume", row.get("volume", 0)) or 0),
                        }
                    )
                except (TypeError, ValueError):
                    continue
    except OSError:
        return []
    return rows[-bars:]


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("T", " ").replace("Z", "")
    if "." in text:
        text = text.split(".", 1)[0]
    for fmt, size in (("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d %H:%M", 16), ("%Y-%m-%d", 10)):
        try:
            return datetime.strptime(text[:size], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def moving_average(rows: list[dict[str, Any]], period: int) -> list[float | None]:
    values = [safe_float(row.get("close"), math.nan) for row in rows]
    out: list[float | None] = []
    rolling = 0.0
    window: list[float] = []
    for value in values:
        if not math.isfinite(value):
            out.append(None)
            continue
        window.append(value)
        rolling += value
        if len(window) > period:
            rolling -= window.pop(0)
        out.append(rolling / period if len(window) == period else None)
    return out


def event_marker_time(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    result = data.get("result") or {}
    for engine in data.get("engines") or []:
        features = engine.get("features") or {}
        if features.get("signal_candle_time"):
            return str(features.get("signal_candle_time"))
    return str(
        data.get("signal_candle_time")
        or candidate.get("timestamp")
        or data.get("timestamp")
        or result.get("timestamp")
        or event.get("timestamp")
        or ""
    )


def event_marker_direction(event: dict[str, Any]) -> str:
    direction = event_direction(event)
    if direction:
        return direction
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return str(candidate.get("side") or "").upper()


def event_marker_status(event: dict[str, Any]) -> str:
    data = raw_data(event)
    result = data.get("result") or {}
    if event.get("type") == "SIGNAL":
        return "SIGNAL"
    return str(result.get("decision") or data.get("status") or event.get("type") or "").upper()


def event_marker_score(event: dict[str, Any]) -> float:
    p_buy, p_sell = event_probabilities(event)
    data = raw_data(event)
    result = data.get("result") or {}
    return max(p_buy, p_sell, safe_float(result.get("tradeability_score")), safe_float(result.get("consensus_score")))


class FusionTerminalDesktop(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Fusion ProfitDesk - Monitor Read-Only")
        self.geometry("1560x900")
        self.minsize(1200, 720)
        self.configure(bg=COLORS["bg"])
        self._stop_event = threading.Event()
        self._latest_payload: dict[str, Any] = {}
        self._last_alert_key = ""
        self.selected_symbol = tk.StringVar(value="GOLD")
        self.selected_timeframe = tk.StringVar(value="M15")
        self._last_chart_key = ""
        self._last_payload_key = ""
        self._last_table_key = ""
        self.show_ema = tk.BooleanVar(value=True)
        self.show_signals = tk.BooleanVar(value=True)
        self.show_positions = tk.BooleanVar(value=True)
        self.show_trailing = tk.BooleanVar(value=True)
        self.crosshair_enabled = tk.BooleanVar(value=False)
        self.cursor_mode = tk.StringVar(value="Cursor")
        self._crosshair_items: list[int] = []
        self._build_style()
        self._build_ui()
        self._worker = threading.Thread(target=self._reader_loop, daemon=True)
        self._worker.start()
        self.after(500, self._refresh_ui)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=COLORS["bg"], foreground=COLORS["text"], fieldbackground=COLORS["panel"])
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"], relief="flat")
        style.configure("Header.TFrame", background=COLORS["header"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
        style.configure("Panel.TLabel", background=COLORS["panel"], foreground=COLORS["text"])
        style.configure("Muted.TLabel", foreground=COLORS["muted"], background=COLORS["panel"])
        style.configure("Header.TLabel", background=COLORS["header"], foreground=COLORS["text"])
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#f8fafc", background=COLORS["header"])
        style.configure("Metric.TLabel", font=("Segoe UI", 12, "bold"), foreground="#f8fafc", background=COLORS["panel"])
        style.configure("Small.TLabel", font=("Segoe UI", 9), foreground=COLORS["muted"], background=COLORS["panel"])
        style.configure("TButton", background=COLORS["panel_2"], foreground=COLORS["text"], borderwidth=1, focusthickness=0)
        style.map("TButton", background=[("active", COLORS["border"])])
        style.configure("TNotebook", background=COLORS["panel"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["header"], foreground=COLORS["muted"], padding=(12, 5))
        style.map("TNotebook.Tab", background=[("selected", COLORS["panel"])], foreground=[("selected", COLORS["text"])])
        style.configure("Treeview", background=COLORS["panel"], fieldbackground=COLORS["panel"], foreground=COLORS["text"], rowheight=24, borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["header"], foreground="#f8fafc", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#1e3a5f")], foreground=[("selected", "#ffffff")])

    def _build_ui(self) -> None:
        self._build_top_bars()
        self._build_workspace()
        self._build_status_bar()

    def _build_top_bars(self) -> None:
        menu = ttk.Frame(self, style="Header.TFrame", padding=(8, 4))
        menu.pack(fill="x")
        ttk.Label(menu, text="Fusion", style="Title.TLabel").pack(side="left")
        ttk.Label(menu, text=" ProfitDesk", style="Title.TLabel", foreground=COLORS["primary"]).pack(side="left")
        for item in ["Arquivo", "Exibir", "Estudos", "Ferramentas", "Cotações", "Estratégias", "Alertas", "Config"]:
            ttk.Label(menu, text=item, style="Header.TLabel", padding=(12, 0)).pack(side="left")
        self.connection_label = ttk.Label(menu, text="Conectando...", style="Header.TLabel")
        self.connection_label.pack(side="right")

        toolbar = ttk.Frame(self, style="Header.TFrame", padding=(8, 3))
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Atualizar", command=self._manual_refresh).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Cursor", command=lambda: self._set_cursor_mode("Cursor")).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Crosshair", command=self._toggle_crosshair).pack(side="left", padx=2)
        ttk.Button(toolbar, text="EMA", command=lambda: self._toggle_overlay(self.show_ema)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Sinais", command=lambda: self._toggle_overlay(self.show_signals)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Posições", command=lambda: self._toggle_overlay(self.show_positions)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Trailing", command=lambda: self._toggle_overlay(self.show_trailing)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Replay", command=self._show_replay_placeholder).pack(side="left", padx=2)
        ttk.Label(toolbar, text="Ativo", style="Header.TLabel", padding=(12, 0)).pack(side="left")
        self.symbol_combo = ttk.Combobox(toolbar, textvariable=self.selected_symbol, width=12, state="readonly")
        self.symbol_combo.pack(side="left", padx=2)
        self.symbol_combo.bind("<<ComboboxSelected>>", lambda _event: self._redraw_chart(force=True))
        ttk.Label(toolbar, text="TF", style="Header.TLabel", padding=(8, 0)).pack(side="left")
        self.tf_combo = ttk.Combobox(toolbar, textvariable=self.selected_timeframe, values=TIMEFRAMES, width=6, state="readonly")
        self.tf_combo.pack(side="left", padx=2)
        self.tf_combo.bind("<<ComboboxSelected>>", lambda _event: self._redraw_chart(force=True))
        for tf in TIMEFRAMES:
            ttk.Button(toolbar, text=tf, command=lambda value=tf: self._select_timeframe(value)).pack(side="left", padx=1)

        self.ribbon = tk.Canvas(self, height=28, bg=COLORS["panel"], highlightthickness=0)
        self.ribbon.pack(fill="x")

    def _build_workspace(self) -> None:
        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, style="Panel.TFrame", padding=6)
        center = ttk.Frame(main, style="Panel.TFrame")
        right = ttk.Frame(main, style="Panel.TFrame", padding=6)
        main.add(left, weight=1)
        main.add(center, weight=4)
        main.add(right, weight=1)

        self._build_left_panel(left)
        self._build_center_panel(center)
        self._build_right_panel(right)

    def _build_left_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Watchlist", style="Metric.TLabel").pack(anchor="w", pady=(0, 6))
        self.watch_tree = ttk.Treeview(parent, columns=("signal", "alerts", "pos", "pnl"), show="tree headings", height=15)
        for key, label, width in [
            ("#0", "Ativo", 88),
            ("signal", "Sinal", 86),
            ("alerts", "Alertas", 54),
            ("pos", "Pos", 44),
            ("pnl", "PnL", 70),
        ]:
            self.watch_tree.heading(key, text=label)
            self.watch_tree.column(key, width=width, anchor="e" if key == "pnl" else "center")
        self.watch_tree.column("#0", anchor="w")
        self.watch_tree.pack(fill="both", expand=True)
        self.watch_tree.bind("<<TreeviewSelect>>", self._on_watch_select)

        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, pady=(8, 0))
        quotes = ttk.Frame(notebook, style="Panel.TFrame", padding=4)
        alerts = ttk.Frame(notebook, style="Panel.TFrame", padding=4)
        notebook.add(quotes, text="Cotações")
        notebook.add(alerts, text="Alertas")

        self.quotes_tree = ttk.Treeview(quotes, columns=("last", "chg", "time"), show="tree headings", height=8)
        for key, label, width in [("#0", "Ativo", 70), ("last", "Ultimo", 75), ("chg", "Var", 58), ("time", "Hora", 70)]:
            self.quotes_tree.heading(key, text=label)
            self.quotes_tree.column(key, width=width)
        self.quotes_tree.pack(fill="both", expand=True)

        self.alert_list = tk.Listbox(alerts, bg=COLORS["panel"], fg=COLORS["text"], selectbackground="#1e3a5f", relief="flat", height=8)
        self.alert_list.pack(fill="both", expand=True)

    def _build_center_panel(self, parent: ttk.Frame) -> None:
        tabbar = ttk.Frame(parent, style="Header.TFrame")
        tabbar.pack(fill="x")
        self.chart_title = ttk.Label(tabbar, text="GOLD M15", style="Title.TLabel")
        self.chart_title.pack(side="left", padx=8, pady=4)
        self.chart_status = ttk.Label(tabbar, text="OHLC local + Event Bus", style="Header.TLabel")
        self.chart_status.pack(side="right", padx=8)

        self.chart_canvas = tk.Canvas(parent, bg=COLORS["bg"], highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True)
        self.chart_canvas.bind("<Configure>", lambda _event: self._redraw_chart(force=True))
        self.chart_canvas.bind("<Motion>", self._on_chart_motion)
        self.chart_canvas.bind("<Leave>", lambda _event: self._clear_crosshair())

        bottom_tabs = ttk.Notebook(parent)
        bottom_tabs.pack(fill="both", expand=False)
        events_frame = ttk.Frame(bottom_tabs, style="Panel.TFrame", padding=4)
        engines_frame = ttk.Frame(bottom_tabs, style="Panel.TFrame", padding=4)
        audit_frame = ttk.Frame(bottom_tabs, style="Panel.TFrame", padding=4)
        bottom_tabs.add(events_frame, text="Sinais e Decisões")
        bottom_tabs.add(engines_frame, text="Engines")
        bottom_tabs.add(audit_frame, text="Auditoria")

        self.events_tree = ttk.Treeview(events_frame, columns=("time", "type", "tf", "direction", "status", "reason"), show="tree headings", height=7)
        for key, label, width in [
            ("#0", "Ativo", 85),
            ("time", "Hora", 142),
            ("type", "Tipo", 110),
            ("tf", "TF", 48),
            ("direction", "Lado", 62),
            ("status", "Status", 90),
            ("reason", "Motivo", 420),
        ]:
            self.events_tree.heading(key, text=label)
            self.events_tree.column(key, width=width)
        self.events_tree.pack(fill="both", expand=True)

        self.engines_tree = ttk.Treeview(engines_frame, columns=("tf", "state", "score", "conf", "warnings"), show="tree headings", height=7)
        for key, label, width in [
            ("#0", "Engine", 170),
            ("tf", "TF", 54),
            ("state", "Estado", 170),
            ("score", "Score", 80),
            ("conf", "Conf", 80),
            ("warnings", "Avisos", 70),
        ]:
            self.engines_tree.heading(key, text=label)
            self.engines_tree.column(key, width=width)
        self.engines_tree.pack(fill="both", expand=True)

        self.audit_text = tk.Text(audit_frame, height=7, bg=COLORS["panel"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", wrap="word")
        self.audit_text.pack(fill="both", expand=True)

    def _build_right_panel(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Painel do Ativo", style="Metric.TLabel").pack(anchor="w")
        self.asset_title = ttk.Label(parent, text="GOLD", style="Title.TLabel", background=COLORS["panel"])
        self.asset_title.pack(anchor="w", pady=(4, 8))

        self.tf_score_frame = ttk.Frame(parent, style="Panel.TFrame")
        self.tf_score_frame.pack(fill="x")
        self.tf_score_labels: dict[str, ttk.Label] = {}
        for tf in TIMEFRAMES:
            frame = ttk.Frame(self.tf_score_frame, style="Panel.TFrame", padding=(0, 3))
            frame.pack(fill="x")
            ttk.Label(frame, text=tf, style="Muted.TLabel", width=5).pack(side="left")
            label = ttk.Label(frame, text="-/-", style="Panel.TLabel")
            label.pack(side="left", fill="x", expand=True)
            self.tf_score_labels[tf] = label

        ttk.Label(parent, text="Posições", style="Metric.TLabel").pack(anchor="w", pady=(12, 6))
        self.positions_tree = ttk.Treeview(parent, columns=("dir", "vol", "open", "current", "pnl"), show="tree headings", height=8)
        for key, label, width in [
            ("#0", "Ativo", 72),
            ("dir", "Dir", 45),
            ("vol", "Vol", 48),
            ("open", "Entrada", 70),
            ("current", "Atual", 70),
            ("pnl", "PnL", 64),
        ]:
            self.positions_tree.heading(key, text=label)
            self.positions_tree.column(key, width=width)
        self.positions_tree.pack(fill="both", expand=True)

        ttk.Label(parent, text="Resumo", style="Metric.TLabel").pack(anchor="w", pady=(12, 6))
        self.summary_text = tk.Text(parent, height=10, bg=COLORS["panel"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", wrap="word")
        self.summary_text.pack(fill="both", expand=True)

    def _build_status_bar(self) -> None:
        status = ttk.Frame(self, style="Header.TFrame", padding=(8, 3))
        status.pack(fill="x", side="bottom")
        self.status_label = ttk.Label(status, text="Inicializando...", style="Header.TLabel")
        self.status_label.pack(side="left")
        self.system_label = ttk.Label(status, text="Read-only | Monitor", style="Header.TLabel")
        self.system_label.pack(side="right")

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            events_path = latest_file(ROOT / "logs" / "events", "events_*.jsonl")
            oms_path = latest_file(ROOT / "logs" / "oms", "oms_snapshot_*.json")
            events = read_jsonl_tail(events_path, tail_bytes=2_500_000)
            oms = normalize_oms(read_json(oms_path))
            self._latest_payload = {
                "events_path": events_path,
                "oms_path": oms_path,
                "events": events,
                "oms": oms,
                "read_at": time.strftime("%H:%M:%S"),
            }
            self._maybe_beep(events)
            self._stop_event.wait(2)

    def _load_payload_once(self) -> None:
        events_path = latest_file(ROOT / "logs" / "events", "events_*.jsonl")
        oms_path = latest_file(ROOT / "logs" / "oms", "oms_snapshot_*.json")
        events = read_jsonl_tail(events_path, tail_bytes=2_500_000)
        oms = normalize_oms(read_json(oms_path))
        self._latest_payload = {
            "events_path": events_path,
            "oms_path": oms_path,
            "events": events,
            "oms": oms,
            "read_at": time.strftime("%H:%M:%S"),
        }

    def _manual_refresh(self) -> None:
        self._load_payload_once()
        self._last_chart_key = ""
        self._last_payload_key = ""
        self._last_table_key = ""
        self._refresh_ui()

    def _maybe_beep(self, events: list[dict[str, Any]]) -> None:
        recent = [event for event in events if event.get("type") in {"SIGNAL", "ORDER_RESULT", "POSITION_UPDATE"}]
        if not recent:
            return
        latest = recent[-1]
        key = str(latest.get("event_id") or latest.get("correlation_id") or latest.get("timestamp"))
        if key and key != self._last_alert_key:
            self._last_alert_key = key
            try:
                self.bell()
            except tk.TclError:
                pass

    def _refresh_ui(self) -> None:
        payload = self._latest_payload
        events = payload.get("events", []) or []
        oms = payload.get("oms", {}) or {}
        payload_key = (
            str(payload.get("read_at", "")),
            str(events[-1].get("event_id") or events[-1].get("timestamp") or "") if events else "",
            len(oms.get("positions", []) or []),
        )
        tables_changed = payload_key != self._last_table_key
        self._update_symbols(events, oms)
        self._update_metrics(events, oms, payload)
        if tables_changed:
            self._update_ribbon(events, oms)
            self._update_watchlist(events, oms)
            self._update_quotes(events, oms)
            self._update_events(events)
            self._update_positions(oms)
            self._last_table_key = payload_key
        self._update_engines(events)
        self._update_asset_panel(events, oms)
        self._redraw_chart()
        self.after(1500, self._refresh_ui)

    def _update_symbols(self, events: list[dict[str, Any]], oms: dict[str, Any]) -> None:
        symbols = set()
        for event in events:
            symbol = event_symbol(event)
            if symbol:
                symbols.add(symbol)
        for position in oms.get("positions", []) or []:
            symbols.add(normalize_symbol(position.get("symbol") or position.get("broker_symbol")))
        values = sorted(symbols)
        if not values:
            values = ["GOLD"]
        if tuple(self.symbol_combo["values"]) != tuple(values):
            self.symbol_combo.configure(values=values)
        if self.selected_symbol.get() not in values:
            self.selected_symbol.set(values[0])

    def _update_metrics(self, events: list[dict[str, Any]], oms: dict[str, Any], payload: dict[str, Any]) -> None:
        positions = oms.get("positions", []) or []
        total_pnl = sum(safe_float(item.get("profit")) for item in positions)
        signal_count = sum(1 for event in events if event.get("type") == "SIGNAL")
        latest_event = events[-1].get("timestamp", "-") if events else "-"
        events_path = payload.get("events_path")
        oms_path = payload.get("oms_path")
        self.connection_label.configure(text=f"Conectado | Eventos {len(events)} | Pos {len(positions)} | PnL {total_pnl:+.2f}")
        self.status_label.configure(
            text=f"Fonte: {events_path.name if events_path else 'sem events'} | OMS: {oms_path.name if oms_path else 'sem snapshot'} | Atualizado {payload.get('read_at', '-')}"
        )
        self.system_label.configure(text=f"Sinais {signal_count} | Último {str(latest_event)[-19:]}")

    def _set_cursor_mode(self, mode: str) -> None:
        self.cursor_mode.set(mode)
        if mode != "Crosshair":
            self.crosshair_enabled.set(False)
            self._clear_crosshair()
        self.status_label.configure(text=f"Ferramenta ativa: {mode}")

    def _toggle_crosshair(self) -> None:
        enabled = not self.crosshair_enabled.get()
        self.crosshair_enabled.set(enabled)
        self.cursor_mode.set("Crosshair" if enabled else "Cursor")
        if not enabled:
            self._clear_crosshair()
        self.status_label.configure(text=f"Crosshair {'ligado' if enabled else 'desligado'}")

    def _toggle_overlay(self, flag: tk.BooleanVar) -> None:
        flag.set(not flag.get())
        self._last_chart_key = ""
        self._redraw_chart(force=True)

    def _select_timeframe(self, timeframe: str) -> None:
        self.selected_timeframe.set(timeframe)
        self._last_chart_key = ""
        self._redraw_chart(force=True)

    def _show_replay_placeholder(self) -> None:
        self.audit_text.delete("1.0", "end")
        self.audit_text.insert(
            "end",
            "Replay visual ainda nao esta ativo.\n\nProximo passo: selecionar data, ativo e navegar evento a evento pelo Event Bus.",
        )

    def _on_chart_motion(self, event: tk.Event) -> None:
        if not self.crosshair_enabled.get():
            return
        self._clear_crosshair()
        width = self.chart_canvas.winfo_width()
        height = self.chart_canvas.winfo_height()
        self._crosshair_items = [
            self.chart_canvas.create_line(event.x, 0, event.x, height, fill=COLORS["border"], dash=(3, 4)),
            self.chart_canvas.create_line(0, event.y, width, event.y, fill=COLORS["border"], dash=(3, 4)),
        ]

    def _clear_crosshair(self) -> None:
        for item in self._crosshair_items:
            try:
                self.chart_canvas.delete(item)
            except tk.TclError:
                pass
        self._crosshair_items = []

    def _build_symbol_model(self, events: list[dict[str, Any]], oms: dict[str, Any]) -> dict[str, dict[str, Any]]:
        model: dict[str, dict[str, Any]] = defaultdict(lambda: {"signals": {}, "alerts": 0, "positions": 0, "pnl": 0.0, "last": None, "last_time": ""})
        for event in events:
            symbol = event_symbol(event)
            if not symbol:
                continue
            item = model[symbol]
            if event.get("type") == "SIGNAL":
                tf = event_timeframe(event)
                p_buy, p_sell = event_probabilities(event)
                direction = event_direction(event)
                item["signals"][tf] = {"direction": direction, "p_buy": p_buy, "p_sell": p_sell, "timestamp": event.get("timestamp", "")}
                item["last"] = max(p_buy, p_sell)
                item["last_time"] = str(event.get("timestamp", ""))[-8:]
            elif event.get("type") == "DECISION" and "BLOCK" in event_reason(event).upper():
                item["alerts"] += 1
        for position in oms.get("positions", []) or []:
            symbol = normalize_symbol(position.get("symbol") or position.get("broker_symbol"))
            item = model[symbol]
            item["positions"] += 1
            item["pnl"] += safe_float(position.get("profit"))
            item["last"] = safe_float(position.get("price_current"), item.get("last") or 0.0)
        return model

    def _update_ribbon(self, events: list[dict[str, Any]], oms: dict[str, Any]) -> None:
        model = self._build_symbol_model(events, oms)
        self.ribbon.delete("all")
        x = 8
        for symbol in sorted(model)[:36]:
            item = model[symbol]
            pnl = safe_float(item.get("pnl"))
            color = COLORS["up"] if pnl >= 0 else COLORS["down"]
            text = f"{symbol} {pnl:+.2f}" if item.get("positions") else f"{symbol}"
            self.ribbon.create_text(x, 14, text=text, fill=color if item.get("positions") else COLORS["text"], anchor="w", font=("Segoe UI", 9, "bold"))
            x += max(82, len(text) * 8)

    def _update_watchlist(self, events: list[dict[str, Any]], oms: dict[str, Any]) -> None:
        model = self._build_symbol_model(events, oms)
        rows = []
        for symbol in sorted(model):
            item = model[symbol]
            latest_signal = "-"
            if item["signals"]:
                latest_tf, sig = sorted(item["signals"].items(), key=lambda pair: str(pair[1].get("timestamp", "")))[-1]
                latest_signal = f"{sig.get('direction') or '-'} {latest_tf}"
            rows.append((symbol, latest_signal, str(item["alerts"]), str(item["positions"]), fmt_pnl(item["pnl"])))
        self._replace_tree(self.watch_tree, rows, color_pnl_index=4)

    def _update_quotes(self, events: list[dict[str, Any]], oms: dict[str, Any]) -> None:
        model = self._build_symbol_model(events, oms)
        rows = []
        for symbol in sorted(model)[:80]:
            item = model[symbol]
            rows.append((symbol, fmt_price(item.get("last")), fmt_pnl(item.get("pnl")), item.get("last_time") or "-"))
        self._replace_tree(self.quotes_tree, rows, color_pnl_index=2)

    def _update_events(self, events: list[dict[str, Any]]) -> None:
        rows = []
        alert_lines = []
        for event in events[-350:]:
            event_type = str(event.get("type", ""))
            if event_type not in {"SIGNAL", "DECISION", "ORDER_REQUEST", "ORDER_RESULT", "POSITION_UPDATE", "RISK_ALERT"}:
                continue
            rows.append(
                (
                    event_symbol(event) or "-",
                    str(event.get("timestamp", ""))[-19:],
                    event_type,
                    event_timeframe(event) or "-",
                    event_direction(event) or "-",
                    str(raw_data(event).get("status") or "-"),
                    event_reason(event)[:140],
                )
            )
        latest_rows = list(reversed(rows[-140:]))
        self._replace_tree(self.events_tree, latest_rows)
        self.alert_list.delete(0, "end")
        self.audit_text.delete("1.0", "end")
        for row in latest_rows[:40]:
            line = f"{row[1]} | {row[0]} {row[3]} | {row[2]} | {row[4]} | {row[6]}"
            alert_lines.append(line)
            if row[2] in {"SIGNAL", "ORDER_RESULT", "RISK_ALERT"}:
                self.alert_list.insert("end", line[:120])
        self.audit_text.insert("end", "\n".join(alert_lines[:80]))

    def _update_engines(self, events: list[dict[str, Any]]) -> None:
        rows = []
        seen = set()
        for event in reversed(events):
            if event.get("type") != "ENGINE_RESULT":
                continue
            data = raw_data(event)
            candidate = data.get("candidate") or {}
            engine_payload = data.get("engine") or data
            symbol = normalize_symbol(data.get("symbol") or candidate.get("symbol"))
            if symbol != normalize_symbol(self.selected_symbol.get()):
                continue
            engine = str(engine_payload.get("engine") or engine_payload.get("engine_name") or "-")
            tf = str(data.get("timeframe") or candidate.get("timeframe") or "-").upper()
            key = (engine, tf)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                (
                    engine,
                    tf,
                    str(engine_payload.get("engine_state") or engine_payload.get("state") or "-"),
                    f"{safe_float(engine_payload.get('engine_score', engine_payload.get('score')), math.nan):.3f}",
                    f"{safe_float(engine_payload.get('confidence'), math.nan):.3f}",
                    str(len(engine_payload.get("warnings") or [])),
                )
            )
            if len(rows) >= 80:
                break
        self._replace_tree(self.engines_tree, rows)

    def _update_positions(self, oms: dict[str, Any]) -> None:
        rows = []
        for position in oms.get("positions", []) or []:
            symbol = normalize_symbol(position.get("symbol") or position.get("broker_symbol"))
            rows.append(
                (
                    symbol,
                    str(position.get("direction", "-")).upper(),
                    str(position.get("volume", "-")),
                    fmt_price(position.get("price_open")),
                    fmt_price(position.get("price_current")),
                    fmt_pnl(position.get("profit")),
                )
            )
        self._replace_tree(self.positions_tree, rows, color_pnl_index=5)

    def _update_asset_panel(self, events: list[dict[str, Any]], oms: dict[str, Any]) -> None:
        symbol = normalize_symbol(self.selected_symbol.get())
        model = self._build_symbol_model(events, oms)
        item = model.get(symbol, {"signals": {}})
        self.asset_title.configure(text=symbol)
        for tf in TIMEFRAMES:
            sig = item.get("signals", {}).get(tf)
            if not sig:
                self.tf_score_labels[tf].configure(text="-/-", foreground=COLORS["muted"])
                continue
            p_buy = safe_float(sig.get("p_buy"))
            p_sell = safe_float(sig.get("p_sell"))
            direction = str(sig.get("direction") or "-")
            color = COLORS["up"] if direction == "BUY" else COLORS["down"] if direction == "SELL" else COLORS["text"]
            self.tf_score_labels[tf].configure(text=f"{direction}  B {p_buy:.3f} / S {p_sell:.3f}", foreground=color)

        positions = [p for p in oms.get("positions", []) or [] if normalize_symbol(p.get("symbol") or p.get("broker_symbol")) == symbol]
        signals = sum(1 for event in events if event.get("type") == "SIGNAL" and event_symbol(event) == symbol)
        blocks = sum(1 for event in events if event.get("type") == "DECISION" and event_symbol(event) == symbol and "BLOCK" in event_reason(event).upper())
        pnl = sum(safe_float(p.get("profit")) for p in positions)
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert(
            "end",
            "\n".join(
                [
                    f"Ativo: {symbol}",
                    f"Timeframe selecionado: {self.selected_timeframe.get()}",
                    f"Posições abertas: {len(positions)}",
                    f"PnL aberto: {pnl:+.2f}",
                    f"Sinais recentes no tail: {signals}",
                    f"Bloqueios recentes no tail: {blocks}",
                    "",
                    "Modo: monitoramento read-only.",
                    "Fonte: Event Bus + OMS snapshot + OHLC CSV local.",
                ]
            ),
        )

    def _redraw_chart(self, force: bool = False) -> None:
        symbol = normalize_symbol(self.selected_symbol.get())
        timeframe = self.selected_timeframe.get().upper()
        events = self._latest_payload.get("events", []) or []
        oms = self._latest_payload.get("oms", {}) or {}
        latest_event_key = str(events[-1].get("event_id") or events[-1].get("timestamp") or "") if events else ""
        pos_count = len(oms.get("positions", []) or [])
        key = f"{symbol}:{timeframe}:{self.chart_canvas.winfo_width()}:{self.chart_canvas.winfo_height()}:{latest_event_key}:{pos_count}"
        key = f"{key}:ema={self.show_ema.get()}:sig={self.show_signals.get()}:pos={self.show_positions.get()}:trail={self.show_trailing.get()}"
        if not force and key == self._last_chart_key:
            return
        self._last_chart_key = key
        self.chart_title.configure(text=f"{symbol} {timeframe}")
        rows = read_ohlc(symbol, timeframe, bars=180)
        self._draw_candles(rows, symbol, timeframe)

    def _draw_candles(self, rows: list[dict[str, Any]], symbol: str, timeframe: str) -> None:
        canvas = self.chart_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 800)
        height = max(canvas.winfo_height(), 360)
        pad_l, pad_r, pad_t, pad_b = 64, 70, 34, 46
        canvas.create_rectangle(0, 0, width, height, fill=COLORS["bg"], outline="")
        if not rows:
            canvas.create_text(width / 2, height / 2, text=f"Sem OHLC local para {symbol} {timeframe}", fill=COLORS["muted"], font=("Segoe UI", 14, "bold"))
            self.chart_status.configure(text="OHLC indisponível")
            return

        lows = [row["low"] for row in rows]
        highs = [row["high"] for row in rows]
        for period in (9, 21, 50):
            ma_values = [value for value in moving_average(rows, period) if value is not None]
            lows.extend(ma_values)
            highs.extend(ma_values)
        min_price, max_price = min(lows), max(highs)
        if min_price == max_price:
            min_price -= 1
            max_price += 1
        span = max_price - min_price
        min_price -= span * 0.08
        max_price += span * 0.08
        plot_w = width - pad_l - pad_r
        plot_h = height - pad_t - pad_b

        def y(price: float) -> float:
            return pad_t + (max_price - price) / (max_price - min_price) * plot_h

        for i in range(6):
            gy = pad_t + i * plot_h / 5
            price = max_price - i * (max_price - min_price) / 5
            canvas.create_line(pad_l, gy, width - pad_r, gy, fill=COLORS["grid"])
            canvas.create_text(width - pad_r + 8, gy, text=fmt_price(price), fill=COLORS["muted"], anchor="w", font=("Segoe UI", 9))
        for i in range(0, len(rows), max(1, len(rows) // 8)):
            gx = pad_l + i * plot_w / max(1, len(rows) - 1)
            canvas.create_line(gx, pad_t, gx, height - pad_b, fill=COLORS["grid"])
            label = str(rows[i]["time"])[-10:]
            canvas.create_text(gx, height - pad_b + 18, text=label, fill=COLORS["muted"], font=("Segoe UI", 8))

        step = plot_w / max(1, len(rows))
        body_w = max(3, min(9, step * 0.58))
        for i, row in enumerate(rows):
            x = pad_l + i * step + step / 2
            open_y, close_y = y(row["open"]), y(row["close"])
            high_y, low_y = y(row["high"]), y(row["low"])
            up = row["close"] >= row["open"]
            color = COLORS["up"] if up else COLORS["down"]
            canvas.create_line(x, high_y, x, low_y, fill=color, width=1)
            top, bottom = min(open_y, close_y), max(open_y, close_y)
            if bottom - top < 2:
                bottom = top + 2
            canvas.create_rectangle(x - body_w / 2, top, x + body_w / 2, bottom, fill=color, outline=color)

        if self.show_ema.get():
            self._draw_ema(canvas, rows, 9, COLORS["primary"], pad_l, step, y)
            self._draw_ema(canvas, rows, 21, COLORS["warn"], pad_l, step, y)
            self._draw_ema(canvas, rows, 50, "#d946ef", pad_l, step, y)

        latest = rows[-1]
        last_y = y(latest["close"])
        canvas.create_line(pad_l, last_y, width - pad_r, last_y, fill=COLORS["primary"], dash=(4, 4))
        canvas.create_text(width - pad_r + 8, last_y, text=fmt_price(latest["close"]), fill=COLORS["primary"], anchor="w", font=("Segoe UI", 10, "bold"))
        canvas.create_text(pad_l, 18, text=f"{symbol} · {timeframe} · O {fmt_price(latest['open'])} H {fmt_price(latest['high'])} L {fmt_price(latest['low'])} C {fmt_price(latest['close'])}", fill=COLORS["text"], anchor="w", font=("Segoe UI", 11, "bold"))
        if self.show_positions.get():
            self._draw_position_lines(canvas, symbol, y, pad_l, width - pad_r)
        if self.show_signals.get():
            self._draw_event_markers(canvas, rows, symbol, timeframe, pad_l, step, y)
        self.chart_status.configure(text=f"{len(rows)} candles | {str(latest['time'])}")

    def _draw_ema(self, canvas: tk.Canvas, rows: list[dict[str, Any]], period: int, color: str, pad_l: int, step: float, y_func: Any) -> None:
        values = moving_average(rows, period)
        points = []
        for i, value in enumerate(values):
            if value is None:
                continue
            x = pad_l + i * step + step / 2
            points.extend([x, y_func(value)])
        if len(points) >= 4:
            canvas.create_line(*points, fill=color, width=1.4, smooth=True)
            canvas.create_text(points[-2] + 4, points[-1], text=f"EMA{period}", fill=color, anchor="w", font=("Segoe UI", 8, "bold"))

    def _event_index_for_rows(self, event: dict[str, Any], rows: list[dict[str, Any]]) -> int | None:
        marker_dt = parse_dt(event_marker_time(event))
        valid = [(idx, parse_dt(row.get("time"))) for idx, row in enumerate(rows)]
        valid = [(idx, dt) for idx, dt in valid if dt is not None]
        if not rows:
            return None
        if not valid or marker_dt is None:
            return len(rows) - 1
        nearest_idx, nearest_dt = min(valid, key=lambda item: abs((item[1] - marker_dt).total_seconds()))
        if abs((nearest_dt - marker_dt).total_seconds()) <= 60 * 60 * 12:
            return nearest_idx
        return len(rows) - 1

    def _draw_event_markers(self, canvas: tk.Canvas, rows: list[dict[str, Any]], symbol: str, timeframe: str, pad_l: int, step: float, y_func: Any) -> None:
        events = self._latest_payload.get("events", []) or []
        selected = []
        for event in events:
            if event.get("type") not in {"SIGNAL", "DECISION", "ORDER_RESULT"}:
                continue
            if event_symbol(event) != normalize_symbol(symbol):
                continue
            tf = event_timeframe(event)
            if tf and tf != timeframe:
                continue
            selected.append(event)
        for event in selected[-24:]:
            idx = self._event_index_for_rows(event, rows)
            if idx is None:
                continue
            row = rows[idx]
            x = pad_l + idx * step + step / 2
            direction = event_marker_direction(event)
            status = event_marker_status(event)
            is_block = status == "BLOCK"
            is_buy = direction == "BUY"
            base_price = row["low"] if is_buy else row["high"]
            marker_y = y_func(base_price) + (16 if is_buy else -16)
            color = COLORS["warn"] if is_block else COLORS["up"] if is_buy else COLORS["down"]
            label = "BLOQ" if is_block else direction[:1] or str(event.get("type", ""))[:1]
            if is_buy:
                points = [x, marker_y - 9, x - 7, marker_y + 5, x + 7, marker_y + 5]
            else:
                points = [x, marker_y + 9, x - 7, marker_y - 5, x + 7, marker_y - 5]
            canvas.create_polygon(points, fill=color, outline=color)
            canvas.create_text(x + 10, marker_y, text=f"{label} {event_marker_score(event):.2f}", fill=color, anchor="w", font=("Segoe UI", 8, "bold"))

    def _draw_position_lines(self, canvas: tk.Canvas, symbol: str, y_func: Any, x1: int, x2: int) -> None:
        oms = self._latest_payload.get("oms", {}) or {}
        for position in oms.get("positions", []) or []:
            if normalize_symbol(position.get("symbol") or position.get("broker_symbol")) != symbol:
                continue
            price = safe_float(position.get("price_open"), math.nan)
            if not math.isfinite(price):
                continue
            line_y = y_func(price)
            direction = str(position.get("direction", "")).upper()
            color = COLORS["buy"] if direction == "BUY" else COLORS["sell"]
            canvas.create_line(x1, line_y, x2, line_y, fill=color, width=2)
            canvas.create_text(x1 + 8, line_y - 10, text=f"{direction} {fmt_price(price)} PnL {fmt_pnl(position.get('profit'))}", fill=color, anchor="w", font=("Segoe UI", 9, "bold"))
            if not self.show_trailing.get():
                continue
            for field, label, line_color in (
                ("sl", "SL", COLORS["down"]),
                ("stop_loss", "SL", COLORS["down"]),
                ("tp", "TP", COLORS["up"]),
                ("take_profit", "TP", COLORS["up"]),
                ("trailing_stop", "TRAIL", COLORS["warn"]),
            ):
                level = safe_float(position.get(field), 0.0)
                if level <= 0:
                    continue
                level_y = y_func(level)
                canvas.create_line(x1, level_y, x2, level_y, fill=line_color, dash=(3, 4))
                canvas.create_text(x2 - 8, level_y - 8, text=f"{label} {fmt_price(level)}", fill=line_color, anchor="e", font=("Segoe UI", 8, "bold"))

    def _on_watch_select(self, _event: Any) -> None:
        selection = self.watch_tree.selection()
        if not selection:
            return
        symbol = self.watch_tree.item(selection[0], "text")
        if symbol:
            self.selected_symbol.set(symbol)
            self._redraw_chart(force=True)

    @staticmethod
    def _replace_tree(tree: ttk.Treeview, rows: list[tuple[Any, ...]], color_pnl_index: int | None = None) -> None:
        tree.delete(*tree.get_children())
        tree.tag_configure("pnl_up", foreground=COLORS["up"])
        tree.tag_configure("pnl_down", foreground=COLORS["down"])
        for row in rows:
            tags = ()
            if color_pnl_index is not None and len(row) > color_pnl_index:
                tags = ("pnl_up",) if safe_float(str(row[color_pnl_index]).replace("+", "")) >= 0 else ("pnl_down",)
            tree.insert("", "end", text=str(row[0]), values=tuple(row[1:]), tags=tags)

    def _on_close(self) -> None:
        self._stop_event.set()
        self.destroy()


def main() -> None:
    app = FusionTerminalDesktop()
    app.mainloop()


if __name__ == "__main__":
    main()
