from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyqtgraph as pg
from PySide6.QtCore import QPointF, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QPen
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)


ROOT = Path(__file__).resolve().parents[1]
TIMEFRAMES = ["M5", "M15", "M30", "H1", "H4", "D1"]
COLORS = {
    "bg": "#071019",
    "panel": "#0d1722",
    "panel2": "#101c2b",
    "header": "#152235",
    "border": "#26374d",
    "grid": "#172436",
    "text": "#d7e2ee",
    "muted": "#8fa4b8",
    "primary": "#38bdf8",
    "up": "#2dd4a7",
    "down": "#fb5a68",
    "warn": "#f59e0b",
    "ema50": "#d946ef",
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


def read_jsonl_tail(path: Path | None, tail_bytes: int = 2_500_000) -> list[dict[str, Any]]:
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
    out = []
    for line in chunk.splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def normalize_symbol(symbol: Any) -> str:
    value = str(symbol or "").upper().replace("/", "")
    return "GOLD" if value == "XAUUSD" else value


def raw_data(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data") or {}
    return data if isinstance(data, dict) else {}


def event_symbol(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return normalize_symbol(data.get("symbol") or candidate.get("symbol") or data.get("broker_symbol") or candidate.get("broker_symbol"))


def event_timeframe(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return str(data.get("timeframe") or candidate.get("timeframe") or "").upper()


def event_side(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    return str(data.get("direction") or data.get("side") or candidate.get("side") or "").upper()


def event_reason(event: dict[str, Any]) -> str:
    data = raw_data(event)
    result = data.get("result") or {}
    return str(result.get("reason") or data.get("reason") or result.get("decision") or data.get("status") or "-")


def event_score(event: dict[str, Any]) -> float:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    result = data.get("result") or {}
    values = [
        safe_float(data.get("p_buy")),
        safe_float(data.get("p_sell")),
        safe_float(candidate.get("p_buy")),
        safe_float(candidate.get("p_sell")),
        safe_float(result.get("tradeability_score")),
        safe_float(result.get("consensus_score")),
    ]
    return max(values)


def event_marker_time(event: dict[str, Any]) -> str:
    data = raw_data(event)
    candidate = data.get("candidate") or {}
    for engine in data.get("engines") or []:
        features = engine.get("features") or {}
        if features.get("signal_candle_time"):
            return str(features.get("signal_candle_time"))
    return str(data.get("signal_candle_time") or candidate.get("timestamp") or data.get("timestamp") or event.get("timestamp") or "")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def normalize_oms(snapshot: dict[str, Any]) -> dict[str, Any]:
    oms = snapshot.get("oms", snapshot)
    return oms if isinstance(oms, dict) else {}


def read_ohlc(symbol: str, timeframe: str, bars: int = 320) -> list[dict[str, Any]]:
    tf_dir = ROOT / "data" / "csv" / timeframe.upper()
    names = [normalize_symbol(symbol)]
    if normalize_symbol(symbol) == "GOLD":
        names.extend(["XAUUSD", "GOLD"])
    candidates = []
    for name in dict.fromkeys(names):
        candidates.extend(tf_dir.glob(f"**/{name}.csv"))
    if not candidates:
        return []
    path = sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]
    rows = []
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
                        }
                    )
                except (TypeError, ValueError):
                    continue
    except OSError:
        return []
    return rows[-bars:]


def moving_average(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = []
    total = 0.0
    window: list[float] = []
    for value in values:
        window.append(value)
        total += value
        if len(window) > period:
            total -= window.pop(0)
        out.append(total / period if len(window) == period else None)
    return out


@dataclass
class CandleItem:
    x: list[float]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]


class CandlestickItem(pg.GraphicsObject):
    def __init__(self) -> None:
        super().__init__()
        self.data: CandleItem | None = None
        self.picture = None
        self.up_color = COLORS["up"]
        self.down_color = COLORS["down"]

    def set_colors(self, up_color: str, down_color: str) -> None:
        self.up_color = up_color
        self.down_color = down_color
        self.picture = None
        self.update()

    def set_data(self, data: CandleItem) -> None:
        self.data = data
        self.picture = None
        self.prepareGeometryChange()
        self.update()

    def generate_picture(self) -> None:
        picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(picture)
        if not self.data:
            painter.end()
            self.picture = picture
            return
        width = 0.62
        wick_up_pen = pg.mkPen(self.up_color)
        wick_down_pen = pg.mkPen(self.down_color)
        body_pen = pg.mkPen("#f8fafc", width=0.7)
        up_brush = pg.mkBrush(self.up_color)
        down_brush = pg.mkBrush(self.down_color)
        for x, o, h, l, c in zip(self.data.x, self.data.open, self.data.high, self.data.low, self.data.close):
            up = c >= o
            painter.setPen(wick_up_pen if up else wick_down_pen)
            painter.drawLine(QPointF(x, l), QPointF(x, h))
            painter.setPen(body_pen)
            painter.setBrush(up_brush if up else down_brush)
            top = max(o, c)
            bottom = min(o, c)
            height = max(top - bottom, 0.0000001)
            painter.drawRect(pg.QtCore.QRectF(x - width / 2, bottom, width, height))
        painter.end()
        self.picture = picture

    def paint(self, painter: Any, *_args: Any) -> None:
        if self.picture is None:
            self.generate_picture()
        if self.picture:
            painter.drawPicture(0, 0, self.picture)

    def boundingRect(self) -> pg.QtCore.QRectF:
        if not self.data or not self.data.x:
            return pg.QtCore.QRectF()
        return pg.QtCore.QRectF(
            min(self.data.x) - 1,
            min(self.data.low),
            max(self.data.x) - min(self.data.x) + 2,
            max(self.data.high) - min(self.data.low),
        )


class FastChartViewBox(pg.ViewBox):
    """ViewBox com wheel zoom mais direto para sensação de plataforma de trading."""

    def wheelEvent(self, event: Any, axis: Any = None) -> None:
        delta = event.delta() if hasattr(event, "delta") else event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        factor = 0.82 if delta > 0 else 1.22
        mouse_point = self.mapSceneToView(event.scenePos())
        self.scaleBy((factor, 1.0), center=mouse_point)
        event.accept()


class FusionTerminalQt(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        pg.setConfigOptions(antialias=True, background=COLORS["bg"], foreground=COLORS["text"])
        self.setWindowTitle("Fusion Terminal Pro - Desktop")
        self.resize(1580, 920)
        self.events: list[dict[str, Any]] = []
        self.oms: dict[str, Any] = {}
        self.candles: list[dict[str, Any]] = []
        self.selected_symbol = "GOLD"
        self.selected_timeframe = "M15"
        self.show_ema = True
        self.show_markers = True
        self.show_positions = True
        self.docks: dict[str, QDockWidget] = {}
        self.candle_item = CandlestickItem()
        self.plot_items: list[Any] = []
        self.marker_items: list[Any] = []
        self.cross_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(COLORS["border"], style=Qt.DashLine))
        self.cross_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(COLORS["border"], style=Qt.DashLine))
        self._build_ui()
        self._apply_style()
        self.refresh_all()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(2500)

    def _build_ui(self) -> None:
        self._build_toolbar()
        splitter = QSplitter(Qt.Horizontal)
        self.setCentralWidget(splitter)

        left = self._panel()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._title("Watchlist"))
        self.watch_table = QTableWidget(0, 4)
        self.watch_table.setHorizontalHeaderLabels(["Ativo", "Sinal", "Pos", "PnL"])
        self.watch_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.watch_table.verticalHeader().setVisible(False)
        self.watch_table.cellClicked.connect(self._watch_clicked)
        left_layout.addWidget(self.watch_table)
        left_layout.addWidget(self._title("Alertas"))
        self.alert_list = QListWidget()
        left_layout.addWidget(self.alert_list)

        center = self._panel()
        center_layout = QVBoxLayout(center)
        self.chart_header = QLabel("GOLD M15")
        self.chart_header.setObjectName("ChartHeader")
        center_layout.addWidget(self.chart_header)
        self.view_box = FastChartViewBox()
        self.plot = pg.PlotWidget(viewBox=self.view_box)
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setClipToView(True)
        self.plot.setDownsampling(auto=True, mode="peak")
        self.plot.addItem(self.candle_item)
        self.plot.addItem(self.cross_v, ignoreBounds=True)
        self.plot.addItem(self.cross_h, ignoreBounds=True)
        self.plot.scene().sigMouseMoved.connect(self._mouse_moved)
        center_layout.addWidget(self.plot, stretch=1)
        self.tabs = QTabWidget()
        self.events_table = QTableWidget(0, 6)
        self.events_table.setHorizontalHeaderLabels(["Hora", "Tipo", "Ativo", "TF", "Lado", "Motivo"])
        self.events_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.engines_table = QTableWidget(0, 5)
        self.engines_table.setHorizontalHeaderLabels(["Engine", "TF", "Estado", "Score", "Conf"])
        self.engines_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabs.addTab(self.events_table, "Eventos")
        self.tabs.addTab(self.engines_table, "Engines")
        center_layout.addWidget(self.tabs, stretch=0)

        right = self._panel()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._title("Painel do Ativo"))
        self.asset_label = QLabel("GOLD")
        self.asset_label.setObjectName("AssetTitle")
        right_layout.addWidget(self.asset_label)
        self.metrics = QGridLayout()
        right_layout.addLayout(self.metrics)
        self.metric_labels: dict[str, QLabel] = {}
        for idx, key in enumerate(["Ultimo", "Timeframe", "Posicoes", "PnL"]):
            card = self._metric_card(key)
            self.metrics.addWidget(card, idx // 2, idx % 2)
        right_layout.addWidget(self._title("Posições"))
        self.positions_table = QTableWidget(0, 5)
        self.positions_table.setHorizontalHeaderLabels(["Ativo", "Dir", "Entrada", "Atual", "PnL"])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        right_layout.addWidget(self.positions_table)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setSizes([300, 920, 340])

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("Inicializando...")
        status.addWidget(self.status_label)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Ferramentas")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction(self._action("Atualizar", self.refresh_all))
        toolbar.addSeparator()
        self.symbol_combo = QComboBox()
        self.symbol_combo.currentTextChanged.connect(self._symbol_changed)
        toolbar.addWidget(self.symbol_combo)
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(TIMEFRAMES)
        self.tf_combo.setCurrentText(self.selected_timeframe)
        self.tf_combo.currentTextChanged.connect(self._timeframe_changed)
        toolbar.addWidget(self.tf_combo)
        toolbar.addSeparator()
        for tf in TIMEFRAMES:
            toolbar.addAction(self._action(tf, lambda checked=False, value=tf: self._timeframe_changed(value)))
        toolbar.addSeparator()
        self.ema_action = self._toggle_action("EMA", True, self._toggle_ema)
        self.markers_action = self._toggle_action("Sinais", True, self._toggle_markers)
        self.positions_action = self._toggle_action("Posições", True, self._toggle_positions)
        toolbar.addAction(self.ema_action)
        toolbar.addAction(self.markers_action)
        toolbar.addAction(self.positions_action)

    def _action(self, text: str, callback: Any) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(callback)
        return action

    def _toggle_action(self, text: str, checked: bool, callback: Any) -> QAction:
        action = QAction(text, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(callback)
        return action

    def _panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Panel")
        return frame

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("PanelTitle")
        return label

    def _metric_card(self, key: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("MetricCard")
        layout = QVBoxLayout(frame)
        name = QLabel(key)
        name.setObjectName("MetricName")
        value = QLabel("-")
        value.setObjectName("MetricValue")
        layout.addWidget(name)
        layout.addWidget(value)
        self.metric_labels[key] = value
        return frame

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {COLORS['bg']}; color: {COLORS['text']}; font-family: Segoe UI; }}
            QToolBar {{ background: {COLORS['header']}; border-bottom: 1px solid {COLORS['border']}; spacing: 6px; padding: 4px; }}
            QToolButton, QPushButton, QComboBox {{ background: {COLORS['panel2']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 3px; padding: 5px 8px; }}
            QToolButton:hover, QPushButton:hover, QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QToolButton:checked {{ background: #1e3a5f; border-color: {COLORS['primary']}; }}
            #Panel {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; }}
            #PanelTitle {{ color: {COLORS['muted']}; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
            #ChartHeader {{ color: {COLORS['text']}; font-size: 18px; font-weight: 700; padding: 8px; }}
            #AssetTitle {{ color: {COLORS['text']}; font-size: 30px; font-weight: 700; }}
            #MetricCard {{ background: {COLORS['panel2']}; border: 1px solid {COLORS['border']}; border-radius: 5px; }}
            #MetricName {{ color: {COLORS['muted']}; font-size: 12px; }}
            #MetricValue {{ color: {COLORS['text']}; font-size: 22px; font-weight: 700; }}
            QTableWidget, QListWidget {{ background: {COLORS['panel']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; gridline-color: {COLORS['grid']}; }}
            QHeaderView::section {{ background: {COLORS['header']}; color: {COLORS['text']}; border: 0; padding: 5px; }}
            QTabWidget::pane {{ border: 1px solid {COLORS['border']}; }}
            QTabBar::tab {{ background: {COLORS['header']}; color: {COLORS['muted']}; padding: 7px 14px; }}
            QTabBar::tab:selected {{ color: {COLORS['text']}; border-bottom: 2px solid {COLORS['primary']}; }}
            QStatusBar {{ background: {COLORS['header']}; color: {COLORS['muted']}; }}
            """
        )

    def refresh_all(self) -> None:
        events_path = latest_file(ROOT / "logs" / "events", "events_*.jsonl")
        oms_path = latest_file(ROOT / "logs" / "oms", "oms_snapshot_*.json")
        self.events = read_jsonl_tail(events_path)
        self.oms = normalize_oms(read_json(oms_path))
        self.candles = read_ohlc(self.selected_symbol, self.selected_timeframe)
        self._update_symbols()
        self._update_watchlist()
        self._update_chart()
        self._update_events_table()
        self._update_engines_table()
        self._update_positions()
        self._update_asset_panel()
        self.status_label.setText(
            f"Eventos: {events_path.name if events_path else '-'} | OMS: {oms_path.name if oms_path else '-'} | Atualizado {time.strftime('%H:%M:%S')}"
        )

    def _update_symbols(self) -> None:
        symbols = set()
        for event in self.events:
            symbol = event_symbol(event)
            if symbol:
                symbols.add(symbol)
        for position in self.oms.get("positions", []) or []:
            symbols.add(normalize_symbol(position.get("symbol") or position.get("broker_symbol")))
        values = sorted(symbols or {"GOLD"})
        current_values = [self.symbol_combo.itemText(i) for i in range(self.symbol_combo.count())]
        if values != current_values:
            self.symbol_combo.blockSignals(True)
            self.symbol_combo.clear()
            self.symbol_combo.addItems(values)
            self.symbol_combo.setCurrentText(self.selected_symbol if self.selected_symbol in values else values[0])
            self.symbol_combo.blockSignals(False)

    def _update_watchlist(self) -> None:
        model = self._symbol_model()
        self.watch_table.setRowCount(len(model))
        for row, symbol in enumerate(sorted(model)):
            item = model[symbol]
            self._set_table_row(self.watch_table, row, [symbol, item["signal"], str(item["positions"]), f"{item['pnl']:+.2f}"])

    def _symbol_model(self) -> dict[str, dict[str, Any]]:
        model: dict[str, dict[str, Any]] = defaultdict(lambda: {"signal": "-", "positions": 0, "pnl": 0.0})
        for event in self.events:
            symbol = event_symbol(event)
            if not symbol:
                continue
            if event.get("type") == "SIGNAL":
                model[symbol]["signal"] = f"{event_side(event) or '-'} {event_timeframe(event) or ''}".strip()
        for position in self.oms.get("positions", []) or []:
            symbol = normalize_symbol(position.get("symbol") or position.get("broker_symbol"))
            model[symbol]["positions"] += 1
            model[symbol]["pnl"] += safe_float(position.get("profit"))
        return model

    def _update_chart(self) -> None:
        self.chart_header.setText(f"{self.selected_symbol} {self.selected_timeframe}")
        self.plot.clear()
        self.plot.addItem(self.candle_item)
        self.plot.addItem(self.cross_v, ignoreBounds=True)
        self.plot.addItem(self.cross_h, ignoreBounds=True)
        if not self.candles:
            return
        x = list(range(len(self.candles)))
        opens = [row["open"] for row in self.candles]
        highs = [row["high"] for row in self.candles]
        lows = [row["low"] for row in self.candles]
        closes = [row["close"] for row in self.candles]
        self.candle_item.set_data(CandleItem(x=x, open=opens, high=highs, low=lows, close=closes))
        self.plot_items.clear()
        if self.show_ema:
            self._plot_ma(x, closes, 9, COLORS["primary"])
            self._plot_ma(x, closes, 21, COLORS["warn"])
            self._plot_ma(x, closes, 50, COLORS["ema50"])
        if self.show_positions:
            self._plot_positions()
        if self.show_markers:
            self._plot_markers()
        self.plot.setXRange(max(0, len(x) - 140), len(x) + 5, padding=0)
        self.plot.setYRange(min(lows), max(highs), padding=0.08)

    def _plot_ma(self, x: list[int], closes: list[float], period: int, color: str) -> None:
        ma = moving_average(closes, period)
        points = [(idx, value) for idx, value in zip(x, ma) if value is not None]
        if len(points) < 2:
            return
        item = self.plot.plot([p[0] for p in points], [p[1] for p in points], pen=pg.mkPen(color, width=1.5), name=f"EMA{period}")
        self.plot_items.append(item)

    def _plot_positions(self) -> None:
        for position in self.oms.get("positions", []) or []:
            if normalize_symbol(position.get("symbol") or position.get("broker_symbol")) != self.selected_symbol:
                continue
            price = safe_float(position.get("price_open"), math.nan)
            if not math.isfinite(price):
                continue
            direction = str(position.get("direction", "")).upper()
            color = COLORS["up"] if direction == "BUY" else COLORS["down"]
            line = pg.InfiniteLine(pos=price, angle=0, pen=pg.mkPen(color, width=2, style=Qt.DashLine), label=f"{direction} {price:.5f} PnL {safe_float(position.get('profit')):+.2f}")
            self.plot.addItem(line)

    def _plot_markers(self) -> None:
        for event in self.events[-300:]:
            if event.get("type") not in {"SIGNAL", "DECISION", "ORDER_RESULT"}:
                continue
            if event_symbol(event) != self.selected_symbol:
                continue
            tf = event_timeframe(event)
            if tf and tf != self.selected_timeframe:
                continue
            idx = self._event_index(event)
            if idx is None or idx >= len(self.candles):
                continue
            row = self.candles[idx]
            side = event_side(event)
            block = event.get("type") == "DECISION" and "BLOCK" in event_reason(event).upper()
            y = row["low"] if side == "BUY" else row["high"]
            symbol = "t1" if side == "BUY" else "t"
            color = COLORS["warn"] if block else COLORS["up"] if side == "BUY" else COLORS["down"]
            marker = pg.ScatterPlotItem([idx], [y], symbol=symbol, size=15, brush=pg.mkBrush(color), pen=pg.mkPen(color))
            marker.setToolTip(f"{event.get('type')} {side} {event_score(event):.3f}\n{event_reason(event)}")
            self.plot.addItem(marker)

    def _event_index(self, event: dict[str, Any]) -> int | None:
        marker = event_marker_time(event)[:10]
        for idx, row in enumerate(self.candles):
            if str(row.get("time", ""))[:10] == marker:
                return idx
        return len(self.candles) - 1 if self.candles else None

    def _update_events_table(self) -> None:
        rows = [
            event
            for event in self.events[-220:]
            if event.get("type") in {"SIGNAL", "DECISION", "ORDER_REQUEST", "ORDER_RESULT", "POSITION_UPDATE", "RISK_ALERT"}
        ][-80:]
        self.events_table.setRowCount(len(rows))
        for row_idx, event in enumerate(reversed(rows)):
            self._set_table_row(
                self.events_table,
                row_idx,
                [
                    str(event.get("timestamp", ""))[-8:],
                    str(event.get("type", "")),
                    event_symbol(event),
                    event_timeframe(event),
                    event_side(event),
                    event_reason(event)[:120],
                ],
            )

    def _update_engines_table(self) -> None:
        rows = []
        seen = set()
        for event in reversed(self.events):
            if event.get("type") != "ENGINE_RESULT":
                continue
            data = raw_data(event)
            candidate = data.get("candidate") or {}
            symbol = normalize_symbol(data.get("symbol") or candidate.get("symbol"))
            if symbol != self.selected_symbol:
                continue
            engine = data.get("engine") or {}
            name = str(engine.get("engine") or "-")
            tf = str(data.get("timeframe") or candidate.get("timeframe") or "-").upper()
            key = (name, tf)
            if key in seen:
                continue
            seen.add(key)
            rows.append([name, tf, str(engine.get("state") or "-"), f"{safe_float(engine.get('score')):.3f}", f"{safe_float(engine.get('confidence')):.3f}"])
            if len(rows) >= 50:
                break
        self.engines_table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self._set_table_row(self.engines_table, row_idx, row)

    def _update_positions(self) -> None:
        rows = self.oms.get("positions", []) or []
        self.positions_table.setRowCount(len(rows))
        for row_idx, position in enumerate(rows):
            self._set_table_row(
                self.positions_table,
                row_idx,
                [
                    normalize_symbol(position.get("symbol") or position.get("broker_symbol")),
                    str(position.get("direction", "-")),
                    str(position.get("price_open", "-")),
                    str(position.get("price_current", "-")),
                    f"{safe_float(position.get('profit')):+.2f}",
                ],
            )

    def _update_asset_panel(self) -> None:
        positions = [
            position
            for position in self.oms.get("positions", []) or []
            if normalize_symbol(position.get("symbol") or position.get("broker_symbol")) == self.selected_symbol
        ]
        last = self.candles[-1] if self.candles else {}
        pnl = sum(safe_float(position.get("profit")) for position in positions)
        self.asset_label.setText(self.selected_symbol)
        self.metric_labels["Ultimo"].setText(f"{safe_float(last.get('close'), math.nan):.5f}" if last else "-")
        self.metric_labels["Timeframe"].setText(self.selected_timeframe)
        self.metric_labels["Posicoes"].setText(str(len(positions)))
        self.metric_labels["PnL"].setText(f"{pnl:+.2f}")

    def _watch_clicked(self, row: int, _column: int) -> None:
        item = self.watch_table.item(row, 0)
        if item:
            self._symbol_changed(item.text())

    def _symbol_changed(self, symbol: str) -> None:
        if not symbol:
            return
        self.selected_symbol = normalize_symbol(symbol)
        self.symbol_combo.blockSignals(True)
        self.symbol_combo.setCurrentText(self.selected_symbol)
        self.symbol_combo.blockSignals(False)
        self.candles = read_ohlc(self.selected_symbol, self.selected_timeframe)
        self._update_chart()
        self._update_engines_table()
        self._update_asset_panel()

    def _timeframe_changed(self, timeframe: str) -> None:
        if timeframe not in TIMEFRAMES:
            return
        self.selected_timeframe = timeframe
        self.tf_combo.blockSignals(True)
        self.tf_combo.setCurrentText(timeframe)
        self.tf_combo.blockSignals(False)
        self.candles = read_ohlc(self.selected_symbol, self.selected_timeframe)
        self._update_chart()
        self._update_asset_panel()

    def _toggle_ema(self, checked: bool) -> None:
        self.show_ema = checked
        self._update_chart()

    def _toggle_markers(self, checked: bool) -> None:
        self.show_markers = checked
        self._update_chart()

    def _toggle_positions(self, checked: bool) -> None:
        self.show_positions = checked
        self._update_chart()

    def _mouse_moved(self, pos: QPointF) -> None:
        if not self.plot.sceneBoundingRect().contains(pos):
            return
        point = self.plot.plotItem.vb.mapSceneToView(pos)
        self.cross_v.setPos(point.x())
        self.cross_h.setPos(point.y())
        idx = round(point.x())
        if 0 <= idx < len(self.candles):
            candle = self.candles[idx]
            self.chart_header.setText(
                f"{self.selected_symbol} {self.selected_timeframe} | O {candle['open']:.5f} H {candle['high']:.5f} L {candle['low']:.5f} C {candle['close']:.5f}"
            )

    @staticmethod
    def _set_table_row(table: QTableWidget, row: int, values: list[Any]) -> None:
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if isinstance(value, str) and value.startswith("-"):
                item.setForeground(QColor(COLORS["down"]))
            elif isinstance(value, str) and value.startswith("+"):
                item.setForeground(QColor(COLORS["up"]))
            table.setItem(row, col, item)


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    window = FusionTerminalQt()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
