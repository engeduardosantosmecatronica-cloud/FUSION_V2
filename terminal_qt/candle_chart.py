from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDockWidget,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QCheckBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStatusBar,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from fusion_terminal_qt import (
    COLORS,
    ROOT,
    TIMEFRAMES,
    CandleItem,
    CandlestickItem,
    FastChartViewBox,
    moving_average,
    normalize_symbol,
)
from chart_axes import PriceAxis, TimeAxis
from runtime_utils import (
    is_color,
    latest_file,
    read_jsonl_tail,
    safe_float,
)
from simulation_engine import (
    max_drawdown_pips,
    pip_value,
    signal_key,
    simulated_order,
    simulate_trade_results,
    strategy_names,
)
from probability_events import probability_model, side_from_probs
from market_data import MarketDataService
from institutional_layers import compact_json, layer_names, layer_snapshot
from terminal_state import account_metrics, latest_oms_snapshot, positions, recent_alerts, symbol_watchlist
from period_backtest_engine import (
    PeriodBacktestState,
    candle_sequence,
    create_order as bt_create_order,
    metrics as bt_metrics,
    signal_for_strategy,
    strategy_options as bt_strategy_options,
    update_orders as bt_update_orders,
)

class CandleChartWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        pg.setConfigOptions(antialias=False, background=COLORS["bg"], foreground=COLORS["text"])
        self.setWindowTitle("Fusion Chart - Candles")
        self.resize(1480, 860)

        self.symbol = "GOLD"
        self.timeframe = "M15"
        self.max_bars = 5000
        self.candles: list[dict[str, Any]] = []
        self.indicator_mode = "EMA 9/21/50"
        self.auto_follow = True
        self.preserve_view_on_next_draw = False
        self.show_simulation_levels = False
        self._last_source_key: tuple[Any, ...] | None = None
        self._last_mouse_update = 0.0
        self.data_source = "Inicializando"
        self.mt5_ready = False
        self.last_broker_symbol = "-"
        self.last_mt5_error = ""
        self.first_candle_time = "-"
        self.last_candle_time = "-"
        self.broker_symbols: dict[str, str] = {}
        self.market_data = MarketDataService()
        self.events: list[dict[str, Any]] = []
        self.oms_snapshot: dict[str, Any] = {}
        self._last_alert_key = ""
        self.theme = {
            "background": COLORS["bg"],
            "bull_candle": COLORS["up"],
            "bear_candle": COLORS["down"],
            "buy_arrow": COLORS["up"],
            "sell_arrow": COLORS["down"],
            "entry_line": COLORS["primary"],
            "sl_line": COLORS["down"],
            "tp_line": COLORS["up"],
            "trailing_line": COLORS["warn"],
        }

        self.candle_item = CandlestickItem()
        self._apply_candle_theme()
        self.cross_v = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen(COLORS["border"], style=Qt.DashLine))
        self.cross_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen(COLORS["border"], style=Qt.DashLine))
        self.ma_items: list[Any] = []
        self.simulation_items: list[Any] = []
        self.simulated_orders: list[dict[str, Any]] = []
        self.simulated_trades: list[dict[str, Any]] = []
        self.selected_order_key: str | None = None
        self.order_overrides: dict[str, dict[str, float]] = {}
        self.trailing_runtime: dict[str, dict[str, float]] = {}
        self.trailing_play_order_key: str | None = None
        self.trailing_play_index = 0
        self.trailing_play_phase = 0
        self.trailing_play_target: float | None = None
        self.trailing_highlight_item: Any = None
        self.trailing_result: dict[str, Any] | None = None
        self.bt_state = PeriodBacktestState()
        self.bt_items: list[Any] = []
        self.bt_fast_ma: list[float | None] = []
        self.bt_slow_ma: list[float | None] = []
        self.bt_trend_ma: list[float | None] = []
        self._bt_last_visual_update = 0.0
        self._bt_visual_update_pending = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.trailing_play_timer = QTimer(self)
        self.trailing_play_timer.timeout.connect(self._advance_trailing_playback)
        self.period_backtest_timer = QTimer(self)
        self.period_backtest_timer.timeout.connect(self._advance_period_backtest)

        self._build_ui()
        self._apply_style()
        self.refresh()

        self.timer.start(5000)

    def _build_ui(self) -> None:
        self._build_menu()
        self._build_toolbar()

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QLabel()
        self.header.setObjectName("ChartHeader")
        layout.addWidget(self.header)

        self.axis = TimeAxis("bottom")
        self.price_axis = PriceAxis("right")
        self.view_box = FastChartViewBox()
        self.plot = pg.PlotWidget(axisItems={"bottom": self.axis, "right": self.price_axis}, viewBox=self.view_box)
        self.plot.showAxis("right")
        self.plot.hideAxis("left")
        self.plot.showGrid(x=True, y=True, alpha=0.25)
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setMenuEnabled(False)
        self.plot.setClipToView(True)
        self.plot.setDownsampling(auto=True, mode="peak")
        self.plot.addItem(self.candle_item)
        self.plot.addItem(self.cross_v, ignoreBounds=True)
        self.plot.addItem(self.cross_h, ignoreBounds=True)
        self.plot.scene().sigMouseMoved.connect(self._mouse_moved)
        self.plot.scene().sigMouseClicked.connect(self._mouse_clicked)
        layout.addWidget(self.plot, stretch=1)
        self.setCentralWidget(root)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel()
        status.addWidget(self.status_label)
        self._build_probability_dock()
        self._build_watchlist_dock()
        self._build_alerts_dock()
        self._build_positions_dock()
        self._build_simulation_dock()
        self._build_simulation_result_dock()
        self._build_period_backtest_dock()
        self._build_layers_dock()
        self._build_properties_dock()
        self._build_analysis_dock()

    def _build_probability_dock(self) -> None:
        panel = QWidget()
        panel.setMinimumWidth(150)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Probabilidades")
        title.setObjectName("SidePanelTitle")
        layout.addWidget(title)

        self.probability_table = QTableWidget(0, 5)
        self.probability_table.setHorizontalHeaderLabels(["TF", "BUY", "SELL", "Lado", "Fonte"])
        self.probability_table.setMinimumWidth(0)
        self.probability_table.horizontalHeader().setMinimumSectionSize(34)
        self.probability_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.probability_table.setColumnWidth(0, 42)
        self.probability_table.setColumnWidth(1, 58)
        self.probability_table.setColumnWidth(2, 58)
        self.probability_table.setColumnWidth(3, 58)
        self.probability_table.setColumnWidth(4, 70)
        self.probability_table.verticalHeader().setVisible(False)
        self.probability_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.probability_table)

        self.probability_dock = QDockWidget("Probabilidades", self)
        self.probability_dock.setObjectName("ProbabilityDock")
        self.probability_dock.setMinimumWidth(160)
        self.probability_dock.setMaximumWidth(900)
        self.probability_dock.setWidget(panel)
        self.probability_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.probability_dock.setFeatures(
            QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        self.probability_dock.visibilityChanged.connect(self._sync_probability_action)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.probability_dock)
        self.resizeDocks([self.probability_dock], [310], Qt.Horizontal)
        self.probability_dock.hide()

    def _build_watchlist_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        title = QLabel("Watchlist")
        title.setObjectName("SidePanelTitle")
        layout.addWidget(title)

        self.watchlist_table = QTableWidget(0, 7)
        self.watchlist_table.setHorizontalHeaderLabels(["Ativo", "Sinais", "Alertas", "Pos", "PnL", "Lado", "TF"])
        self.watchlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.watchlist_table.verticalHeader().setVisible(False)
        self.watchlist_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.watchlist_table.setSelectionBehavior(QTableWidget.SelectRows)
        widths = [74, 54, 58, 44, 68, 58, 44]
        for col, width in enumerate(widths):
            self.watchlist_table.setColumnWidth(col, width)
        self.watchlist_table.itemSelectionChanged.connect(self._watchlist_selection_changed)
        layout.addWidget(self.watchlist_table)

        self.watchlist_dock = QDockWidget("Watchlist", self)
        self.watchlist_dock.setObjectName("WatchlistDock")
        self.watchlist_dock.setMinimumWidth(250)
        self.watchlist_dock.setWidget(panel)
        self.watchlist_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.watchlist_dock.visibilityChanged.connect(self._sync_watchlist_action)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.watchlist_dock)
        self.watchlist_dock.hide()

    def _build_alerts_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        title = QLabel("Alertas e Eventos")
        title.setObjectName("SidePanelTitle")
        layout.addWidget(title)

        self.alerts_table = QTableWidget(0, 7)
        self.alerts_table.setHorizontalHeaderLabels(["Hora", "Tipo", "Ativo", "TF", "Lado", "Status", "Motivo"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.alerts_table.verticalHeader().setVisible(False)
        self.alerts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectRows)
        for col, width in enumerate([150, 110, 74, 46, 60, 80, 240]):
            self.alerts_table.setColumnWidth(col, width)
        layout.addWidget(self.alerts_table)

        self.alerts_dock = QDockWidget("Alertas", self)
        self.alerts_dock.setObjectName("AlertsDock")
        self.alerts_dock.setMinimumWidth(520)
        self.alerts_dock.setWidget(panel)
        self.alerts_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.alerts_dock.visibilityChanged.connect(self._sync_alerts_action)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.alerts_dock)
        self.alerts_dock.hide()

    def _build_positions_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.account_summary = QLabel("Conta: -")
        self.account_summary.setObjectName("SimulationStatus")
        self.account_summary.setWordWrap(True)
        layout.addWidget(self.account_summary)

        self.positions_table = QTableWidget(0, 7)
        self.positions_table.setHorizontalHeaderLabels(["Ativo", "Lado", "Lote", "Entrada", "Atual", "PnL", "TF"])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.positions_table.verticalHeader().setVisible(False)
        self.positions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.positions_table.setSelectionBehavior(QTableWidget.SelectRows)
        for col, width in enumerate([78, 58, 54, 82, 82, 70, 50]):
            self.positions_table.setColumnWidth(col, width)
        layout.addWidget(self.positions_table)

        self.positions_dock = QDockWidget("Posicoes / OMS", self)
        self.positions_dock.setObjectName("PositionsDock")
        self.positions_dock.setMinimumWidth(430)
        self.positions_dock.setWidget(panel)
        self.positions_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.positions_dock.visibilityChanged.connect(self._sync_positions_action)
        self.addDockWidget(Qt.RightDockWidgetArea, self.positions_dock)
        self.positions_dock.hide()

    def _build_menu(self) -> None:
        bar = self.menuBar()
        bar.setNativeMenuBar(False)
        tools_menu = bar.addMenu("Ferramentas")
        self.probability_action = QAction("Probabilidades", self)
        self.probability_action.setCheckable(True)
        self.probability_action.triggered.connect(self._toggle_probability_panel)
        tools_menu.addAction(self.probability_action)

        self.watchlist_action = QAction("Watchlist", self)
        self.watchlist_action.setCheckable(True)
        self.watchlist_action.triggered.connect(self._toggle_watchlist_panel)
        tools_menu.addAction(self.watchlist_action)

        self.alerts_action = QAction("Alertas / Eventos", self)
        self.alerts_action.setCheckable(True)
        self.alerts_action.triggered.connect(self._toggle_alerts_panel)
        tools_menu.addAction(self.alerts_action)

        self.positions_action = QAction("Posicoes / OMS", self)
        self.positions_action.setCheckable(True)
        self.positions_action.triggered.connect(self._toggle_positions_panel)
        tools_menu.addAction(self.positions_action)

        self.simulation_action = QAction("Simulacao", self)
        self.simulation_action.setCheckable(True)
        self.simulation_action.triggered.connect(self._toggle_simulation_panel)
        tools_menu.addAction(self.simulation_action)
        self.analysis_action = QAction("Analise da Estrategia", self)
        self.analysis_action.setCheckable(True)
        self.analysis_action.triggered.connect(self._toggle_analysis_panel)
        tools_menu.addAction(self.analysis_action)

        self.period_backtest_action = QAction("Backtest Visual por Periodo", self)
        self.period_backtest_action.setCheckable(True)
        self.period_backtest_action.triggered.connect(self._toggle_period_backtest_panel)
        tools_menu.addAction(self.period_backtest_action)

        layers_menu = bar.addMenu("Camadas")
        self.layers_action = QAction("Painel Institucional", self)
        self.layers_action.setCheckable(True)
        self.layers_action.triggered.connect(self._toggle_layers_panel)
        layers_menu.addAction(self.layers_action)
        layers_menu.addSeparator()
        self.layer_actions: dict[str, QAction] = {}
        for name in layer_names():
            action = QAction(name, self)
            action.triggered.connect(lambda _checked=False, layer=name: self._show_layer(layer))
            self.layer_actions[name] = action
            layers_menu.addAction(action)

        properties_menu = bar.addMenu("Propriedades")
        self.properties_action = QAction("Cores", self)
        self.properties_action.setCheckable(True)
        self.properties_action.triggered.connect(self._toggle_properties_panel)
        properties_menu.addAction(self.properties_action)

    def _build_simulation_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QLabel("Simulacao Visual")
        header.setObjectName("SidePanelTitle")
        layout.addWidget(header)

        setup_group = QGroupBox("Setup")
        setup_form = QFormLayout(setup_group)
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(self._strategy_names())
        self.strategy_combo.currentTextChanged.connect(self._simulation_changed)
        setup_form.addRow("Estrategia", self.strategy_combo)
        layout.addWidget(setup_group)

        risk_group = QGroupBox("Risco")
        risk_form = QFormLayout(risk_group)
        self.stop_loss_spin = self._pip_spinbox(0.0, 10000.0, 50.0)
        self.take_profit_spin = self._pip_spinbox(0.0, 10000.0, 100.0)
        self.use_stop_loss_checkbox = QCheckBox("Usar stop loss")
        self.use_stop_loss_checkbox.setChecked(True)
        self.use_take_profit_checkbox = QCheckBox("Usar take profit")
        self.use_take_profit_checkbox.setChecked(True)
        self.use_stop_loss_checkbox.toggled.connect(self._simulation_changed)
        self.use_take_profit_checkbox.toggled.connect(self._simulation_changed)
        self.stop_loss_spin.valueChanged.connect(self._simulation_changed)
        self.take_profit_spin.valueChanged.connect(self._simulation_changed)
        risk_form.addRow("", self.use_stop_loss_checkbox)
        risk_form.addRow("Stop loss", self.stop_loss_spin)
        risk_form.addRow("", self.use_take_profit_checkbox)
        risk_form.addRow("Take profit", self.take_profit_spin)
        layout.addWidget(risk_group)

        trailing_group = QGroupBox("Trailing")
        trailing_form = QFormLayout(trailing_group)
        self.trailing_activation_spin = self._pip_spinbox(0.0, 10000.0, 80.0)
        self.trailing_distance_spin = self._pip_spinbox(0.0, 10000.0, 40.0)
        self.trailing_activation_spin.valueChanged.connect(self._simulation_changed)
        self.trailing_distance_spin.valueChanged.connect(self._simulation_changed)
        trailing_form.addRow("Ativacao", self.trailing_activation_spin)
        trailing_form.addRow("Distancia", self.trailing_distance_spin)
        layout.addWidget(trailing_group)

        self.reset_trailing_button = QPushButton("Resetar simulacao do trailing")
        self.reset_trailing_button.clicked.connect(self._reset_selected_trailing_simulation)
        layout.addWidget(self.reset_trailing_button)

        playback_group = QGroupBox("Replay do trailing")
        playback_layout = QVBoxLayout(playback_group)
        self.start_trailing_button = QPushButton("Iniciar")
        self.pause_trailing_button = QPushButton("Pausar")
        self.stop_trailing_button = QPushButton("Parar")
        self.start_trailing_button.clicked.connect(self._start_trailing_playback)
        self.pause_trailing_button.clicked.connect(self._pause_trailing_playback)
        self.stop_trailing_button.clicked.connect(self._stop_trailing_playback)
        playback_layout.addWidget(self.start_trailing_button)
        playback_layout.addWidget(self.pause_trailing_button)
        playback_layout.addWidget(self.stop_trailing_button)
        self.trailing_step_spin = self._pip_spinbox(1.0, 500.0, 10.0)
        playback_layout.addWidget(QLabel("Passo do preco simulado (pips)"))
        playback_layout.addWidget(self.trailing_step_spin)
        self.trailing_speed_label = QLabel()
        self.trailing_speed_slider = QSlider(Qt.Horizontal)
        self.trailing_speed_slider.setRange(1, 20)
        self.trailing_speed_slider.setValue(8)
        self.trailing_speed_slider.valueChanged.connect(self._sync_playback_speed_label)
        playback_layout.addWidget(QLabel("Velocidade da simulacao"))
        playback_layout.addWidget(self.trailing_speed_slider)
        playback_layout.addWidget(self.trailing_speed_label)
        self._sync_playback_speed_label()
        layout.addWidget(playback_group)

        self.show_levels_checkbox = QCheckBox("Mostrar entrada / SL / TP / trailing")
        self.show_levels_checkbox.setChecked(self.show_simulation_levels)
        self.show_levels_checkbox.toggled.connect(self._toggle_simulation_levels)
        layout.addWidget(self.show_levels_checkbox)

        self.apply_simulation_button = QPushButton("Aplicar parametros")
        self.apply_simulation_button.clicked.connect(self._update_simulation_status)
        layout.addWidget(self.apply_simulation_button)

        self.simulation_status = QLabel()
        self.simulation_status.setObjectName("SimulationStatus")
        self.simulation_status.setWordWrap(True)
        layout.addWidget(self.simulation_status)
        layout.addStretch(1)

        self.simulation_dock = QDockWidget("Simulacao", self)
        self.simulation_dock.setObjectName("SimulationDock")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(panel)
        self.simulation_dock.setWidget(scroll)
        self.simulation_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.simulation_dock.visibilityChanged.connect(self._sync_simulation_action)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.simulation_dock)
        self.simulation_dock.hide()
        self._update_simulation_status()

    def _build_simulation_result_dock(self) -> None:
        panel = QWidget()
        panel.setMinimumWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("Resultado da Simulacao")
        title.setObjectName("SidePanelTitle")
        layout.addWidget(title)

        self.simulation_result_summary = QLabel()
        self.simulation_result_summary.setObjectName("SimulationStatus")
        self.simulation_result_summary.setWordWrap(True)
        layout.addWidget(self.simulation_result_summary)

        lot_group = QGroupBox("Lote")
        lot_form = QFormLayout(lot_group)
        self.result_lot_spin = QDoubleSpinBox()
        self.result_lot_spin.setDecimals(2)
        self.result_lot_spin.setRange(0.01, 100.0)
        self.result_lot_spin.setSingleStep(0.01)
        self.result_lot_spin.setValue(0.01)
        self.result_lot_spin.valueChanged.connect(self._update_simulation_result_panel)
        lot_form.addRow("Lote", self.result_lot_spin)
        layout.addWidget(lot_group)

        self.simulation_result_table = QTableWidget(0, 2)
        self.simulation_result_table.setHorizontalHeaderLabels(["Campo", "Valor"])
        self.simulation_result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.simulation_result_table.verticalHeader().setVisible(False)
        self.simulation_result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.simulation_result_table)
        layout.addStretch(1)

        self.simulation_result_dock = QDockWidget("Resultado", self)
        self.simulation_result_dock.setObjectName("SimulationResultDock")
        self.simulation_result_dock.setMinimumWidth(240)
        self.simulation_result_dock.setWidget(panel)
        self.simulation_result_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.simulation_result_dock)
        self.simulation_result_dock.hide()
        self._update_simulation_result_panel()

    def _build_period_backtest_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel("Backtest Visual por Periodo")
        title.setObjectName("SidePanelTitle")
        layout.addWidget(title)

        setup_group = QGroupBox("Periodo e estrategia")
        setup_form = QFormLayout(setup_group)
        self.bt_strategy_combo = QComboBox()
        self.bt_strategy_combo.addItems(bt_strategy_options())
        self.bt_start_spin = QSpinBox()
        self.bt_start_spin.setRange(0, 0)
        self.bt_end_spin = QSpinBox()
        self.bt_end_spin.setRange(0, 0)
        self.bt_max_orders_spin = QSpinBox()
        self.bt_max_orders_spin.setRange(1, 20)
        self.bt_max_orders_spin.setValue(1)
        self.bt_max_orders_spin.setToolTip("Limite de ordens abertas ao mesmo tempo. Nao limita o total de trades do teste.")
        setup_form.addRow("Estrategia", self.bt_strategy_combo)
        setup_form.addRow("Candle inicial", self.bt_start_spin)
        setup_form.addRow("Candle final", self.bt_end_spin)
        setup_form.addRow("Max simultaneas", self.bt_max_orders_spin)
        layout.addWidget(setup_group)

        risk_group = QGroupBox("Risco")
        risk_form = QFormLayout(risk_group)
        self.bt_lot_spin = QDoubleSpinBox()
        self.bt_lot_spin.setDecimals(2)
        self.bt_lot_spin.setRange(0.01, 100.0)
        self.bt_lot_spin.setSingleStep(0.01)
        self.bt_lot_spin.setValue(0.01)
        self.bt_use_sl_checkbox = QCheckBox("Usar stop loss")
        self.bt_use_sl_checkbox.setChecked(True)
        self.bt_use_tp_checkbox = QCheckBox("Usar take profit")
        self.bt_use_tp_checkbox.setChecked(True)
        self.bt_stop_loss_spin = self._pip_spinbox(0.0, 10000.0, 50.0)
        self.bt_take_profit_spin = self._pip_spinbox(0.0, 10000.0, 100.0)
        risk_form.addRow("Lote", self.bt_lot_spin)
        risk_form.addRow("", self.bt_use_sl_checkbox)
        risk_form.addRow("Stop loss", self.bt_stop_loss_spin)
        risk_form.addRow("", self.bt_use_tp_checkbox)
        risk_form.addRow("Take profit", self.bt_take_profit_spin)
        layout.addWidget(risk_group)

        trailing_group = QGroupBox("Trailing")
        trailing_form = QFormLayout(trailing_group)
        self.bt_trailing_activation_spin = self._pip_spinbox(0.0, 10000.0, 80.0)
        self.bt_trailing_distance_spin = self._pip_spinbox(0.0, 10000.0, 40.0)
        trailing_form.addRow("Ativacao", self.bt_trailing_activation_spin)
        trailing_form.addRow("Distancia", self.bt_trailing_distance_spin)
        layout.addWidget(trailing_group)

        playback_group = QGroupBox("Replay")
        playback_layout = QVBoxLayout(playback_group)
        self.bt_start_button = QPushButton("Iniciar")
        self.bt_pause_button = QPushButton("Pausar")
        self.bt_stop_button = QPushButton("Parar")
        self.bt_clear_button = QPushButton("Limpar")
        self.bt_start_button.clicked.connect(self._start_period_backtest)
        self.bt_pause_button.clicked.connect(self._pause_period_backtest)
        self.bt_stop_button.clicked.connect(self._stop_period_backtest)
        self.bt_clear_button.clicked.connect(self._clear_period_backtest)
        playback_layout.addWidget(self.bt_start_button)
        playback_layout.addWidget(self.bt_pause_button)
        playback_layout.addWidget(self.bt_stop_button)
        playback_layout.addWidget(self.bt_clear_button)
        self.bt_step_spin = self._pip_spinbox(1.0, 500.0, 10.0)
        playback_layout.addWidget(QLabel("Passo do preco (pips)"))
        playback_layout.addWidget(self.bt_step_spin)
        self.bt_speed_label = QLabel()
        self.bt_speed_slider = QSlider(Qt.Horizontal)
        self.bt_speed_slider.setRange(1, 30)
        self.bt_speed_slider.setValue(10)
        self.bt_speed_slider.valueChanged.connect(self._sync_period_backtest_speed_label)
        playback_layout.addWidget(QLabel("Velocidade"))
        playback_layout.addWidget(self.bt_speed_slider)
        playback_layout.addWidget(self.bt_speed_label)
        self._sync_period_backtest_speed_label()
        layout.addWidget(playback_group)

        self.bt_status = QLabel()
        self.bt_status.setObjectName("SimulationStatus")
        self.bt_status.setWordWrap(True)
        layout.addWidget(self.bt_status)

        self.bt_summary_table = QTableWidget(0, 2)
        self.bt_summary_table.setHorizontalHeaderLabels(["Metrica", "Valor"])
        self.bt_summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bt_summary_table.verticalHeader().setVisible(False)
        self.bt_summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.bt_summary_table)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(panel)
        self.period_backtest_dock = QDockWidget("Backtest Visual", self)
        self.period_backtest_dock.setObjectName("PeriodBacktestDock")
        self.period_backtest_dock.setMinimumWidth(300)
        self.period_backtest_dock.setWidget(scroll)
        self.period_backtest_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.period_backtest_dock.visibilityChanged.connect(self._sync_period_backtest_action)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.period_backtest_dock)
        self.period_backtest_dock.hide()
        self._update_period_backtest_panel()

    def _build_layers_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel("Camadas Institucionais")
        title.setObjectName("SidePanelTitle")
        layout.addWidget(title)

        self.layers_tabs = QTabWidget()
        self.layer_tables: dict[str, QTableWidget] = {}
        self.layer_details: dict[str, QTextEdit] = {}
        for name in layer_names():
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(4, 4, 4, 4)
            tab_layout.setSpacing(6)

            table = QTableWidget(0, 8)
            table.setHorizontalHeaderLabels(["Engine", "TF", "Direcao", "Estado", "Score", "Conf", "+/-/!", "Lado"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setColumnWidth(0, 150)
            table.setColumnWidth(1, 46)
            table.setColumnWidth(2, 70)
            table.setColumnWidth(3, 115)
            table.setColumnWidth(4, 62)
            table.setColumnWidth(5, 62)
            table.setColumnWidth(6, 62)
            table.setColumnWidth(7, 70)

            detail = QTextEdit()
            detail.setReadOnly(True)
            detail.setMinimumHeight(180)
            detail.setObjectName("LayerDetail")

            table.itemSelectionChanged.connect(lambda layer=name: self._update_layer_detail(layer))
            tab_layout.addWidget(table, stretch=2)
            tab_layout.addWidget(detail, stretch=1)
            self.layers_tabs.addTab(tab, name)
            self.layer_tables[name] = table
            self.layer_details[name] = detail

        layout.addWidget(self.layers_tabs)

        self.layers_dock = QDockWidget("Camadas", self)
        self.layers_dock.setObjectName("LayersDock")
        self.layers_dock.setMinimumWidth(520)
        self.layers_dock.setWidget(panel)
        self.layers_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.layers_dock.visibilityChanged.connect(self._sync_layers_action)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layers_dock)
        self.layers_dock.hide()

    def _build_properties_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        header = QLabel("Propriedades")
        header.setObjectName("SidePanelTitle")
        layout.addWidget(header)

        colors_group = QGroupBox("Cores")
        colors_form = QFormLayout(colors_group)
        self.color_inputs: dict[str, QLineEdit] = {}
        labels = {
            "background": "Fundo",
            "bull_candle": "Candle alta",
            "bear_candle": "Candle baixa",
            "buy_arrow": "Seta BUY",
            "sell_arrow": "Seta SELL",
            "entry_line": "Linha entrada",
            "sl_line": "Linha SL",
            "tp_line": "Linha TP",
            "trailing_line": "Linha trailing",
        }
        for key, label in labels.items():
            field = QLineEdit(self.theme[key])
            field.setMaxLength(16)
            self.color_inputs[key] = field
            colors_form.addRow(label, field)
        layout.addWidget(colors_group)

        apply_button = QPushButton("Aplicar cores")
        apply_button.clicked.connect(self._apply_theme_from_panel)
        layout.addWidget(apply_button)
        layout.addStretch(1)

        self.properties_dock = QDockWidget("Propriedades", self)
        self.properties_dock.setObjectName("PropertiesDock")
        self.properties_dock.setWidget(panel)
        self.properties_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.properties_dock.visibilityChanged.connect(self._sync_properties_action)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.properties_dock)
        self.properties_dock.hide()

    def _build_analysis_dock(self) -> None:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.analysis_summary = QTableWidget(0, 2)
        self.analysis_summary.setHorizontalHeaderLabels(["Metrica", "Valor"])
        self.analysis_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.analysis_summary.verticalHeader().setVisible(False)
        self.analysis_summary.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.analysis_summary, stretch=1)

        self.analysis_dock = QDockWidget("Analise da Estrategia", self)
        self.analysis_dock.setObjectName("AnalysisDock")
        self.analysis_dock.setWidget(panel)
        self.analysis_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable)
        self.analysis_dock.visibilityChanged.connect(self._sync_analysis_action)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.analysis_dock)
        self.analysis_dock.hide()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Chart")
        toolbar.setMovable(False)
        toolbar.setObjectName("ChartToolbar")
        self.addToolBar(toolbar)

        toolbar.addWidget(QLabel("Ativo "))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setMinimumWidth(130)
        self.broker_symbols = self._build_symbol_map()
        self.symbol_combo.addItems(sorted(self.broker_symbols))
        self.symbol_combo.setCurrentText(self.symbol)
        self.symbol_combo.currentTextChanged.connect(self._symbol_changed)
        toolbar.addWidget(self.symbol_combo)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Timeframe "))
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(TIMEFRAMES)
        self.tf_combo.setCurrentText(self.timeframe)
        self.tf_combo.currentTextChanged.connect(self._timeframe_changed)
        toolbar.addWidget(self.tf_combo)

        toolbar.addSeparator()
        toolbar.addWidget(QLabel("Indicador "))
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems(["Nenhum", "EMA 9", "EMA 21", "EMA 50", "EMA 9/21", "EMA 9/21/50"])
        self.indicator_combo.setCurrentText(self.indicator_mode)
        self.indicator_combo.currentTextChanged.connect(self._indicator_changed)
        toolbar.addWidget(self.indicator_combo)

        toolbar.addSeparator()
        self.follow_action = self._toggle_action("Auto", True, self._toggle_follow)
        toolbar.addAction(self.follow_action)
        toolbar.addAction(self._action("Atualizar", self.refresh))

    def _apply_style(self) -> None:
        self.setStyleSheet(
            f"""
            QMainWindow, QWidget {{ background: {COLORS['bg']}; color: {COLORS['text']}; font-family: Segoe UI; }}
            QToolBar {{ background: {COLORS['header']}; border-bottom: 1px solid {COLORS['border']}; spacing: 6px; padding: 5px; }}
            QToolButton, QComboBox {{ background: {COLORS['panel2']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 3px; padding: 5px 8px; }}
            QToolButton:hover, QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QToolButton:checked {{ background: #12314f; border-color: {COLORS['primary']}; }}
            #ChartHeader {{ background: {COLORS['panel']}; color: {COLORS['text']}; font-size: 15px; font-weight: 700; padding: 8px 12px; border-bottom: 1px solid {COLORS['border']}; }}
            QMenuBar {{ background: {COLORS['header']}; color: {COLORS['text']}; border-bottom: 1px solid {COLORS['border']}; }}
            QMenuBar::item {{ padding: 5px 10px; }}
            QMenuBar::item:selected, QMenu {{ background: {COLORS['panel2']}; color: {COLORS['text']}; }}
            QMenu::item:selected {{ background: #12314f; }}
            QDockWidget {{ titlebar-close-icon: none; titlebar-normal-icon: none; color: {COLORS['text']}; }}
            QDockWidget::title {{ background: {COLORS['header']}; padding: 7px; border: 1px solid {COLORS['border']}; }}
            QGroupBox {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']}; border-radius: 4px; margin-top: 14px; padding: 8px; font-weight: 700; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {COLORS['muted']}; }}
            QCheckBox {{ color: {COLORS['text']}; spacing: 8px; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; }}
            QDoubleSpinBox, QSpinBox, QPushButton {{ background: {COLORS['panel2']}; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 3px; padding: 5px 8px; }}
            QPushButton:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: {COLORS['primary']}; }}
            #SidePanelTitle {{ color: {COLORS['text']}; font-size: 18px; font-weight: 800; }}
            #SimulationStatus {{ color: {COLORS['muted']}; padding: 8px; border: 1px solid {COLORS['border']}; background: {COLORS['panel']}; }}
            QStatusBar {{ background: {COLORS['header']}; color: {COLORS['muted']}; }}
            """
        )

    def refresh(self) -> None:
        self.events = read_jsonl_tail(latest_file(ROOT / "logs" / "events", "events_*.jsonl"))
        self.oms_snapshot = latest_oms_snapshot(ROOT)
        candles, source_key, data_source = self._read_market_data()
        if source_key == self._last_source_key:
            self._update_probability_panel()
            self._update_layers_panel()
            self._update_terminal_state_panels()
            self.status_label.setText(self._status_text("aguardando novo candle"))
            return
        self._last_source_key = source_key
        self.data_source = data_source
        self.candles = candles
        self.first_candle_time = str(candles[0].get("time", "-")) if candles else "-"
        self.last_candle_time = str(candles[-1].get("time", "-")) if candles else "-"
        self._sync_period_backtest_ranges()
        self._draw_chart()
        self._update_probability_panel()
        self._update_layers_panel()
        self._update_terminal_state_panels()
        self.status_label.setText(self._status_text())

    def _draw_chart(self) -> None:
        view_range = self.plot.viewRange() if hasattr(self, "plot") else None
        self.header.setText(f"{self.symbol} | {self.timeframe}")
        self.plot.setBackground(self.theme["background"])
        for item in self.ma_items:
            self.plot.removeItem(item)
        self.ma_items.clear()
        self._clear_simulation_items()
        self._clear_period_backtest_items()
        self._clear_trailing_highlight()

        if not self.candles:
            self.header.setText(f"{self.symbol} | {self.timeframe} | sem candles")
            return

        x = list(range(len(self.candles)))
        opens = [row["open"] for row in self.candles]
        highs = [row["high"] for row in self.candles]
        lows = [row["low"] for row in self.candles]
        closes = [row["close"] for row in self.candles]
        labels = [str(row.get("time", "")) for row in self.candles]

        self.axis.set_labels(labels)
        self.candle_item.set_data(CandleItem(x=x, open=opens, high=highs, low=lows, close=closes))
        self._plot_selected_indicators(x, closes)
        self._run_visual_simulation(x, highs, lows, closes)
        self._plot_trailing_highlight()
        self._draw_period_backtest_items()

        if self.preserve_view_on_next_draw and view_range:
            self.plot.setXRange(view_range[0][0], view_range[0][1], padding=0)
            self.plot.setYRange(view_range[1][0], view_range[1][1], padding=0)
            self.preserve_view_on_next_draw = False
        elif self.auto_follow:
            visible = min(160, len(x))
            self.plot.setXRange(max(0, len(x) - visible), len(x) + 5, padding=0)
            self.plot.setYRange(min(lows[-visible:]), max(highs[-visible:]), padding=0.08)

    def _plot_ma(self, x: list[int], closes: list[float], period: int, color: str) -> None:
        ma = moving_average(closes, period)
        points = [(idx, value) for idx, value in zip(x, ma) if value is not None]
        if len(points) < 2:
            return
        item = self.plot.plot([p[0] for p in points], [p[1] for p in points], pen=pg.mkPen(color, width=1.2))
        self.ma_items.append(item)

    def _mouse_moved(self, pos: QPointF) -> None:
        now = time.perf_counter()
        if now - self._last_mouse_update < 0.035:
            return
        self._last_mouse_update = now
        if not self.plot.sceneBoundingRect().contains(pos):
            return
        point = self.plot.plotItem.vb.mapSceneToView(pos)
        self.cross_v.setPos(point.x())
        self.cross_h.setPos(point.y())
        idx = round(point.x())
        if 0 <= idx < len(self.candles):
            candle = self.candles[idx]
            self.header.setText(
                f"{self.symbol} | {self.timeframe} | {candle.get('time', '')} | "
                f"O {candle['open']:.5f} H {candle['high']:.5f} L {candle['low']:.5f} C {candle['close']:.5f}"
            )

    def _mouse_clicked(self, event: Any) -> None:
        if not self._period_backtest_click_enabled(event):
            return
        point = self.plot.plotItem.vb.mapSceneToView(event.scenePos())
        idx = round(point.x())
        if 0 <= idx < len(self.candles):
            self._jump_period_backtest_to_candle(idx)
            event.accept()

    def _period_backtest_click_enabled(self, event: Any) -> bool:
        if not hasattr(self, "period_backtest_dock") or not self.period_backtest_dock.isVisible():
            return False
        if not self.candles:
            return False
        if hasattr(event, "isAccepted") and event.isAccepted():
            return False
        if hasattr(event, "button") and event.button() != Qt.LeftButton:
            return False
        if not self.plot.sceneBoundingRect().contains(event.scenePos()):
            return False
        return True

    def _update_probability_panel(self) -> None:
        if not hasattr(self, "probability_table"):
            return
        model = self._probability_model()
        self.probability_table.setRowCount(len(TIMEFRAMES))
        for row, timeframe in enumerate(TIMEFRAMES):
            item = model.get(timeframe, {})
            p_buy = item.get("p_buy")
            p_sell = item.get("p_sell")
            side = item.get("side") or self._side_from_probs(p_buy, p_sell)
            values = [
                timeframe,
                f"{p_buy:.3f}" if isinstance(p_buy, float) else "-",
                f"{p_sell:.3f}" if isinstance(p_sell, float) else "-",
                side or "-",
                item.get("source") or "-",
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if col == 3 and value == "BUY":
                    table_item.setForeground(pg.mkColor(self.theme["buy_arrow"]))
                elif col == 3 and value == "SELL":
                    table_item.setForeground(pg.mkColor(self.theme["sell_arrow"]))
                self.probability_table.setItem(row, col, table_item)

    def _probability_model(self) -> dict[str, dict[str, Any]]:
        return probability_model(self.events, self.symbol, self.last_broker_symbol)

    @staticmethod
    def _side_from_probs(p_buy: Any, p_sell: Any) -> str:
        return side_from_probs(p_buy, p_sell)

    def _update_terminal_state_panels(self) -> None:
        self._update_watchlist_panel()
        self._update_alerts_panel()
        self._update_positions_panel()

    def _update_watchlist_panel(self) -> None:
        if not hasattr(self, "watchlist_table"):
            return
        rows = symbol_watchlist(self.events, self.oms_snapshot)
        self.watchlist_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [
                item.get("symbol", "-"),
                item.get("signals", 0),
                item.get("alerts", 0),
                item.get("positions", 0),
                f"{safe_float(item.get('pnl')):+.2f}",
                item.get("last_side", "-"),
                item.get("last_tf", "-"),
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if col == 4:
                    table_item.setForeground(pg.mkColor(self.theme["buy_arrow"] if safe_float(item.get("pnl")) >= 0 else self.theme["sell_arrow"]))
                if col == 5 and str(value).upper() == "BUY":
                    table_item.setForeground(pg.mkColor(self.theme["buy_arrow"]))
                elif col == 5 and str(value).upper() == "SELL":
                    table_item.setForeground(pg.mkColor(self.theme["sell_arrow"]))
                self.watchlist_table.setItem(row, col, table_item)

    def _update_alerts_panel(self) -> None:
        if not hasattr(self, "alerts_table"):
            return
        rows = recent_alerts(self.events)
        self.alerts_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [
                str(item.get("time", "-"))[:19],
                item.get("type", "-"),
                item.get("symbol", "-"),
                item.get("tf", "-"),
                item.get("side", "-"),
                item.get("status", "-"),
                item.get("reason", "-"),
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if col == 4 and str(value).upper() == "BUY":
                    table_item.setForeground(pg.mkColor(self.theme["buy_arrow"]))
                elif col == 4 and str(value).upper() == "SELL":
                    table_item.setForeground(pg.mkColor(self.theme["sell_arrow"]))
                self.alerts_table.setItem(row, col, table_item)

    def _update_positions_panel(self) -> None:
        if not hasattr(self, "positions_table"):
            return
        metrics = account_metrics(self.oms_snapshot)
        self.account_summary.setText(
            f"Balance {metrics['balance']:.2f} {metrics['currency']} | "
            f"Equity {metrics['equity']:.2f} | Margem {metrics['margin']:.2f} | "
            f"PnL aberto {metrics['pnl']:+.2f} | Posicoes {metrics['positions']} | Trades {metrics['trades']}"
        )
        rows = positions(self.oms_snapshot)
        self.positions_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [
                normalize_symbol(item.get("symbol") or item.get("broker_symbol")),
                item.get("direction") or item.get("side") or "-",
                item.get("volume") or item.get("lot") or "-",
                item.get("price_open") or item.get("price") or "-",
                item.get("price_current") or item.get("current_price") or "-",
                f"{safe_float(item.get('profit')):+.2f}",
                item.get("timeframe") or item.get("strategy_timeframe") or "-",
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if col == 5:
                    table_item.setForeground(pg.mkColor(self.theme["buy_arrow"] if safe_float(item.get("profit")) >= 0 else self.theme["sell_arrow"]))
                self.positions_table.setItem(row, col, table_item)

    def _watchlist_selection_changed(self) -> None:
        selected = self.watchlist_table.selectedItems() if hasattr(self, "watchlist_table") else []
        if not selected:
            return
        symbol_item = self.watchlist_table.item(selected[0].row(), 0)
        if symbol_item:
            self.symbol_combo.setCurrentText(symbol_item.text())

    def _update_layers_panel(self) -> None:
        if not hasattr(self, "layer_tables"):
            return
        for name in layer_names():
            snapshot = layer_snapshot(self.events, name, self.symbol, self.last_broker_symbol)
            rows = snapshot.get("engines", [])
            table = self.layer_tables[name]
            table.setRowCount(len(rows))
            for row, item in enumerate(rows):
                values = [
                    item.get("engine", "-"),
                    item.get("timeframe", "-"),
                    item.get("direction", "-"),
                    item.get("state", "-"),
                    f"{safe_float(item.get('score')):.3f}",
                    f"{safe_float(item.get('confidence')):.3f}",
                    f"{item.get('positive_count', 0)}/{item.get('negative_count', 0)}/{item.get('warning_count', 0)}",
                    item.get("side", "-"),
                ]
                for col, value in enumerate(values):
                    table_item = QTableWidgetItem(str(value))
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    if col == 2 and value == "BUY":
                        table_item.setForeground(pg.mkColor(self.theme["buy_arrow"]))
                    elif col == 2 and value == "SELL":
                        table_item.setForeground(pg.mkColor(self.theme["sell_arrow"]))
                    table.setItem(row, col, table_item)
                table.item(row, 0).setData(Qt.UserRole, item)
            if not rows:
                table.setRowCount(1)
                for col, value in enumerate(["-", "-", "-", "sem evento", "-", "-", "-", "-"]):
                    table_item = QTableWidgetItem(value)
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    table.setItem(0, col, table_item)
            self._update_layer_detail(name, snapshot)

    def _update_layer_detail(self, layer_name: str, snapshot: dict[str, Any] | None = None) -> None:
        if not hasattr(self, "layer_details"):
            return
        detail = self.layer_details[layer_name]
        table = self.layer_tables[layer_name]
        selected = table.selectedItems()
        if selected:
            row = selected[0].row()
            item = table.item(row, 0).data(Qt.UserRole) if table.item(row, 0) else None
            if item:
                detail.setPlainText(compact_json(item))
                return
        if snapshot is None:
            snapshot = layer_snapshot(self.events, layer_name, self.symbol, self.last_broker_symbol)
        detail.setPlainText(compact_json(snapshot))

    def _show_layer(self, layer_name: str) -> None:
        if not hasattr(self, "layers_dock"):
            return
        self.layers_dock.setVisible(True)
        self.layers_dock.raise_()
        self._sync_layers_action(True)
        index = layer_names().index(layer_name) if layer_name in layer_names() else 0
        self.layers_tabs.setCurrentIndex(index)
        self._update_layers_panel()

    def _available_symbols(self) -> list[str]:
        return self.market_data.available_symbols()

    def _build_symbol_map(self) -> dict[str, str]:
        self.broker_symbols = self.market_data.build_symbol_map()
        self._sync_market_state()
        return self.broker_symbols

    def _broker_symbol_for(self, symbol: str, mt5_symbols: set[str] | None = None) -> str:
        return self.market_data.broker_symbol_for(symbol, mt5_symbols)

    def _mt5_visible_symbols(self) -> list[str]:
        symbols = self.market_data.mt5_visible_symbols()
        self._sync_market_state()
        return symbols

    def _symbol_changed(self, symbol: str) -> None:
        if not symbol:
            return
        self.symbol = normalize_symbol(symbol)
        self._last_source_key = None
        self._update_probability_panel()
        self.refresh()

    def _timeframe_changed(self, timeframe: str) -> None:
        if timeframe not in TIMEFRAMES:
            return
        self.timeframe = timeframe
        self.tf_combo.blockSignals(True)
        self.tf_combo.setCurrentText(timeframe)
        self.tf_combo.blockSignals(False)
        self._last_source_key = None
        self.refresh()

    def _indicator_changed(self, value: str) -> None:
        self.indicator_mode = value
        self._redraw_indicator_layer()

    def _plot_selected_indicators(self, x: list[int], closes: list[float]) -> None:
        if self.indicator_mode == "Nenhum":
            return
        if "9" in self.indicator_mode:
            self._plot_ma(x, closes, 9, COLORS["primary"])
        if "21" in self.indicator_mode:
            self._plot_ma(x, closes, 21, COLORS["warn"])
        if "50" in self.indicator_mode:
            self._plot_ma(x, closes, 50, COLORS["ema50"])

    def _clear_simulation_items(self) -> None:
        if not hasattr(self, "plot"):
            return
        for item in self.simulation_items:
            try:
                self.plot.removeItem(item)
            except Exception:
                pass
        self.simulation_items.clear()
        self.simulated_orders.clear()
        self.simulated_trades.clear()

    def _simulation_changed(self, *_args: Any) -> None:
        self._store_selected_order_override()
        self._update_simulation_status()
        self._redraw_simulation_layer()

    def _chart_arrays(self) -> tuple[list[int], list[float], list[float], list[float]]:
        x = list(range(len(self.candles)))
        highs = [row["high"] for row in self.candles]
        lows = [row["low"] for row in self.candles]
        closes = [row["close"] for row in self.candles]
        return x, highs, lows, closes

    def _redraw_indicator_layer(self) -> None:
        if not self.candles or not hasattr(self, "plot"):
            return
        view_range = self.plot.viewRange()
        self.plot.setUpdatesEnabled(False)
        try:
            for item in self.ma_items:
                try:
                    self.plot.removeItem(item)
                except Exception:
                    pass
            self.ma_items.clear()
            x, _highs, _lows, closes = self._chart_arrays()
            self._plot_selected_indicators(x, closes)
        finally:
            self.plot.setUpdatesEnabled(True)
            self.plot.setXRange(view_range[0][0], view_range[0][1], padding=0)
            self.plot.setYRange(view_range[1][0], view_range[1][1], padding=0)

    def _redraw_simulation_layer(self) -> None:
        if not self.candles or not hasattr(self, "plot"):
            return
        view_range = self.plot.viewRange()
        self.plot.setUpdatesEnabled(False)
        try:
            self._clear_simulation_items()
            self._clear_trailing_highlight()
            x, highs, lows, closes = self._chart_arrays()
            self._run_visual_simulation(x, highs, lows, closes)
            self._plot_trailing_highlight()
        finally:
            self.plot.setUpdatesEnabled(True)
            self.plot.setXRange(view_range[0][0], view_range[0][1], padding=0)
            self.plot.setYRange(view_range[1][0], view_range[1][1], padding=0)

    def _run_visual_simulation(self, x: list[int], highs: list[float], lows: list[float], closes: list[float]) -> None:
        if not hasattr(self, "strategy_combo"):
            return
        strategy = self.strategy_combo.currentText().lower()
        if "cruzamento" not in strategy and "ema cross" not in strategy:
            self._update_simulation_status()
            return

        ema_fast = moving_average(closes, 9)
        ema_slow = moving_average(closes, 21)
        signals: list[dict[str, Any]] = []
        for idx in range(1, len(closes)):
            prev_fast = ema_fast[idx - 1]
            prev_slow = ema_slow[idx - 1]
            curr_fast = ema_fast[idx]
            curr_slow = ema_slow[idx]
            if prev_fast is None or prev_slow is None or curr_fast is None or curr_slow is None:
                continue
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                signals.append({"index": idx, "side": "BUY", "price": closes[idx]})
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                signals.append({"index": idx, "side": "SELL", "price": closes[idx]})

        self._plot_simulation_signals(signals, highs, lows)
        self._simulate_trade_results(signals, highs, lows, closes)
        self._update_analysis_panel()
        self._update_simulation_status()

    def _plot_simulation_signals(self, signals: list[dict[str, Any]], highs: list[float], lows: list[float]) -> None:
        if not signals:
            return
        visible_signals = signals[-250:]
        buy_points: list[dict[str, Any]] = []
        sell_points: list[dict[str, Any]] = []

        for signal in visible_signals:
            idx = int(signal["index"])
            side = str(signal["side"])
            price = float(signal["price"])
            order = self._simulated_order(signal)
            self.simulated_orders.append(order)
            selected = order["key"] == self.selected_order_key
            if side == "BUY":
                buy_points.append(
                    {
                        "pos": (idx, lows[idx]),
                        "data": order["key"],
                        "symbol": "t1",
                        "size": 17 if selected else 11,
                        "brush": pg.mkBrush("#00ffbf" if selected else self.theme["buy_arrow"]),
                        "pen": pg.mkPen("#ffffff" if selected else self.theme["buy_arrow"], width=2.2 if selected else 1.4),
                    }
                )
            else:
                sell_points.append(
                    {
                        "pos": (idx, highs[idx]),
                        "data": order["key"],
                        "symbol": "t",
                        "size": 17 if selected else 11,
                        "brush": pg.mkBrush("#ff1744" if selected else self.theme["sell_arrow"]),
                        "pen": pg.mkPen("#ffffff" if selected else self.theme["sell_arrow"], width=2.2 if selected else 1.4),
                    }
                )

        if buy_points:
            item = pg.ScatterPlotItem()
            item.addPoints(buy_points)
            item.setToolTip("BUY simulado")
            item.sigClicked.connect(self._simulation_arrow_clicked)
            self.plot.addItem(item)
            self.simulation_items.append(item)
        if sell_points:
            item = pg.ScatterPlotItem()
            item.addPoints(sell_points)
            item.setToolTip("SELL simulado")
            item.sigClicked.connect(self._simulation_arrow_clicked)
            self.plot.addItem(item)
            self.simulation_items.append(item)
        if self.selected_order_key:
            self._plot_selected_trade_exit()
        if self.show_simulation_levels:
            orders = [order for order in self.simulated_orders if order["key"] == self.selected_order_key]
            self._plot_simulation_levels(orders)

    def _simulated_order(self, signal: dict[str, Any]) -> dict[str, Any]:
        return simulated_order(
            self.symbol,
            self.timeframe,
            signal,
            self.order_overrides,
            self.stop_loss_spin.value() if self.use_stop_loss_checkbox.isChecked() else 0.0,
            self.take_profit_spin.value() if self.use_take_profit_checkbox.isChecked() else 0.0,
            self.trailing_activation_spin.value(),
            self.trailing_distance_spin.value(),
        )

    def _signal_key(self, signal: dict[str, Any]) -> str:
        return signal_key(self.symbol, self.timeframe, signal)

    def _simulate_trade_results(
        self,
        signals: list[dict[str, Any]],
        highs: list[float],
        lows: list[float],
        closes: list[float],
    ) -> None:
        self.simulated_trades = simulate_trade_results(
            self.symbol,
            self.timeframe,
            signals,
            highs,
            lows,
            closes,
            self.candles,
            self.stop_loss_spin.value() if self.use_stop_loss_checkbox.isChecked() else 0.0,
            self.take_profit_spin.value() if self.use_take_profit_checkbox.isChecked() else 0.0,
        )

    def _plot_selected_trade_exit(self) -> None:
        if not self.selected_order_key:
            return
        trade = next((item for item in self.simulated_trades if item.get("key") == self.selected_order_key), None)
        if not trade:
            return
        exit_index = int(trade["exit_index"])
        exit_price = float(trade["exit"])
        pnl_pips = safe_float(trade.get("pnl_pips"))
        color = "#00ffbf" if pnl_pips >= 0 else "#ff1744"
        marker = pg.ScatterPlotItem(
            [exit_index],
            [exit_price],
            symbol="o",
            size=13,
            brush=pg.mkBrush(color),
            pen=pg.mkPen("#ffffff", width=2),
        )
        marker.setToolTip(f"Saida simulada | {pnl_pips:+.1f} pips | {trade.get('reason', '')}")
        self.plot.addItem(marker)
        self.simulation_items.append(marker)
        text = pg.TextItem(f"Saida {pnl_pips:+.1f} pips", color=color, anchor=(0, 1.2))
        text.setPos(exit_index + 1, exit_price)
        self.plot.addItem(text)
        self.simulation_items.append(text)

    def _update_analysis_panel(self) -> None:
        if not hasattr(self, "analysis_summary"):
            return
        trades = self.simulated_trades
        total = len(trades)
        wins = [trade for trade in trades if safe_float(trade.get("pnl")) > 0]
        losses = [trade for trade in trades if safe_float(trade.get("pnl")) < 0]
        gross_profit = sum(safe_float(trade.get("pnl_pips")) for trade in wins)
        gross_loss = sum(safe_float(trade.get("pnl_pips")) for trade in losses)
        net = gross_profit + gross_loss
        win_rate = (len(wins) / total * 100.0) if total else 0.0
        drawdown = self._max_drawdown_pips(trades)
        profit_factor = abs(gross_profit / gross_loss) if gross_loss else 0.0

        summary = [
            ("Trades", total),
            ("Vencedores", len(wins)),
            ("Perdedores", len(losses)),
            ("Win rate", f"{win_rate:.1f}%"),
            ("Lucro bruto", f"{gross_profit:+.1f} pips"),
            ("Prejuizo bruto", f"{gross_loss:+.1f} pips"),
            ("Resultado liquido", f"{net:+.1f} pips"),
            ("Drawdown max", f"{drawdown:.1f} pips"),
            ("Profit factor", f"{profit_factor:.2f}" if gross_loss else "-"),
        ]
        self.analysis_summary.setRowCount(len(summary))
        for row, (name, value) in enumerate(summary):
            self._set_table_item(self.analysis_summary, row, 0, name)
            self._set_table_item(self.analysis_summary, row, 1, value)

    def _max_drawdown_pips(self, trades: list[dict[str, Any]]) -> float:
        return max_drawdown_pips(trades)

    def _sync_period_backtest_ranges(self) -> None:
        if not hasattr(self, "bt_start_spin"):
            return
        max_index = max(0, len(self.candles) - 1)
        previous_start = self.bt_start_spin.value()
        previous_end = self.bt_end_spin.value()
        for spin in (self.bt_start_spin, self.bt_end_spin):
            spin.blockSignals(True)
            spin.setRange(0, max_index)
        self.bt_start_spin.setValue(min(previous_start, max_index))
        self.bt_end_spin.setValue(max(min(previous_end or max_index, max_index), self.bt_start_spin.value()))
        for spin in (self.bt_start_spin, self.bt_end_spin):
            spin.blockSignals(False)

    def _prepare_period_backtest_indicators(self) -> None:
        closes = [safe_float(row.get("close")) for row in self.candles]
        self.bt_fast_ma = moving_average(closes, 9)
        self.bt_slow_ma = moving_average(closes, 21)
        self.bt_trend_ma = moving_average(closes, 50)

    def _start_period_backtest(self) -> None:
        if not self.candles:
            return
        start = min(self.bt_start_spin.value(), len(self.candles) - 1)
        end = max(self.bt_end_spin.value(), start)
        self._prepare_period_backtest_indicators()
        if self.bt_state.finished or self.bt_state.index < start or self.bt_state.index > end:
            first_price = safe_float(self.candles[start].get("open"))
            self.bt_state = PeriodBacktestState(index=start, phase=0, price=first_price)
        self.period_backtest_timer.start(self._period_backtest_interval_ms())
        self._follow_period_backtest_candle()
        self._update_period_backtest_panel()
        self._draw_period_backtest_items()

    def _jump_period_backtest_to_candle(self, index: int) -> None:
        if not self.candles or not hasattr(self, "bt_start_spin"):
            return
        idx = min(max(index, 0), len(self.candles) - 1)
        was_running = self.period_backtest_timer.isActive()
        self.period_backtest_timer.stop()
        self._prepare_period_backtest_indicators()
        self._ensure_period_backtest_range_contains(idx)
        first_price = safe_float(self.candles[idx].get("open"))
        self.bt_state = PeriodBacktestState(index=idx, phase=0, price=first_price)
        self._draw_period_backtest_items()
        self._follow_period_backtest_candle()
        self._update_period_backtest_panel()
        self.statusBar().showMessage(f"Backtest reposicionado para candle {idx}", 2500)
        if was_running:
            self.period_backtest_timer.start(self._period_backtest_interval_ms())

    def _ensure_period_backtest_range_contains(self, index: int) -> None:
        start = self.bt_start_spin.value()
        end = self.bt_end_spin.value()
        if index < start:
            self.bt_start_spin.setValue(index)
        if index > end:
            self.bt_end_spin.setValue(index)

    def _pause_period_backtest(self) -> None:
        self.period_backtest_timer.stop()
        self._update_period_backtest_panel()

    def _stop_period_backtest(self) -> None:
        self.period_backtest_timer.stop()
        self.bt_state.finished = True
        self._update_period_backtest_panel()
        self._schedule_period_backtest_visual_update(force=True)

    def _clear_period_backtest(self) -> None:
        self.period_backtest_timer.stop()
        self.bt_state = PeriodBacktestState()
        self.bt_fast_ma = []
        self.bt_slow_ma = []
        self.bt_trend_ma = []
        self._clear_period_backtest_items()
        self._update_period_backtest_panel()

    def _advance_period_backtest(self) -> None:
        if not self.candles:
            self._pause_period_backtest()
            return
        end = min(self.bt_end_spin.value(), len(self.candles) - 1)
        if self.bt_state.index > end:
            self.bt_state.finished = True
            self._pause_period_backtest()
            return

        candle = self.candles[self.bt_state.index]
        sequence = self._period_candle_sequence(candle)
        phase = min(self.bt_state.phase, len(sequence) - 1)
        target = sequence[phase]
        current = self.bt_state.price or sequence[0]
        step = max(self.bt_step_spin.value() * self._pip_value(), self._pip_value())
        if abs(target - current) > step:
            direction = 1.0 if target > current else -1.0
            self.bt_state.price = current + direction * step
        else:
            self.bt_state.price = target
            self.bt_state.phase += 1

        bt_update_orders(self.bt_state, self.bt_state.price, self.bt_state.index)
        if self.bt_state.phase >= len(sequence):
            self._period_backtest_open_signal_if_needed()
            self.bt_state.phase = 0
            self.bt_state.index += 1
            if self.bt_state.index > end:
                self.bt_state.finished = True
                self.period_backtest_timer.stop()

        self._schedule_period_backtest_visual_update()

    def _period_candle_sequence(self, candle: dict[str, Any]) -> list[float]:
        if self.bt_state.open_orders:
            side = self.bt_state.open_orders[0].side
            open_price = safe_float(candle.get("open"))
            high_price = safe_float(candle.get("high"))
            low_price = safe_float(candle.get("low"))
            close_price = safe_float(candle.get("close"))
            if side == "SELL":
                return [open_price, high_price, low_price, close_price]
            return [open_price, low_price, high_price, close_price]
        return candle_sequence(candle)

    def _period_backtest_open_signal_if_needed(self) -> None:
        max_simultaneous = self.bt_max_orders_spin.value()
        open_count = len(self.bt_state.open_orders)
        if open_count >= max_simultaneous:
            self.statusBar().showMessage(
                f"Backtest: limite simultaneo atingido ({open_count}/{max_simultaneous}). "
                "Novas ordens voltam a abrir quando alguma fechar.",
                2500,
            )
            return
        if not self.bt_fast_ma or not self.bt_slow_ma or not self.bt_trend_ma:
            self._prepare_period_backtest_indicators()
        side = signal_for_strategy(
            self.bt_strategy_combo.currentText(),
            self.bt_state.index,
            self.candles,
            self.bt_fast_ma,
            self.bt_slow_ma,
            self.bt_trend_ma,
        )
        if not side:
            return
        price = safe_float(self.candles[self.bt_state.index].get("close"))
        stop_loss = self.bt_stop_loss_spin.value() if self.bt_use_sl_checkbox.isChecked() else 0.0
        take_profit = self.bt_take_profit_spin.value() if self.bt_use_tp_checkbox.isChecked() else 0.0
        bt_create_order(
            self.bt_state,
            self.symbol,
            self.timeframe,
            side,
            self.bt_state.index,
            price,
            self._pip_value(),
            self.bt_lot_spin.value(),
            stop_loss,
            take_profit,
            self.bt_trailing_activation_spin.value(),
            self.bt_trailing_distance_spin.value(),
        )

    def _draw_period_backtest_items(self) -> None:
        if not hasattr(self, "plot"):
            return
        self.plot.setUpdatesEnabled(False)
        try:
            self._clear_period_backtest_items()
            if not self.candles or (not self.bt_state.signals and not self.bt_state.open_orders and not self.bt_state.closed_trades and self.bt_state.price <= 0):
                return

            current_index = min(max(self.bt_state.index, 0), max(0, len(self.candles) - 1))
            if self.bt_state.price > 0:
                price_line = pg.InfiniteLine(
                    pos=self.bt_state.price,
                    angle=0,
                    movable=False,
                    pen=pg.mkPen("#ffffff", width=1.0, style=Qt.DotLine),
                )
                price_line.setZValue(25)
                self.plot.addItem(price_line)
                self.bt_items.append(price_line)
                label_text, label_color = self._period_backtest_floating_result_label()
                label = pg.TextItem(label_text, color=label_color, anchor=(0, 1))
                label.setPos(current_index + 1, self.bt_state.price)
                self.plot.addItem(label)
                self.bt_items.append(label)

            if 0 <= current_index < len(self.candles):
                low = safe_float(self.candles[current_index].get("low"))
                high = safe_float(self.candles[current_index].get("high"))
                region = pg.LinearRegionItem(
                    values=[max(0, current_index - 0.45), current_index + 0.45],
                    orientation="vertical",
                    brush=pg.mkBrush(255, 255, 255, 18),
                    pen=pg.mkPen("#ffffff", width=0.8, style=Qt.DotLine),
                )
                region.setZValue(-3)
                self.plot.addItem(region)
                self.bt_items.append(region)
                marker = pg.TextItem("candle em replay", color="#cbd5e1", anchor=(0, 1))
                marker.setPos(current_index + 0.55, high if high > low else self.bt_state.price)
                self.plot.addItem(marker)
                self.bt_items.append(marker)

            self._draw_period_backtest_signals()
            self._draw_period_backtest_open_orders()
            self._draw_period_backtest_exits()
        finally:
            self.plot.setUpdatesEnabled(True)

    def _period_backtest_floating_result_label(self) -> tuple[str, str]:
        if not self.bt_state.open_orders:
            return f"BT preco {self.bt_state.price:.5f}", "#ffffff"
        net_pips = 0.0
        for order in self.bt_state.open_orders:
            if not order.pip_value:
                continue
            if order.side == "BUY":
                net_pips += (self.bt_state.price - order.entry) / order.pip_value
            else:
                net_pips += (order.entry - self.bt_state.price) / order.pip_value
        color = "#22c55e" if net_pips >= 0 else "#ef4444"
        return f"Flutuante {net_pips:+.1f} pips", color

    def _draw_period_backtest_signals(self) -> None:
        signals = self.bt_state.signals[-250:]
        if not signals:
            return
        points: list[dict[str, Any]] = []
        for signal in signals:
            idx = int(signal.get("index", 0))
            if not 0 <= idx < len(self.candles):
                continue
            side = str(signal.get("side", ""))
            price = safe_float(signal.get("price"))
            points.append(
                {
                    "pos": (idx, price),
                    "symbol": "t1" if side == "BUY" else "t",
                    "size": 10,
                    "brush": pg.mkBrush("#00ffbf" if side == "BUY" else "#ff4d6d"),
                    "pen": pg.mkPen("#ffffff", width=1.0),
                }
            )
        if points:
            item = pg.ScatterPlotItem()
            item.addPoints(points)
            item.setToolTip("Sinais do backtest por periodo")
            item.setZValue(20)
            self.plot.addItem(item)
            self.bt_items.append(item)

    def _draw_period_backtest_open_orders(self) -> None:
        for order in self.bt_state.open_orders:
            start = order.entry_index
            end = min(max(start + 80, self.bt_state.index + 3), len(self.candles) - 1)
            self._add_bt_level(start, end, order.entry, "#38bdf8", f"BT #{order.order_id} {order.side} entrada", Qt.SolidLine)
            if order.stop_loss is not None:
                self._add_bt_level(start, end, order.stop_loss, self.theme["sl_line"], f"BT #{order.order_id} SL", Qt.DashLine)
            if order.take_profit is not None:
                self._add_bt_level(start, end, order.take_profit, self.theme["tp_line"], f"BT #{order.order_id} TP", Qt.DashLine)
            activation_level = self._bt_trailing_activation_level(order)
            preview_stop = self._bt_trailing_preview_stop(order)
            if activation_level is not None:
                self._add_bt_level(
                    start,
                    end,
                    activation_level,
                    self.theme["trailing_line"],
                    f"BT #{order.order_id} trailing ativa em {order.trailing_activation_pips:.1f} pips",
                    Qt.DotLine,
                )
            if preview_stop is not None and order.trailing_stop is None:
                self._add_bt_level(
                    start,
                    end,
                    preview_stop,
                    "#8b5cf6",
                    f"BT #{order.order_id} trailing distancia {order.trailing_distance_pips:.1f} pips",
                    Qt.DotLine,
                )
            if order.trailing_stop is not None:
                state = "ativo" if order.trailing_active else "aguardando"
                self._add_bt_level(
                    start,
                    end,
                    order.trailing_stop,
                    self.theme["trailing_line"],
                    f"BT #{order.order_id} trailing stop {state}",
                    Qt.SolidLine,
                )

    def _bt_trailing_activation_level(self, order: Any) -> float | None:
        activation = safe_float(getattr(order, "trailing_activation_pips", 0.0)) * safe_float(getattr(order, "pip_value", 0.0))
        distance = safe_float(getattr(order, "trailing_distance_pips", 0.0)) * safe_float(getattr(order, "pip_value", 0.0))
        if activation <= 0 or distance <= 0:
            return None
        if order.side == "BUY":
            return order.entry + activation
        return order.entry - activation

    def _bt_trailing_preview_stop(self, order: Any) -> float | None:
        activation_level = self._bt_trailing_activation_level(order)
        distance = safe_float(getattr(order, "trailing_distance_pips", 0.0)) * safe_float(getattr(order, "pip_value", 0.0))
        if activation_level is None or distance <= 0:
            return None
        if order.side == "BUY":
            return activation_level - distance
        return activation_level + distance

    def _draw_period_backtest_exits(self) -> None:
        trades = self.bt_state.closed_trades[-250:]
        if not trades:
            return
        points: list[dict[str, Any]] = []
        for trade in trades:
            color = "#22c55e" if trade.pnl_pips > 0 else "#ef4444"
            points.append(
                {
                    "pos": (trade.exit_index, trade.exit),
                    "symbol": "o",
                    "size": 8,
                    "brush": pg.mkBrush(color),
                    "pen": pg.mkPen("#ffffff", width=0.8),
                }
            )
        item = pg.ScatterPlotItem()
        item.addPoints(points)
        item.setToolTip("Saidas do backtest por periodo")
        item.setZValue(21)
        self.plot.addItem(item)
        self.bt_items.append(item)

    def _add_bt_level(self, start: int, end: int, price: float, color: str, label: str, style: Qt.PenStyle) -> None:
        item = self.plot.plot([start, end], [price, price], pen=pg.mkPen(color, width=1.1, style=style))
        item.setToolTip(label)
        self.bt_items.append(item)
        text = pg.TextItem(f"{label} | {price:.5f}", color=color, anchor=(0, 0.5))
        text.setPos(end + 1, price)
        self.plot.addItem(text)
        self.bt_items.append(text)

    def _clear_period_backtest_items(self) -> None:
        if not hasattr(self, "plot"):
            return
        for item in self.bt_items:
            try:
                self.plot.removeItem(item)
            except Exception:
                pass
        self.bt_items.clear()

    def _schedule_period_backtest_visual_update(self, force: bool = False) -> None:
        now = time.perf_counter()
        if not force and now - self._bt_last_visual_update < 0.045:
            if not self._bt_visual_update_pending:
                self._bt_visual_update_pending = True
                QTimer.singleShot(45, self._flush_period_backtest_visual_update)
            return
        self._flush_period_backtest_visual_update()

    def _flush_period_backtest_visual_update(self) -> None:
        self._bt_visual_update_pending = False
        self._bt_last_visual_update = time.perf_counter()
        self._draw_period_backtest_items()
        self._follow_period_backtest_candle()
        self._update_period_backtest_panel()

    def _period_backtest_interval_ms(self) -> int:
        if not hasattr(self, "bt_speed_slider"):
            return 120
        return max(15, 320 - self.bt_speed_slider.value() * 10)

    def _follow_period_backtest_candle(self) -> None:
        if not self.candles:
            return
        idx = min(max(self.bt_state.index, 0), len(self.candles) - 1)
        left_context = 95
        right_context = 28
        start = max(0, idx - left_context)
        end = min(len(self.candles) - 1, idx + right_context)
        if end <= start:
            return

        lows = [safe_float(row.get("low")) for row in self.candles[start : end + 1]]
        highs = [safe_float(row.get("high")) for row in self.candles[start : end + 1]]
        level_prices = [self.bt_state.price] if self.bt_state.price > 0 else []
        for order in self.bt_state.open_orders:
            level_prices.append(order.entry)
            if order.stop_loss is not None:
                level_prices.append(order.stop_loss)
            if order.take_profit is not None:
                level_prices.append(order.take_profit)
            activation_level = self._bt_trailing_activation_level(order)
            preview_stop = self._bt_trailing_preview_stop(order)
            if activation_level is not None:
                level_prices.append(activation_level)
            if preview_stop is not None:
                level_prices.append(preview_stop)
            if order.trailing_stop is not None:
                level_prices.append(order.trailing_stop)

        low = min(lows + level_prices)
        high = max(highs + level_prices)
        span = high - low
        padding = max(span * 0.12, self._pip_value() * 20.0)
        self.plot.setXRange(start, end + 2, padding=0)
        self.plot.setYRange(low - padding, high + padding, padding=0)

    def _sync_period_backtest_speed_label(self) -> None:
        if not hasattr(self, "bt_speed_label"):
            return
        self.bt_speed_label.setText(f"{self.bt_speed_slider.value()}x | intervalo {self._period_backtest_interval_ms()} ms")
        if self.period_backtest_timer.isActive():
            self.period_backtest_timer.start(self._period_backtest_interval_ms())

    def _update_period_backtest_panel(self) -> None:
        if not hasattr(self, "bt_status"):
            return
        running = self.period_backtest_timer.isActive()
        status = "rodando" if running else ("finalizado" if self.bt_state.finished else "pausado")
        current_time = "-"
        if self.candles and 0 <= self.bt_state.index < len(self.candles):
            current_time = str(self.candles[self.bt_state.index].get("time", "-"))
        self.bt_status.setText(
            f"Status: {status}\n"
            f"Estrategia: {self.bt_strategy_combo.currentText()}\n"
            f"Candle: {self.bt_state.index} / {self.bt_end_spin.value()} | {current_time}\n"
            f"Preco replay: {self.bt_state.price:.5f}\n"
            f"Ordens abertas: {len(self.bt_state.open_orders)} / {self.bt_max_orders_spin.value()} simultaneas\n"
            f"Trades fechados: {len(self.bt_state.closed_trades)} | Total abertas no periodo: {max(0, self.bt_state.next_order_id - 1)}\n"
            f"Clique em um candle para pular/retroceder o replay"
        )
        data = bt_metrics(self.bt_state)
        profit_factor = abs(data["gross_profit"] / data["gross_loss"]) if data["gross_loss"] else 0.0
        rows = [
            ("Abertas", int(data["open"])),
            ("Fechadas", int(data["closed"])),
            ("Vencedoras", int(data["wins"])),
            ("Perdedoras", int(data["losses"])),
            ("Win rate", f"{data['win_rate']:.1f}%"),
            ("Resultado", f"{data['net_pips']:+.1f} pips"),
            ("Lucro bruto", f"{data['gross_profit']:+.1f} pips"),
            ("Prejuizo bruto", f"{data['gross_loss']:+.1f} pips"),
            ("Profit factor", f"{profit_factor:.2f}" if data["gross_loss"] else "-"),
        ]
        self.bt_summary_table.setRowCount(len(rows))
        for row, (name, value) in enumerate(rows):
            self._set_table_item(self.bt_summary_table, row, 0, name)
            self._set_table_item(self.bt_summary_table, row, 1, value)

    @staticmethod
    def _set_table_item(table: QTableWidget, row: int, col: int, value: Any) -> None:
        item = QTableWidgetItem(str(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        table.setItem(row, col, item)

    def _plot_simulation_levels(self, orders: list[dict[str, Any]]) -> None:
        for order in orders:
            idx = int(order["index"])
            side = str(order["side"])
            entry = float(order["entry"])
            stop_loss = order.get("stop_loss")
            take_profit = order.get("take_profit")
            pip_value = self._pip_value()
            trailing_activation = safe_float(order.get("trailing_activation")) * pip_value
            trailing_distance = safe_float(order.get("trailing_distance")) * pip_value
            if side == "BUY":
                trailing_activation_level = entry + trailing_activation if trailing_activation else None
                trailing_stop_level = trailing_activation_level - trailing_distance if trailing_activation_level is not None and trailing_distance else None
            else:
                trailing_activation_level = entry - trailing_activation if trailing_activation else None
                trailing_stop_level = trailing_activation_level + trailing_distance if trailing_activation_level is not None and trailing_distance else None

            self._add_level_segment(idx, entry, self.theme["entry_line"], f"{side} entrada", Qt.SolidLine)
            if stop_loss is not None:
                sl_pips = abs(entry - float(stop_loss)) / pip_value if pip_value else 0.0
                self._add_level_segment(idx, float(stop_loss), self.theme["sl_line"], f"SL {sl_pips:.1f} pips", Qt.DashLine)
            if take_profit is not None:
                tp_pips = abs(float(take_profit) - entry) / pip_value if pip_value else 0.0
                self._add_level_segment(idx, float(take_profit), self.theme["tp_line"], f"TP {tp_pips:.1f} pips", Qt.DashLine)
            if trailing_activation_level is not None:
                activation_pips = abs(float(trailing_activation_level) - entry) / pip_value if pip_value else 0.0
                self._add_level_segment(
                    idx,
                    float(trailing_activation_level),
                    self.theme["trailing_line"],
                    f"TR ativacao {activation_pips:.1f} pips",
                    Qt.DotLine,
                )
            self._add_trailing_drag_simulator(order)

    def _add_level_segment(self, start_index: int, price: float, color: str, label: str, style: Qt.PenStyle) -> None:
        end_index = min(start_index + 80, max(start_index + 1, len(self.candles) - 1))
        item = self.plot.plot(
            [start_index, end_index],
            [price, price],
            pen=pg.mkPen(color, width=1.2, style=style),
        )
        item.setToolTip(label)
        self.simulation_items.append(item)
        text = pg.TextItem(f"{label} | {price:.5f}", color=color, anchor=(0, 0.5))
        text.setPos(end_index + 1, price)
        self.plot.addItem(text)
        self.simulation_items.append(text)

    def _add_trailing_drag_simulator(self, order: dict[str, Any]) -> None:
        key = str(order.get("key"))
        side = str(order.get("side"))
        entry = safe_float(order.get("entry"))
        pip_value = self._pip_value()
        activation_pips = safe_float(order.get("trailing_activation"))
        distance_pips = safe_float(order.get("trailing_distance"))
        if activation_pips <= 0 or distance_pips <= 0:
            return

        runtime = self.trailing_runtime.setdefault(key, {})
        if "sim_price" not in runtime:
            initial_offset = min(10.0, activation_pips) * pip_value
            runtime["sim_price"] = entry + initial_offset if side == "BUY" else entry - initial_offset
            runtime["best_price"] = entry

        sim_line = pg.InfiniteLine(
            pos=runtime["sim_price"],
            angle=0,
            movable=True,
            pen=pg.mkPen("#ffffff", width=1.4, style=Qt.SolidLine),
            label=f"Preco simulado {safe_float(runtime.get('sim_price')):.5f}",
            labelOpts={"position": 0.08, "color": "#ffffff"},
        )
        stop_line = pg.InfiniteLine(
            pos=entry,
            angle=0,
            movable=False,
            pen=pg.mkPen(self.theme["sl_line"], width=1.6, style=Qt.DashDotLine),
            label="TR distancia",
            labelOpts={"position": 0.18, "color": self.theme["sl_line"]},
        )
        self.plot.addItem(sim_line)
        self.plot.addItem(stop_line)
        self.simulation_items.extend([sim_line, stop_line])
        runtime["sim_line"] = sim_line
        runtime["stop_line"] = stop_line
        self._sync_trailing_visual(order, sim_line, stop_line)
        sim_line.sigPositionChanged.connect(lambda line, current_order=order, current_stop=stop_line: self._trailing_drag_changed(current_order, line, current_stop))

    def _trailing_drag_changed(self, order: dict[str, Any], sim_line: Any, stop_line: Any) -> None:
        key = str(order.get("key"))
        runtime = self.trailing_runtime.setdefault(key, {})
        runtime["sim_price"] = float(sim_line.value())
        sim_line.label.setText(f"Preco simulado {runtime['sim_price']:.5f}")
        self._sync_trailing_visual(order, sim_line, stop_line)

    def _update_trailing_drag_stop(self, order: dict[str, Any], sim_line: Any, stop_line: Any) -> None:
        self._sync_trailing_visual(order, sim_line, stop_line)

    def _sync_trailing_visual(self, order: dict[str, Any], sim_line: Any | None = None, stop_line: Any | None = None) -> None:
        key = str(order.get("key"))
        runtime = self.trailing_runtime.setdefault(key, {})
        if sim_line is None:
            sim_line = runtime.get("sim_line")
        if stop_line is None:
            stop_line = runtime.get("stop_line")
        current = safe_float(runtime.get("sim_price"), safe_float(order.get("entry")))
        state = self._update_trailing_state(order, current)
        if sim_line is not None:
            sim_line.blockSignals(True)
            sim_line.setPos(current)
            sim_line.blockSignals(False)
            sim_line.label.setText(f"Preco simulado {current:.5f}")
        if stop_line is None:
            return
        if not state.get("active"):
            stop_line.setVisible(False)
            return
        stop_price = safe_float(state.get("stop_price"))
        stop_line.setVisible(True)
        stop_line.setPos(stop_price)
        stop_line.label.setText(f"TR distancia {state.get('distance_pips', 0.0):.1f} pips | {stop_price:.5f}")

    def _update_trailing_state(self, order: dict[str, Any], current: float) -> dict[str, Any]:
        key = str(order.get("key"))
        side = str(order.get("side"))
        entry = safe_float(order.get("entry"))
        pip_value = self._pip_value()
        activation = safe_float(order.get("trailing_activation")) * pip_value
        distance = safe_float(order.get("trailing_distance")) * pip_value
        runtime = self.trailing_runtime.setdefault(key, {})

        threshold_reached = current >= entry + activation if side == "BUY" else current <= entry - activation
        active = bool(runtime.get("trailing_active")) or threshold_reached
        runtime["sim_price"] = current
        runtime["trailing_active"] = active
        if not active:
            return {"active": False, "distance_pips": safe_float(order.get("trailing_distance"))}

        if side == "BUY":
            runtime["best_price"] = max(safe_float(runtime.get("best_price"), entry), current)
            stop_price = runtime["best_price"] - distance
        else:
            runtime["best_price"] = min(safe_float(runtime.get("best_price"), entry), current)
            stop_price = runtime["best_price"] + distance

        runtime["trailing_stop"] = stop_price
        return {
            "active": True,
            "stop_price": stop_price,
            "distance_pips": distance / pip_value if pip_value else 0.0,
            "best_price": runtime["best_price"],
        }

    def _simulation_arrow_clicked(self, _item: Any, points: list[Any]) -> None:
        if not points:
            return
        key = points[0].data()
        if not key:
            return
        self.selected_order_key = str(key)
        self.show_simulation_levels = True
        self.simulation_dock.setVisible(True)
        self.simulation_dock.raise_()
        self.simulation_result_dock.setVisible(True)
        self.simulation_result_dock.raise_()
        self._sync_simulation_action(True)
        if hasattr(self, "show_levels_checkbox"):
            self.show_levels_checkbox.blockSignals(True)
            self.show_levels_checkbox.setChecked(True)
            self.show_levels_checkbox.blockSignals(False)
        self._load_selected_order_params()
        self.trailing_result = None
        self._update_simulation_result_panel()
        self._update_simulation_status()
        self._redraw_simulation_layer()

    def _selected_order(self) -> dict[str, Any] | None:
        if not self.selected_order_key:
            return None
        for order in self.simulated_orders:
            if order.get("key") == self.selected_order_key:
                return order
        return None

    def _load_selected_order_params(self) -> None:
        order = self._selected_order()
        if not order:
            return
        widgets = [
            self.stop_loss_spin,
            self.take_profit_spin,
            self.trailing_activation_spin,
            self.trailing_distance_spin,
            self.use_stop_loss_checkbox,
            self.use_take_profit_checkbox,
        ]
        for widget in widgets:
            widget.blockSignals(True)
        self.stop_loss_spin.setValue(safe_float(order.get("stop_loss_pips")))
        self.take_profit_spin.setValue(safe_float(order.get("take_profit_pips")))
        self.trailing_activation_spin.setValue(safe_float(order.get("trailing_activation")))
        self.trailing_distance_spin.setValue(safe_float(order.get("trailing_distance")))
        self.use_stop_loss_checkbox.setChecked(order.get("stop_loss") is not None)
        self.use_take_profit_checkbox.setChecked(order.get("take_profit") is not None)
        for widget in widgets:
            widget.blockSignals(False)

    def _store_selected_order_override(self) -> None:
        if not self.selected_order_key:
            return
        self.order_overrides[self.selected_order_key] = {
            "stop_loss": self.stop_loss_spin.value() if self.use_stop_loss_checkbox.isChecked() else 0.0,
            "take_profit": self.take_profit_spin.value() if self.use_take_profit_checkbox.isChecked() else 0.0,
            "trailing_activation": self.trailing_activation_spin.value(),
            "trailing_distance": self.trailing_distance_spin.value(),
        }

    def _reset_selected_trailing_simulation(self) -> None:
        if not self.selected_order_key:
            return
        self._pause_trailing_playback()
        self.trailing_runtime.pop(self.selected_order_key, None)
        self.trailing_play_index = 0
        self.trailing_play_phase = 0
        self.trailing_play_target = None
        self.trailing_result = None
        self._update_simulation_result_panel()
        QTimer.singleShot(0, self._redraw_simulation_layer)

    def _start_trailing_playback(self) -> None:
        order = self._selected_order()
        if not order:
            return
        self.show_simulation_levels = True
        if hasattr(self, "show_levels_checkbox"):
            self.show_levels_checkbox.blockSignals(True)
            self.show_levels_checkbox.setChecked(True)
            self.show_levels_checkbox.blockSignals(False)
        self.trailing_play_order_key = str(order["key"])
        if self.trailing_play_index <= 0:
            self.trailing_play_index = int(order["index"])
            self.trailing_play_phase = 0
            self.trailing_play_target = None
        if self.trailing_play_index >= len(self.candles):
            self.trailing_play_index = int(order["index"])
            self.trailing_play_phase = 0
            self.trailing_play_target = None
        runtime = self.trailing_runtime.setdefault(str(order["key"]), {})
        if "sim_price" not in runtime and self.trailing_play_index < len(self.candles):
            runtime["sim_price"] = safe_float(self.candles[self.trailing_play_index].get("open"), safe_float(order.get("entry")))
            runtime["best_price"] = safe_float(order.get("entry"))
        runtime.pop("finished", None)
        self.trailing_result = None
        self._update_simulation_result_panel()
        self.simulation_result_dock.setVisible(True)
        if not self.trailing_play_timer.isActive():
            self.trailing_play_timer.start(self._playback_interval_ms())
        self._redraw_simulation_layer()

    def _pause_trailing_playback(self) -> None:
        self.trailing_play_timer.stop()

    def _stop_trailing_playback(self) -> None:
        self.trailing_play_timer.stop()
        self.trailing_play_order_key = None
        self.trailing_play_index = 0
        self.trailing_play_phase = 0
        self.trailing_play_target = None
        self._clear_trailing_highlight()
        if self.selected_order_key:
            self.trailing_runtime.pop(self.selected_order_key, None)
        self.trailing_result = None
        self._update_simulation_result_panel()
        QTimer.singleShot(0, self._redraw_simulation_layer)

    def _advance_trailing_playback(self) -> None:
        order = self._selected_order()
        if not order or self.trailing_play_order_key != order.get("key"):
            self._pause_trailing_playback()
            return
        if self.trailing_play_index >= len(self.candles):
            self._pause_trailing_playback()
            return

        candle = self.candles[self.trailing_play_index]
        side = str(order.get("side"))
        sequence = ["open", "low", "high", "close"] if side == "BUY" else ["open", "high", "low", "close"]
        field = sequence[self.trailing_play_phase]
        target = safe_float(candle.get(field))
        runtime = self.trailing_runtime.setdefault(str(order["key"]), {})
        current = safe_float(runtime.get("sim_price"), safe_float(candle.get("open"), safe_float(order.get("entry"))))
        step = max(self.trailing_step_spin.value() * self._pip_value(), self._pip_value())
        distance = abs(target - current)
        if distance > step:
            price = current + step if target > current else current - step
        else:
            price = target
            self.trailing_play_phase += 1
            self.trailing_play_target = None
            if self.trailing_play_phase >= len(sequence):
                self.trailing_play_phase = 0
                self.trailing_play_index += 1
        if distance > step:
            self.trailing_play_target = target
        runtime["sim_price"] = price
        self._sync_trailing_visual(order)
        exit_reason, exit_price = self._simulation_exit_hit(order, price)
        if exit_reason:
            self._finish_trailing_playback(order, exit_price, exit_reason)
            return
        self._plot_trailing_highlight()

    def _simulation_exit_hit(self, order: dict[str, Any], price: float) -> tuple[str | None, float]:
        side = str(order.get("side"))
        stop_loss = order.get("stop_loss")
        take_profit = order.get("take_profit")

        if side == "BUY":
            if stop_loss is not None and price <= safe_float(stop_loss):
                return "stop_loss", safe_float(stop_loss)
            if take_profit is not None and price >= safe_float(take_profit):
                return "take_profit", safe_float(take_profit)
        else:
            if stop_loss is not None and price >= safe_float(stop_loss):
                return "stop_loss", safe_float(stop_loss)
            if take_profit is not None and price <= safe_float(take_profit):
                return "take_profit", safe_float(take_profit)

        if self._trailing_stop_hit(order, price):
            runtime = self.trailing_runtime.setdefault(str(order.get("key")), {})
            return "trailing_stop", safe_float(runtime.get("trailing_stop"), price)
        return None, price

    def _trailing_stop_hit(self, order: dict[str, Any], price: float) -> bool:
        runtime = self.trailing_runtime.setdefault(str(order.get("key")), {})
        if not runtime.get("trailing_active"):
            return False
        stop_price = runtime.get("trailing_stop")
        if stop_price is None:
            return False
        side = str(order.get("side"))
        stop = safe_float(stop_price)
        return price <= stop if side == "BUY" else price >= stop

    def _finish_trailing_playback(self, order: dict[str, Any], price: float, reason: str) -> None:
        self._pause_trailing_playback()
        runtime = self.trailing_runtime.setdefault(str(order.get("key")), {})
        if reason == "trailing_stop" and runtime.get("trailing_stop") is not None:
            price = safe_float(runtime.get("trailing_stop"), price)
        runtime["finished"] = True
        runtime["exit_price"] = price
        runtime["exit_reason"] = reason
        entry = safe_float(order.get("entry"))
        side = str(order.get("side"))
        pnl = (price - entry) if side == "BUY" else (entry - price)
        pip_value = self._pip_value()
        pnl_pips = pnl / pip_value if pip_value else 0.0
        self.trailing_result = {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "side": side,
            "entry": entry,
            "exit": price,
            "reason": reason,
            "pnl_pips": pnl_pips,
            "trailing_stop": runtime.get("trailing_stop"),
            "best_price": runtime.get("best_price"),
            "candle_index": self.trailing_play_index,
            "phase": self.trailing_play_phase,
        }
        self._update_simulation_result_panel()
        self.simulation_result_dock.setVisible(True)
        self.simulation_result_dock.raise_()
        self._plot_trailing_highlight()

    def _update_simulation_result_panel(self) -> None:
        if not hasattr(self, "simulation_result_summary"):
            return
        result = self.trailing_result
        if not result:
            self.simulation_result_summary.setText(
                "Selecione uma seta e inicie o replay do trailing.\n"
                "Quando o preco simulado tocar a linha de distancia, o resultado aparece aqui."
            )
            self.simulation_result_table.setRowCount(0)
            return
        pnl_pips = safe_float(result.get("pnl_pips"))
        lot = self.result_lot_spin.value()
        money = self._money_result_from_pips(self.symbol, pnl_pips, lot)
        status = "GANHO" if pnl_pips >= 0 else "PREJUIZO"
        self.simulation_result_summary.setText(
            f"{status} | {pnl_pips:+.1f} pips | {money['usd']:+.2f} USD\n"
            f"{result.get('symbol')} {result.get('timeframe')} {result.get('side')}\n"
            f"Motivo: {self._exit_reason_label(str(result.get('reason')))}"
        )
        rows = [
            ("Lote", f"{lot:.2f}"),
            ("Entrada", f"{safe_float(result.get('entry')):.5f}"),
            ("Saida", f"{safe_float(result.get('exit')):.5f}"),
            ("Resultado", f"{pnl_pips:+.1f} pips"),
            ("Resultado USD", f"{money['usd']:+.2f}"),
            ("Resultado BRL", f"{money['brl']:+.2f}"),
            ("USD/pip/lote", f"{money['usd_per_pip_per_lot']:.2f}"),
            ("Trailing stop", f"{safe_float(result.get('trailing_stop')):.5f}"),
            ("Melhor preco", f"{safe_float(result.get('best_price')):.5f}"),
            ("Candle", result.get("candle_index", "-")),
            ("Fase", result.get("phase", "-")),
        ]
        self.simulation_result_table.setRowCount(len(rows))
        for row, (name, value) in enumerate(rows):
            self._set_table_item(self.simulation_result_table, row, 0, name)
            self._set_table_item(self.simulation_result_table, row, 1, value)

    def _money_result_from_pips(self, symbol: str, pnl_pips: float, lot: float) -> dict[str, float]:
        usd_per_pip_per_lot = self._usd_per_pip_per_lot(symbol)
        usd = pnl_pips * usd_per_pip_per_lot * lot
        brl = usd * self._usd_brl_rate()
        return {
            "usd": usd,
            "brl": brl,
            "usd_per_pip_per_lot": usd_per_pip_per_lot,
        }

    def _usd_per_pip_per_lot(self, symbol: str) -> float:
        normalized = normalize_symbol(symbol)
        if normalized in {"GOLD", "XAUUSD"}:
            return 10.0
        if "JPY" in normalized:
            return 9.0
        return 10.0

    def _usd_brl_rate(self) -> float:
        return 5.0

    @staticmethod
    def _exit_reason_label(reason: str) -> str:
        labels = {
            "stop_loss": "Stop loss",
            "take_profit": "Take profit",
            "trailing_stop": "Trailing stop",
        }
        return labels.get(reason, reason or "-")

    def _playback_interval_ms(self) -> int:
        speed = self.trailing_speed_slider.value() if hasattr(self, "trailing_speed_slider") else 8
        return max(25, 1100 - speed * 50)

    def _sync_playback_speed_label(self, *_args: Any) -> None:
        if not hasattr(self, "trailing_speed_label"):
            return
        interval = self._playback_interval_ms()
        self.trailing_speed_label.setText(f"{self.trailing_speed_slider.value()}x | intervalo {interval} ms")
        if hasattr(self, "trailing_play_timer") and self.trailing_play_timer.isActive():
            self.trailing_play_timer.setInterval(interval)

    def _clear_trailing_highlight(self) -> None:
        if self.trailing_highlight_item is not None:
            try:
                self.plot.removeItem(self.trailing_highlight_item)
            except Exception:
                pass
            self.trailing_highlight_item = None

    def _plot_trailing_highlight(self) -> None:
        self._clear_trailing_highlight()
        timer = getattr(self, "trailing_play_timer", None)
        if timer is None or not timer.isActive() or self.trailing_play_index >= len(self.candles):
            return
        region = pg.LinearRegionItem(
            values=[self.trailing_play_index - 0.5, self.trailing_play_index + 0.5],
            orientation="vertical",
            movable=False,
            brush=pg.mkBrush(255, 255, 255, 35),
        )
        region.setZValue(-5)
        self.plot.addItem(region)
        self.trailing_highlight_item = region

    def _pip_value(self) -> float:
        return pip_value(self.symbol)

    def _toggle_follow(self, checked: bool) -> None:
        self.auto_follow = checked

    def _toggle_simulation_levels(self, checked: bool) -> None:
        self.show_simulation_levels = checked
        self._redraw_simulation_layer()

    def _toggle_simulation_panel(self, checked: bool) -> None:
        self.simulation_dock.setVisible(checked)
        if checked:
            self.simulation_dock.raise_()
            self.simulation_result_dock.setVisible(True)
            self.simulation_result_dock.raise_()

    def _toggle_probability_panel(self, checked: bool) -> None:
        self.probability_dock.setVisible(checked)
        if checked:
            self.probability_dock.raise_()
            self._update_probability_panel()

    def _toggle_watchlist_panel(self, checked: bool) -> None:
        self.watchlist_dock.setVisible(checked)
        if checked:
            self.watchlist_dock.raise_()
            self._update_watchlist_panel()

    def _toggle_alerts_panel(self, checked: bool) -> None:
        self.alerts_dock.setVisible(checked)
        if checked:
            self.alerts_dock.raise_()
            self._update_alerts_panel()

    def _toggle_positions_panel(self, checked: bool) -> None:
        self.positions_dock.setVisible(checked)
        if checked:
            self.positions_dock.raise_()
            self._update_positions_panel()

    def _toggle_properties_panel(self, checked: bool) -> None:
        self.properties_dock.setVisible(checked)
        if checked:
            self.properties_dock.raise_()

    def _toggle_analysis_panel(self, checked: bool) -> None:
        self.analysis_dock.setVisible(checked)
        if checked:
            self.analysis_dock.raise_()
            self._update_analysis_panel()

    def _toggle_period_backtest_panel(self, checked: bool) -> None:
        self.period_backtest_dock.setVisible(checked)
        if checked:
            self.period_backtest_dock.raise_()
            self._sync_period_backtest_ranges()
            self._update_period_backtest_panel()

    def _toggle_layers_panel(self, checked: bool) -> None:
        self.layers_dock.setVisible(checked)
        if checked:
            self.layers_dock.raise_()
            self._update_layers_panel()

    def _sync_simulation_action(self, visible: bool) -> None:
        self.simulation_action.blockSignals(True)
        self.simulation_action.setChecked(visible)
        self.simulation_action.blockSignals(False)

    def _sync_probability_action(self, visible: bool) -> None:
        self.probability_action.blockSignals(True)
        self.probability_action.setChecked(visible)
        self.probability_action.blockSignals(False)

    def _sync_watchlist_action(self, visible: bool) -> None:
        self.watchlist_action.blockSignals(True)
        self.watchlist_action.setChecked(visible)
        self.watchlist_action.blockSignals(False)

    def _sync_alerts_action(self, visible: bool) -> None:
        self.alerts_action.blockSignals(True)
        self.alerts_action.setChecked(visible)
        self.alerts_action.blockSignals(False)

    def _sync_positions_action(self, visible: bool) -> None:
        self.positions_action.blockSignals(True)
        self.positions_action.setChecked(visible)
        self.positions_action.blockSignals(False)

    def _sync_properties_action(self, visible: bool) -> None:
        self.properties_action.blockSignals(True)
        self.properties_action.setChecked(visible)
        self.properties_action.blockSignals(False)

    def _sync_analysis_action(self, visible: bool) -> None:
        self.analysis_action.blockSignals(True)
        self.analysis_action.setChecked(visible)
        self.analysis_action.blockSignals(False)

    def _sync_period_backtest_action(self, visible: bool) -> None:
        self.period_backtest_action.blockSignals(True)
        self.period_backtest_action.setChecked(visible)
        self.period_backtest_action.blockSignals(False)

    def _sync_layers_action(self, visible: bool) -> None:
        self.layers_action.blockSignals(True)
        self.layers_action.setChecked(visible)
        self.layers_action.blockSignals(False)

    def _apply_theme_from_panel(self) -> None:
        for key, field in self.color_inputs.items():
            value = field.text().strip()
            if self._is_color(value):
                self.theme[key] = value
            else:
                field.setText(self.theme[key])
        self._apply_candle_theme()
        self._draw_chart()

    def _apply_candle_theme(self) -> None:
        if hasattr(self.candle_item, "set_colors"):
            self.candle_item.set_colors(self.theme["bull_candle"], self.theme["bear_candle"])

    @staticmethod
    def _is_color(value: str) -> bool:
        return is_color(value)

    def _pip_spinbox(self, minimum: float, maximum: float, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(1)
        spin.setRange(minimum, maximum)
        spin.setSingleStep(1.0)
        spin.setValue(value)
        spin.setSuffix(" pips")
        return spin

    def _strategy_names(self) -> list[str]:
        return strategy_names()

    def _update_simulation_status(self) -> None:
        if not hasattr(self, "simulation_status"):
            return
        self.simulation_status.setText(
            "Parametros ativos:\n"
            f"Estrategia: {self.strategy_combo.currentText()}\n"
            f"Ordem selecionada: {self.selected_order_key or '-'}\n"
            f"SL: {'ON' if self.use_stop_loss_checkbox.isChecked() else 'OFF'} "
            f"{self.stop_loss_spin.value():.1f} pips\n"
            f"TP: {'ON' if self.use_take_profit_checkbox.isChecked() else 'OFF'} "
            f"{self.take_profit_spin.value():.1f} pips\n"
            f"Trailing: ativa em {self.trailing_activation_spin.value():.1f} pips, "
            f"distancia {self.trailing_distance_spin.value():.1f} pips\n"
            f"Replay: passo {self.trailing_step_spin.value():.1f} pips, "
            f"velocidade {self.trailing_speed_slider.value()}x\n"
            f"Ordens simuladas no grafico: {len(self.simulated_orders)}\n"
            f"Trades analisados: {len(self.simulated_trades)}"
        )

    def _read_market_data(self) -> tuple[list[dict[str, Any]], tuple[Any, ...], str]:
        result = self.market_data.read_market_data(self.symbol, self.timeframe, self.max_bars)
        self._sync_market_state()
        return result

    def _read_csv_history(self) -> list[dict[str, Any]]:
        return self.market_data.read_csv_history(self.symbol, self.timeframe, self.max_bars)

    def _merge_candles(self, historical: list[dict[str, Any]], live: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.market_data.merge_candles(historical, live, self.max_bars)

    def _read_ohlc_mt5(self) -> list[dict[str, Any]]:
        rows = self.market_data.read_ohlc_mt5(self.symbol, self.timeframe)
        self._sync_market_state()
        return rows

    def _initialize_mt5(self) -> bool:
        ready = self.market_data.initialize_mt5()
        self._sync_market_state()
        return ready

    def _status_text(self, suffix: str = "") -> str:
        text = (
            f"{self.symbol} -> {self.last_broker_symbol} | {self.timeframe} | "
            f"candles={len(self.candles)} | {self.data_source} | "
            f"{self.first_candle_time} -> {self.last_candle_time}"
        )
        if "MT5" not in self.data_source and self.last_mt5_error:
            text += f" | {self.last_mt5_error}"
        if suffix:
            text += f" | {suffix}"
        return text

    def _source_key(self) -> tuple[str, str, float, int]:
        return self.market_data.source_key(self.symbol, self.timeframe)

    def _source_path(self) -> Path | None:
        return self.market_data.source_path(self.symbol, self.timeframe)

    def _sync_market_state(self) -> None:
        self.mt5_ready = self.market_data.mt5_ready
        self.last_broker_symbol = self.market_data.last_broker_symbol
        self.last_mt5_error = self.market_data.last_mt5_error
        self.broker_symbols = self.market_data.broker_symbols

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


def main() -> None:
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    window = CandleChartWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
