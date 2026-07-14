using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Chart;
using FusionTerminalWindows.Data;
using FusionTerminalWindows.Models;
using FusionTerminalWindows.Theme;
using FusionTerminalWindows.Widgets;

namespace FusionTerminalWindows;

public sealed class MainForm : Form
{
    private readonly CandleChartControl _chart = new();
    private readonly CsvCandleLoader _loader;
    private readonly TerminalSnapshotLoader _snapshotLoader;
    private readonly SignalEventLoader _signalLoader;
    private readonly ProbabilityPanel _probabilityPanel;
    private readonly TechnicalAnalysisPanel _technicalPanel;
    private readonly OperationalMatrixPanel _operationalMatrixPanel;
    private readonly SimulationPanel _simulationPanel = new();
    private readonly BacktestPanel _backtestPanel;
    private readonly EventTablePanel _signalsPanel;
    private readonly EventTablePanel _ordersPanel;
    private readonly EventTablePanel _layersPanel;
    private readonly EventTablePanel _eventsPanel;
    private Form? _readingWindow;
    private readonly System.Windows.Forms.Timer _marketRefreshTimer = new() { Interval = 5000 };
    private readonly System.Windows.Forms.Timer _simulationTimer = new();
    private readonly TextBox _symbolCombo = new() { Width = 118, Text = "AUDUSD" };
    private readonly TextBox _timeframeCombo = new() { Width = 62, Text = "M15" };
    private readonly NumericUpDown _rightMarginSpin = new() { Width = 54, Minimum = 0, Maximum = 120, Value = 18 };
    private readonly Label _connection = new() { Dock = DockStyle.Fill, ForeColor = TerminalTheme.Muted, Padding = new Padding(8, 2, 0, 0), AutoEllipsis = true };
    private readonly Button _robotButton;
    private readonly Label _robotStatus = new() { Dock = DockStyle.Fill, ForeColor = TerminalTheme.Muted, Padding = new Padding(8, 2, 0, 0), AutoEllipsis = true, Text = "Robo: parado" };
    private readonly string _repoRoot;
    private Process? _fusionProcess;
    private Process? _bridgeProcess;
    private readonly ToolStripStatusLabel _statusLeft = new() { Spring = true, TextAlign = ContentAlignment.MiddleLeft };
    private readonly ToolStripStatusLabel _statusRight = new() { TextAlign = ContentAlignment.MiddleRight };
    private readonly TreeView _navigator = new() { Dock = DockStyle.Fill, BorderStyle = BorderStyle.None };
    private readonly TabControl _rightTabs = new() { Dock = DockStyle.Fill };
    private readonly TabControl _bottomTabs = new() { Dock = DockStyle.Fill };
    private readonly Panel _centerHost = new() { Dock = DockStyle.Fill, BackColor = TerminalTheme.Background };
    private ColumnStyle? _leftDockColumn;
    private ColumnStyle? _rightDockColumn;
    private RowStyle? _bottomDockRow;
    private Control? _leftDock;
    private Control? _chartArea;
    private Control? _bottomDock;
    private string _lastModuleSymbol = "";
    private string _lastModuleTimeframe = "";
    private string _lastChartSymbol = "";
    private string _lastChartTimeframe = "";
    private DateTime _lastModuleRefresh = DateTime.MinValue;
    private bool _isLoadingMarketData;
    private bool _suppressMarketTextEvents;
    private readonly Queue<Action> _moduleLoadQueue = new();
    private readonly System.Windows.Forms.Timer _moduleLoadTimer = new() { Interval = 150 };
    private readonly System.Windows.Forms.Timer _marketLoadDebounceTimer = new() { Interval = 250 };
    private bool _pendingMarketRefreshSymbols;

    public MainForm()
    {
        Text = "Fusion Control Center";
        AutoScaleMode = AutoScaleMode.Dpi;
        Width = 1460;
        Height = 880;
        MinimumSize = new Size(1220, 760);
        StartPosition = FormStartPosition.CenterScreen;
        WindowState = FormWindowState.Maximized;
        BackColor = TerminalTheme.Background;
        ForeColor = TerminalTheme.Text;
        Font = new Font("Segoe UI", 9f);
        AutoScroll = false;

        Program.StartupTrace("MainForm base properties ok");
        _repoRoot = FindRepoRoot(AppContext.BaseDirectory);
        Program.StartupTrace("repo root=" + _repoRoot);
        Program.StartupTrace("creating loaders/panels start");
        _loader = new CsvCandleLoader(_repoRoot);
        _snapshotLoader = new TerminalSnapshotLoader(_repoRoot);
        _signalLoader = new SignalEventLoader(_repoRoot);
        _probabilityPanel = new ProbabilityPanel(_repoRoot);
        _technicalPanel = new TechnicalAnalysisPanel(_repoRoot);
        _operationalMatrixPanel = new OperationalMatrixPanel(_repoRoot);
        _backtestPanel = new BacktestPanel(_repoRoot);
        _signalsPanel = new EventTablePanel(_repoRoot, EventTableMode.Signals);
        _ordersPanel = new EventTablePanel(_repoRoot, EventTableMode.Orders);
        _layersPanel = new EventTablePanel(_repoRoot, EventTableMode.Layers);
        _eventsPanel = new EventTablePanel(_repoRoot, EventTableMode.Events);
        Program.StartupTrace("creating loaders/panels ok");
        _robotButton = Button("Iniciar Robo", 112);
        _robotButton.BackColor = TerminalTheme.PositiveSoft;
        _robotButton.ForeColor = TerminalTheme.Text;
        _robotButton.Click += (_, _) => ToggleFusionRobot();
        _marketRefreshTimer.Tick += (_, _) => QueueMarketDataLoad(refreshSymbols: false);
        _simulationTimer.Tick += (_, _) =>
        {
            _simulationTimer.Interval = _chart.SimulationTimerInterval();
            _chart.StepSimulationPlayback();
        };
        _moduleLoadTimer.Tick += (_, _) => DrainModuleLoadQueue();
        _marketLoadDebounceTimer.Tick += (_, _) =>
        {
            _marketLoadDebounceTimer.Stop();
            var refreshSymbols = _pendingMarketRefreshSymbols;
            _pendingMarketRefreshSymbols = false;
            QueueMarketDataLoad(refreshSymbols);
        };
        _chart.SignalSelected += (_, signal) => OpenSimulationFromSignal(signal);
        _backtestPanel.TradesApplied += (_, trades) => _chart.SetBacktestTrades(trades);

        Program.StartupTrace("building controls start");
        MainMenuStrip = BuildMenu();
        var shell = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 4,
            ColumnCount = 1,
            BackColor = TerminalTheme.Background,
        };
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 124));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 48));
        shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        shell.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        shell.Controls.Add(BuildHeader(), 0, 0);
        shell.Controls.Add(BuildToolbar(), 0, 1);
        shell.Controls.Add(BuildWorkspace(), 0, 2);
        shell.Controls.Add(BuildStatusBar(), 0, 3);
        Controls.Add(shell);
        Program.StartupTrace("building controls ok");

        Program.StartupTrace("timeframe setup deferred");
        Program.StartupTrace("ConfigureNavigator start");
        ConfigureNavigator();
        Program.StartupTrace("ConfigureNavigator ok");
        Program.StartupTrace("MainForm ctor end");
        Program.StartupTrace("Shown handler attach start");
        Shown += (_, _) => BeginInvoke(InitializeMarketData);
        Program.StartupTrace("Shown handler attach ok");
    }

    private void InitializeMarketData()
    {
        Program.StartupTrace("InitializeMarketData start");
        _statusLeft.Text = "Carregando dados em segundo plano...";
        _connection.Text = "MT5: iniciando ponte";
        StartMt5BridgeIfAvailable();
        QueueMarketDataLoad(refreshSymbols: true);
        _marketRefreshTimer.Start();
        Program.StartupTrace("InitializeMarketData queued background load");
    }

    private MenuStrip BuildMenu()
    {
        var menu = new MenuStrip
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.PanelAlt,
            ForeColor = TerminalTheme.Text,
        };

        menu.Items.Add(MenuItem("Arquivo", "Abrir workspace", "Salvar layout", "Sair"));
        menu.Items.Add(MenuItem("Mercado", "Reconectar MT5", "Atualizar candles", "Fonte de dados"));
        menu.Items.Add(BuildInsertMenu());
        menu.Items.Add(BuildToolsMenu());
        menu.Items.Add(MenuItem("Analise", "Probabilidades", "Leitura tecnica", "Matriz operacional", "Camadas"));
        menu.Items.Add(MenuItem("Backtest", "Backtest visual", "Replay historico", "Banco de estrategias"));
        menu.Items.Add(MenuItem("Alertas", "Alertas sonoros", "Alertas visuais", "Historico"));
        return menu;
    }

    private Control BuildHeader()
    {
        var header = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            Padding = new Padding(16, 6, 16, 10),
            RowCount = 1,
            ColumnCount = 3,
        };
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 340));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 300));

        var brand = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            WrapContents = false,
            Padding = new Padding(0, 7, 0, 0),
        };
        brand.Controls.Add(new Label
        {
            Text = "FUSION",
            AutoSize = true,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI Semibold", 21f, FontStyle.Bold),
            Margin = new Padding(0, 0, 10, 0),
        });
        brand.Controls.Add(new Label
        {
            Text = "Control Center",
            AutoSize = true,
            ForeColor = TerminalTheme.Primary,
            Font = new Font("Segoe UI", 10.5f, FontStyle.Bold),
            Padding = new Padding(0, 14, 0, 0),
        });

        var center = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            WrapContents = false,
            Padding = new Padding(8, 14, 8, 0),
        };
        center.Controls.Add(HeaderButton("Home", 82, ShowChartInWorkspace));
        center.Controls.Add(HeaderButton("Mercado", 100, ShowChartInWorkspace));
        center.Controls.Add(HeaderButton("Analise", 92, () => SelectReadingTabInWorkspace("Probabilidades")));
        center.Controls.Add(HeaderButton("Ordens", 88, () => SelectReadingTabInWorkspace("Ordens")));
        center.Controls.Add(HeaderButton("Backtest", 98, () => SelectBottomTab("Backtest")));

        var status = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(12, 4, 12, 4),
            RowCount = 2,
            ColumnCount = 1,
        };
        status.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        status.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        status.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        status.Paint += (_, e) => DrawBorder(e.Graphics, status.ClientRectangle);
        status.Controls.Add(StatusCaption("STATUS DO ROBO"), 0, 0);
        status.Controls.Add(_robotStatus, 0, 1);

        header.Controls.Add(brand, 0, 0);
        header.Controls.Add(center, 1, 0);
        header.Controls.Add(status, 2, 0);
        return header;
    }
    private ToolStripMenuItem BuildToolsMenu()
    {
        var menu = new ToolStripMenuItem("Ferramentas");
        menu.DropDownItems.Add(new ToolStripMenuItem("Mostrar navegador", null, (_, _) => SetLeftDockVisible(true)));
        menu.DropDownItems.Add(new ToolStripMenuItem("Leitura", null, (_, _) => ShowReadingWindow()));
        menu.DropDownItems.Add(new ToolStripMenuItem("Mostrar painel inferior", null, (_, _) => SetBottomDockVisible(true)));
        menu.DropDownItems.Add(new ToolStripSeparator());
        menu.DropDownItems.Add(new ToolStripMenuItem("Probabilidades", null, (_, _) => SelectReadingTabInWorkspace("Probabilidades")));
        menu.DropDownItems.Add(new ToolStripMenuItem("Leitura tecnica", null, (_, _) => SelectReadingTabInWorkspace("Leitura Tecnica")));
        menu.DropDownItems.Add(new ToolStripMenuItem("Matriz operacional", null, (_, _) => SelectReadingTabInWorkspace("Matriz Operacional")));
        menu.DropDownItems.Add(new ToolStripMenuItem("Sinais e alertas", null, (_, _) => SelectReadingTabInWorkspace("Sinais")));
        menu.DropDownItems.Add(new ToolStripMenuItem("Ordens e posicoes", null, (_, _) => SelectReadingTabInWorkspace("Ordens")));
        menu.DropDownItems.Add(new ToolStripMenuItem("Simulacao", null, (_, _) => SelectBottomTab("Simulacao")));
        menu.DropDownItems.Add(new ToolStripMenuItem("Backtest", null, (_, _) => SelectBottomTab("Backtest")));
        return menu;
    }

    private static ToolStripMenuItem MenuItem(string title, params string[] items)
    {
        var menu = new ToolStripMenuItem(title);
        foreach (var item in items)
        {
            menu.DropDownItems.Add(new ToolStripMenuItem(item));
        }
        return menu;
    }

    private ToolStripMenuItem BuildInsertMenu()
    {
        var menu = new ToolStripMenuItem("Inserir");
        var indicators = new ToolStripMenuItem("Indicadores");
        indicators.DropDownItems.Add(new ToolStripMenuItem("EMA 9/21/50", null, (_, _) => _chart.MovingAverageMode = MovingAverageMode.Exponential));
        indicators.DropDownItems.Add(new ToolStripMenuItem("MA 9/21/50", null, (_, _) => _chart.MovingAverageMode = MovingAverageMode.Simple));
        indicators.DropDownItems.Add(new ToolStripMenuItem("Remover indicadores", null, (_, _) => _chart.MovingAverageMode = MovingAverageMode.None));
        indicators.DropDownItems.Add(new ToolStripMenuItem("Gerenciar indicadores..."));
        menu.DropDownItems.Add(indicators);
        menu.DropDownItems.Add(new ToolStripMenuItem("Objetos"));
        menu.DropDownItems.Add(new ToolStripMenuItem("Alertas no grafico"));
        return menu;
    }

    private Control BuildToolbar()
    {
        var toolbar = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.PanelAlt,
            Padding = new Padding(14, 7, 14, 6),
            WrapContents = false,
        };

        var refresh = Button("Atualizar", 96);
        var latest = Button("Ultimo", 78);
        var zoomIn = Button("+", 32);
        var zoomOut = Button("-", 32);
        refresh.Click += (_, _) => RequestMarketDataLoad(refreshSymbols: true);
        latest.Click += (_, _) => _chart.ResetViewToLatest();
        zoomIn.Click += (_, _) => _chart.ZoomIn();
        zoomOut.Click += (_, _) => _chart.ZoomOut();
        _timeframeCombo.TextChanged += (_, _) =>
        {
            if (!_suppressMarketTextEvents)
            {
                RequestMarketDataLoad(refreshSymbols: true);
            }
        };
        _symbolCombo.TextChanged += (_, _) =>
        {
            if (!_suppressMarketTextEvents)
            {
                RequestMarketDataLoad(refreshSymbols: false);
            }
        };
        _rightMarginSpin.ValueChanged += (_, _) => _chart.RightMarginCandles = (int)_rightMarginSpin.Value;

        toolbar.Controls.Add(ToolGroup("Ativo", _symbolCombo, Label("TF"), _timeframeCombo, refresh));
        toolbar.Controls.Add(ToolGroup("Grafico", Label("Zoom"), zoomOut, zoomIn, latest, Label("Margem"), _rightMarginSpin));
        toolbar.Controls.Add(ToolGroup("Robo", _robotButton));
        toolbar.Controls.Add(ToolGroup("Modulos", HeaderButton("Leitura", 76, () => SelectReadingTabInWorkspace("Probabilidades")), HeaderButton("Eventos", 88, () => SelectReadingTabInWorkspace("Eventos")), HeaderButton("Simular", 86, () => SelectBottomTab("Simulacao"))));
        return toolbar;
    }
    private Control BuildWorkspace()
    {
        var main = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Border,
            ColumnCount = 4,
            RowCount = 2,
        };
        _leftDockColumn = new ColumnStyle(SizeType.Absolute, 300);
        _rightDockColumn = new ColumnStyle(SizeType.Absolute, 0);
        _bottomDockRow = new RowStyle(SizeType.Absolute, 260);
        main.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 58));
        main.ColumnStyles.Add(_leftDockColumn);
        main.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        main.ColumnStyles.Add(_rightDockColumn);
        main.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        main.RowStyles.Add(_bottomDockRow);

        _leftDock = BuildNavigatorPanel();
        _chartArea = BuildChartArea();
        _bottomDock = BuildBottomPanel();

        var navigationRail = BuildNavigationRail();
        main.Controls.Add(navigationRail, 0, 0);
        main.SetRowSpan(navigationRail, 2);
        main.Controls.Add(_leftDock, 1, 0);
        main.SetRowSpan(_leftDock, 2);
        _centerHost.Controls.Add(_chartArea);
        main.Controls.Add(_centerHost, 2, 0);
        main.Controls.Add(_bottomDock, 2, 1);
        main.SetColumnSpan(_bottomDock, 2);
        return main;
    }


    private Control BuildNavigationRail()
    {
        var rail = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = Color.FromArgb(8, 15, 22),
            Padding = new Padding(6, 10, 6, 10),
        };
        var buttons = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            AutoScroll = true,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            BackColor = rail.BackColor,
        };

        buttons.Controls.Add(RailButton("⌂", "Home", ShowModuleCatalog, true));
        buttons.Controls.Add(RailButton("▣", "Mercado", ShowChartInWorkspace));
        buttons.Controls.Add(RailButton("⌁", "Grafico", ShowChartInWorkspace));
        buttons.Controls.Add(RailButton("!", "Sinais", () => SelectReadingTabInWorkspace("Sinais")));
        buttons.Controls.Add(RailButton("≡", "Ordens", () => SelectReadingTabInWorkspace("Ordens")));
        buttons.Controls.Add(RailButton("◈", "Portfolio", () => ShowWorkspaceModule("Portfolio", "Exposicao, correlacao, risco agregado e desempenho da carteira.")));
        buttons.Controls.Add(RailButton("↗", "Analise", () => SelectReadingTabInWorkspace("Probabilidades")));
        buttons.Controls.Add(RailButton("♙", "Estrategias", () => ShowWorkspaceModule("Estrategias", "Catalogo, ranking, parametros e desempenho das estrategias.")));
        buttons.Controls.Add(RailButton("B", "Backtest", () => SelectBottomTab("Backtest")));
        buttons.Controls.Add(RailButton("▶", "Simulacao", () => SelectBottomTab("Simulacao")));
        buttons.Controls.Add(RailButton("□", "Eventos", () => SelectReadingTabInWorkspace("Eventos")));
        buttons.Controls.Add(RailButton("R", "Relatorios", () => ShowWorkspaceModule("Relatorios", "Resultados diarios, semanais, mensais e exportacoes.")));
        buttons.Controls.Add(RailButton("L", "Logs", () => ShowWorkspaceModule("Logs e auditoria", "Decisoes, ordens, risco, mercado, modelos e integracoes.")));
        buttons.Controls.Add(RailButton("♥", "Saude do sistema", () => ShowWorkspaceModule("Saude do sistema", "Conectividade, latencia, processos, dados e prontidao operacional.")));
        buttons.Controls.Add(RailButton("⚙", "Configuracoes", () => ShowWorkspaceModule("Configuracoes", "Mercado, risco, operacao, interface, seguranca e perfis.")));
        buttons.Controls.Add(RailButton("?", "Ajuda", () => ShowWorkspaceModule("Ajuda", "Documentacao e orientacoes do Fusion Control Center.")));
        buttons.Controls.Add(RailButton("⇥", "Sair", Close));

        rail.Controls.Add(buttons);
        return rail;
    }

    private void ShowModuleCatalog()
    {
        _centerHost.Controls.Clear();
        _centerHost.Controls.Add(new ModuleCatalogPanel());
    }

    private void ShowWorkspaceModule(string title, string description)
    {
        _centerHost.Controls.Clear();
        _centerHost.Controls.Add(new ModulePlaceholder(title, description));
    }

    private static Button RailButton(string glyph, string hint, Action onClick, bool active = false)
    {
        var button = new Button
        {
            Text = glyph,
            Width = 42,
            Height = 36,
            FlatStyle = FlatStyle.Flat,
            BackColor = active ? TerminalTheme.PrimarySoft : Color.FromArgb(8, 15, 22),
            ForeColor = active ? TerminalTheme.Primary : TerminalTheme.Muted,
            Font = new Font("Segoe UI Symbol", 12f, FontStyle.Bold),
            Margin = new Padding(0, 0, 0, 3),
            Cursor = Cursors.Hand,
            AccessibleName = hint,
        };
        button.FlatAppearance.BorderSize = 0;
        button.FlatAppearance.MouseOverBackColor = TerminalTheme.PanelSoft;
        button.Click += (_, _) => onClick();
        new ToolTip().SetToolTip(button, hint);
        return button;
    }
    private Control BuildChartArea()
    {
        var dashboard = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            Padding = new Padding(14),
            RowCount = 2,
            ColumnCount = 1,
        };
        dashboard.RowStyles.Add(new RowStyle(SizeType.Absolute, 88));
        dashboard.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var metrics = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            ColumnCount = 4,
            RowCount = 1,
        };
        metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
        metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
        metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
        metrics.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
        metrics.Controls.Add(MetricCard("ATIVO", _symbolCombo.Text, "+ candles live"), 0, 0);
        metrics.Controls.Add(MetricCard("TIMEFRAME", _timeframeCombo.Text, "MT5 sincronizado"), 1, 0);
        metrics.Controls.Add(MetricCard("ORDENS", "1 por ativo", "limite operacional"), 2, 0);
        metrics.Controls.Add(MetricCard("ROBO", "READY", "demo conectado"), 3, 0);

        var chartShell = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(10),
        };
        chartShell.Paint += (_, e) => DrawBorder(e.Graphics, chartShell.ClientRectangle);
        _chart.Dock = DockStyle.Fill;
        chartShell.Controls.Add(_chart);

        dashboard.Controls.Add(metrics, 0, 0);
        dashboard.Controls.Add(chartShell, 0, 1);
        return dashboard;
    }

    private static Control MetricCard(string label, string value, string detail)
    {
        var card = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(12, 4, 12, 4),
            Margin = new Padding(0, 0, 10, 10),
            RowCount = 3,
            ColumnCount = 1,
        };
        card.RowStyles.Add(new RowStyle(SizeType.Absolute, 18));
        card.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        card.RowStyles.Add(new RowStyle(SizeType.Absolute, 18));
        card.Paint += (_, e) => DrawBorder(e.Graphics, card.ClientRectangle);
        card.Controls.Add(new Label
        {
            Text = label,
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 7.75f, FontStyle.Bold),
        }, 0, 0);
        card.Controls.Add(new Label
        {
            Text = value,
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI Semibold", 15.5f, FontStyle.Bold),
            TextAlign = ContentAlignment.MiddleLeft,
        }, 0, 1);
        card.Controls.Add(new Label
        {
            Text = detail,
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Positive,
            Font = new Font("Segoe UI", 8f),
        }, 0, 2);
        return card;
    }
    private Control BuildNavigatorPanel()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            Padding = new Padding(14, 14, 8, 14),
            RowCount = 5,
            ColumnCount = 1,
        };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 130));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 128));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 104));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 30));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        panel.Controls.Add(BuildMarketOverviewCard(), 0, 0);
        panel.Controls.Add(BuildActiveBotsCard(), 0, 1);
        panel.Controls.Add(BuildBotControlsCard(), 0, 2);
        panel.Controls.Add(new Label
        {
            Text = "ATIVOS MONITORADOS",
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8f, FontStyle.Bold),
            TextAlign = ContentAlignment.BottomLeft,
            Padding = new Padding(2, 0, 0, 4),
        }, 0, 3);

        var treeHost = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(8),
        };
        treeHost.Paint += (_, e) => DrawBorder(e.Graphics, treeHost.ClientRectangle);
        _navigator.BackColor = TerminalTheme.Panel;
        _navigator.ForeColor = TerminalTheme.Text;
        _navigator.Font = new Font("Segoe UI", 8.75f, FontStyle.Regular);
        _navigator.ItemHeight = 24;
        _navigator.HideSelection = false;
        _navigator.ShowLines = false;
        _navigator.ShowRootLines = false;
        _navigator.BorderStyle = BorderStyle.None;
        _navigator.NodeMouseClick += (_, args) => HandleNavigatorNode(args.Node);
        _navigator.NodeMouseDoubleClick += (_, args) =>
        {
            if (args.Node?.Tag is string symbol)
            {
                _symbolCombo.Text = symbol;
            }
            else if (args.Node?.Text == "EMA 9/21/50")
            {
                _chart.MovingAverageMode = MovingAverageMode.Exponential;
            }
            else if (args.Node?.Text == "MA 9/21/50")
            {
                _chart.MovingAverageMode = MovingAverageMode.Simple;
            }
        };
        treeHost.Controls.Add(_navigator);
        panel.Controls.Add(treeHost, 0, 4);
        return panel;
    }

    private Control BuildMarketOverviewCard()
    {
        var card = DashboardCard("LIVE MARKET OVERVIEW");
        card.Controls.Add(new Label
        {
            Text = "AUDUSD  M15",
            Dock = DockStyle.Top,
            Height = 28,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI Semibold", 14f, FontStyle.Bold),
        });
        card.Controls.Add(new Label
        {
            Text = "Candles em tempo real via MT5 + historico CSV",
            Dock = DockStyle.Top,
            Height = 24,
            ForeColor = TerminalTheme.Positive,
            Font = new Font("Segoe UI", 8.5f),
        });
        card.Controls.Add(new Label
        {
            Text = "Spread, drawdown e contexto operacional ficam concentrados aqui para leitura rapida.",
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8.25f),
        });
        return card;
    }

    private Control BuildActiveBotsCard()
    {
        var card = DashboardCard("ACTIVE BOTS");
        card.Controls.Add(BotLine("Fusion Core", "1 ordem por ativo", TerminalTheme.Positive));
        card.Controls.Add(BotLine("MT5 Bridge", "candles live", TerminalTheme.Primary));
        return card;
    }

    private Control BuildBotControlsCard()
    {
        var card = DashboardCard("BOT CONTROLS");
        var row = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 34,
            BackColor = TerminalTheme.Panel,
            WrapContents = false,
        };
        row.Controls.Add(_robotButton);
        row.Controls.Add(HeaderButton("Leitura", 82, () => SelectReadingTabInWorkspace("Probabilidades")));
        card.Controls.Add(row);
        card.Controls.Add(new Label
        {
            Text = "Use este bloco para iniciar/parar o robo e abrir os modulos de decisao.",
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8.25f),
        });
        return card;
    }

    private static FlowLayoutPanel DashboardCard(string title)
    {
        var card = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(12, 10, 12, 10),
            Margin = new Padding(0, 0, 0, 10),
        };
        card.Paint += (_, e) => DrawBorder(e.Graphics, card.ClientRectangle);
        card.Controls.Add(new Label
        {
            Text = title,
            Width = 260,
            Height = 22,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8f, FontStyle.Bold),
        });
        return card;
    }

    private static Control BotLine(string name, string detail, Color color)
    {
        var panel = new TableLayoutPanel
        {
            Width = 260,
            Height = 40,
            BackColor = TerminalTheme.PanelSoft,
            Margin = new Padding(0, 2, 0, 3),
            ColumnCount = 2,
            RowCount = 2,
        };
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 62));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 38));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 55));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 45));
        panel.Controls.Add(new Label { Text = name, Dock = DockStyle.Fill, ForeColor = TerminalTheme.Text, Font = new Font("Segoe UI", 8.5f, FontStyle.Bold), TextAlign = ContentAlignment.BottomLeft, Padding = new Padding(8, 0, 0, 0) }, 0, 0);
        panel.Controls.Add(new Label { Text = "ACTIVE", Dock = DockStyle.Fill, ForeColor = color, Font = new Font("Segoe UI", 7.5f, FontStyle.Bold), TextAlign = ContentAlignment.BottomRight, Padding = new Padding(0, 0, 8, 0) }, 1, 0);
        panel.Controls.Add(new Label { Text = detail, Dock = DockStyle.Fill, ForeColor = TerminalTheme.Muted, Font = new Font("Segoe UI", 7.75f), TextAlign = ContentAlignment.TopLeft, Padding = new Padding(8, 0, 0, 0) }, 0, 1);
        panel.SetColumnSpan(panel.GetControlFromPosition(0, 1)!, 2);
        return panel;
    }
    private void EnsureReadingTabs()
    {
        if (_rightTabs.TabPages.Count > 0)
        {
            return;
        }

        _rightTabs.Appearance = TabAppearance.FlatButtons;
        _rightTabs.BackColor = TerminalTheme.Panel;
        ApplyDarkTabs(_rightTabs);
        AddTab("Probabilidades", _probabilityPanel);
        AddTab("Leitura Tecnica", _technicalPanel);
        AddTab("Matriz Operacional", _operationalMatrixPanel);
        AddTab("Sinais", _signalsPanel);
        AddTab("Ordens", _ordersPanel);
        AddTab("Camadas", _layersPanel);
        AddTab("Eventos", _eventsPanel);
    }

    private Control BuildBottomPanel()
    {
        var panel = CompactDockWithClose(out var content, () => SetBottomDockVisible(false));
        _bottomTabs.Appearance = TabAppearance.FlatButtons;
        _bottomTabs.BackColor = TerminalTheme.Panel;
        ApplyDarkTabs(_bottomTabs);
        _simulationPanel.SettingsChanged += (_, settings) => _chart.UpdateSimulationSettings(settings);
        _simulationPanel.StartRequested += (_, _) =>
        {
            _chart.StartSimulationPlayback();
            _simulationTimer.Interval = _chart.SimulationTimerInterval();
            _simulationTimer.Start();
        };
        _simulationPanel.PauseRequested += (_, _) =>
        {
            _chart.PauseSimulationPlayback();
            _simulationTimer.Stop();
        };
        _simulationPanel.StopRequested += (_, _) =>
        {
            _chart.StopSimulationPlayback();
            _simulationTimer.Stop();
        };
        AddBottomTab("Simulacao", _simulationPanel);
        AddBottomTab("Resultado", "Resultado da simulacao", "Pips, USD, BRL, lote, motivo de saida e estatisticas.");
        AddBottomTab("Backtest", _backtestPanel);
        content.Controls.Add(_bottomTabs);
        return panel;
    }

    private static Control CompactDockWithClose(out Panel contentHost, Action onClose)
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(6, 4, 6, 6),
            RowCount = 1,
            ColumnCount = 2,
        };
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 28));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        contentHost = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
        };
        var close = new Button
        {
            Text = "X",
            Dock = DockStyle.Top,
            Width = 24,
            Height = 24,
            FlatStyle = FlatStyle.Flat,
            BackColor = TerminalTheme.PanelAlt,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8f, FontStyle.Bold),
        };
        close.FlatAppearance.BorderColor = TerminalTheme.Border;
        close.Click += (_, _) => onClose();

        panel.Controls.Add(contentHost, 0, 0);
        panel.Controls.Add(close, 1, 0);
        return panel;
    }

    private void AddTab(string tabName, string title, string description)
    {
        var page = new TabPage(tabName)
        {
            BackColor = TerminalTheme.Panel,
            ForeColor = TerminalTheme.Text,
        };
        page.Controls.Add(new ModulePlaceholder(title, description));
        _rightTabs.TabPages.Add(page);
    }

    private void AddTab(string tabName, Control content)
    {
        var page = new TabPage(tabName)
        {
            BackColor = TerminalTheme.Panel,
            ForeColor = TerminalTheme.Text,
        };
        page.Controls.Add(content);
        _rightTabs.TabPages.Add(page);
    }

    private void AddBottomTab(string tabName, string title, string description)
    {
        var page = new TabPage(tabName)
        {
            BackColor = TerminalTheme.Panel,
            ForeColor = TerminalTheme.Text,
        };
        page.Controls.Add(new ModulePlaceholder(title, description));
        _bottomTabs.TabPages.Add(page);
    }

    private void AddBottomTab(string tabName, Control content)
    {
        var page = new TabPage(tabName)
        {
            BackColor = TerminalTheme.Panel,
            ForeColor = TerminalTheme.Text,
        };
        page.Controls.Add(content);
        _bottomTabs.TabPages.Add(page);
    }

    private StatusStrip BuildStatusBar()
    {
        var status = new StatusStrip
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.PanelAlt,
            ForeColor = TerminalTheme.Muted,
            SizingGrip = false,
        };
        status.Items.Add(_statusLeft);
        status.Items.Add(_statusRight);
        return status;
    }

    private static Control PanelWithHeader(string title, string subtitle, out Panel contentHost, Action? onClose = null)
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(10),
            RowCount = 3,
            ColumnCount = 2,
        };
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 30));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 28));
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        contentHost = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(0, 8, 0, 0),
        };
        var titleLabel = new Label
        {
            Text = title,
            Dock = DockStyle.Top,
            Height = 28,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI", 11f, FontStyle.Bold),
        };
        var subtitleLabel = new Label
        {
            Text = subtitle,
            Dock = DockStyle.Top,
            Height = 24,
            ForeColor = TerminalTheme.Muted,
        };
        var close = new Button
        {
            Text = "X",
            Dock = DockStyle.Fill,
            Width = 26,
            Height = 24,
            FlatStyle = FlatStyle.Flat,
            BackColor = TerminalTheme.PanelAlt,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8f, FontStyle.Bold),
        };
        close.FlatAppearance.BorderColor = TerminalTheme.Border;
        close.Click += (_, _) => onClose?.Invoke();
        panel.Controls.Add(titleLabel, 0, 0);
        if (onClose is not null)
        {
            panel.Controls.Add(close, 1, 0);
        }
        panel.Controls.Add(subtitleLabel, 0, 1);
        panel.SetColumnSpan(subtitleLabel, 2);
        panel.Controls.Add(contentHost, 0, 2);
        panel.SetColumnSpan(contentHost, 2);
        return panel;
    }

    private static void ApplyDarkTabs(TabControl tabs)
    {
        tabs.DrawMode = TabDrawMode.OwnerDrawFixed;
        tabs.ItemSize = new Size(112, 30);
        tabs.SizeMode = TabSizeMode.Fixed;
        tabs.Padding = new Point(8, 4);
        tabs.DrawItem += (_, e) =>
        {
            var selected = e.Index == tabs.SelectedIndex;
            var page = tabs.TabPages[e.Index];
            using var back = new SolidBrush(selected ? TerminalTheme.PanelSoft : TerminalTheme.Background);
            using var fore = new SolidBrush(selected ? TerminalTheme.Text : TerminalTheme.Muted);
            e.Graphics.FillRectangle(back, e.Bounds);
            using var pen = new Pen(selected ? TerminalTheme.Primary : TerminalTheme.Border);
            e.Graphics.DrawRectangle(pen, e.Bounds.X, e.Bounds.Y, e.Bounds.Width - 1, e.Bounds.Height - 1);
            TextRenderer.DrawText(
                e.Graphics,
                page.Text,
                new Font("Segoe UI", 8.5f, FontStyle.Bold),
                e.Bounds,
                selected ? TerminalTheme.Text : TerminalTheme.Muted,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis
            );
        };
    }
    private static Label Label(string text) => new()
    {
        Text = text,
        AutoSize = true,
        ForeColor = TerminalTheme.Muted,
        Font = new Font("Segoe UI", 8.25f, FontStyle.Bold),
        Padding = new Padding(6, 7, 2, 0),
    };

    private static Label StatusCaption(string text) => new()
    {
        Text = text,
        Dock = DockStyle.Fill,
        ForeColor = TerminalTheme.Muted,
        Font = new Font("Segoe UI", 7.25f, FontStyle.Bold),
        TextAlign = ContentAlignment.BottomLeft,
    };

    private static Button Button(string text, int width)
    {
        var button = new Button
        {
            Text = text,
            Width = width,
            Height = 28,
            FlatStyle = FlatStyle.Flat,
            BackColor = TerminalTheme.PanelSoft,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI", 8.25f, FontStyle.Bold),
            Margin = new Padding(3, 1, 3, 1),
        };
        button.FlatAppearance.BorderColor = TerminalTheme.Border;
        button.FlatAppearance.MouseOverBackColor = TerminalTheme.PrimarySoft;
        return button;
    }

    private static Button HeaderButton(string text, int width, Action onClick)
    {
        var button = Button(text, width);
        button.Height = 30;
        button.BackColor = TerminalTheme.Background;
        button.Click += (_, _) => onClick();
        return button;
    }

    private static Control ToolGroup(string title, params Control[] controls)
    {
        var group = new FlowLayoutPanel
        {
            AutoSize = true,
            Height = 32,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(8, 1, 8, 1),
            Margin = new Padding(0, 0, 8, 0),
            WrapContents = false,
        };
        group.Paint += (_, e) => DrawBorder(e.Graphics, group.ClientRectangle);
        group.Controls.Add(new Label
        {
            Text = title,
            AutoSize = true,
            ForeColor = TerminalTheme.Primary,
            Font = new Font("Segoe UI", 8.25f, FontStyle.Bold),
            Padding = new Padding(0, 7, 8, 0),
            Margin = new Padding(0),
        });
        foreach (var control in controls)
        {
            control.Margin = new Padding(2, 1, 2, 1);
            group.Controls.Add(control);
        }
        return group;
    }

    private static void DrawBorder(Graphics graphics, Rectangle bounds)
    {
        if (bounds.Width <= 1 || bounds.Height <= 1)
        {
            return;
        }
        using var pen = new Pen(TerminalTheme.Border);
        graphics.DrawRectangle(pen, bounds.X, bounds.Y, bounds.Width - 1, bounds.Height - 1);
    }
    private void ConfigureNavigator()
    {
        _navigator.Nodes.Clear();
        _navigator.Nodes.Add(new TreeNode("Visao principal")
        {
            Nodes =
            {
                new TreeNode("Grafico de mercado") { Tag = "view:chart" },
                new TreeNode("Probabilidades") { Tag = "reading:Probabilidades" },
                new TreeNode("Leitura tecnica") { Tag = "reading:Leitura Tecnica" },
                new TreeNode("Matriz operacional") { Tag = "reading:Matriz Operacional" },
            },
        });
        _navigator.Nodes.Add(new TreeNode("Monitoramento")
        {
            Nodes =
            {
                new TreeNode("Sinais e alertas") { Tag = "reading:Sinais" },
                new TreeNode("Ordens e posicoes") { Tag = "reading:Ordens" },
                new TreeNode("Camadas de decisao") { Tag = "reading:Camadas" },
                new TreeNode("Eventos do sistema") { Tag = "reading:Eventos" },
            },
        });
        _navigator.Nodes.Add(new TreeNode("Ativos monitorados") { Name = "Ativos" });
        _navigator.Nodes.Add(new TreeNode("Ferramentas do grafico")
        {
            Nodes =
            {
                new TreeNode("EMA 9/21/50"),
                new TreeNode("MA 9/21/50"),
                new TreeNode("Remover indicadores"),
            },
        });
        _navigator.Nodes.Add(new TreeNode("Pesquisa e teste")
        {
            Nodes =
            {
                new TreeNode("Simulacao") { Tag = "bottom:Simulacao" },
                new TreeNode("Backtest") { Tag = "bottom:Backtest" },
                new TreeNode("Resultado") { Tag = "bottom:Resultado" },
            },
        });
        _navigator.ExpandAll();
    }

    private void HandleNavigatorNode(TreeNode? node)
    {
        if (node?.Tag is not string tag)
        {
            return;
        }

        if (tag == "view:chart")
        {
            ShowChartInWorkspace();
            return;
        }

        if (tag.StartsWith("reading:", StringComparison.OrdinalIgnoreCase))
        {
            SelectReadingTabInWorkspace(tag["reading:".Length..]);
            return;
        }

        if (tag.StartsWith("bottom:", StringComparison.OrdinalIgnoreCase))
        {
            SelectBottomTab(tag["bottom:".Length..]);
        }
    }

    private void SetLeftDockVisible(bool visible)
    {
        if (_leftDock is not null)
        {
            _leftDock.Visible = visible;
        }
        if (_leftDockColumn is not null)
        {
            _leftDockColumn.Width = visible ? 320 : 0;
        }
    }

    private void SetRightDockVisible(bool visible)
    {
        if (visible)
        {
            ShowReadingWindow();
            return;
        }

        _readingWindow?.Hide();
    }

    private void SetBottomDockVisible(bool visible)
    {
        if (_bottomDock is not null)
        {
            _bottomDock.Visible = visible;
        }
        if (_bottomDockRow is not null)
        {
            _bottomDockRow.Height = visible ? 260 : 0;
        }
    }

    private void SelectRightTab(string tabName)
    {
        ShowReadingWindow();
        foreach (TabPage page in _rightTabs.TabPages)
        {
            if (page.Text == tabName)
            {
                _rightTabs.SelectedTab = page;
                _readingWindow?.Activate();
                return;
            }
        }
    }

    private void SelectReadingTabInWorkspace(string tabName)
    {
        EnsureReadingTabs();
        _readingWindow?.Hide();

        if (_rightTabs.Parent != _centerHost)
        {
            _rightTabs.Parent?.Controls.Remove(_rightTabs);
            _centerHost.Controls.Clear();
            _rightTabs.Dock = DockStyle.Fill;
            _centerHost.Controls.Add(_rightTabs);
        }

        foreach (TabPage page in _rightTabs.TabPages)
        {
            if (page.Text == tabName)
            {
                _rightTabs.SelectedTab = page;
                break;
            }
        }

        _statusLeft.Text = $"Leitura aberta no painel principal: {tabName}";
    }

    private void ShowChartInWorkspace()
    {
        if (_chartArea is null)
        {
            return;
        }

        if (_chartArea.Parent != _centerHost)
        {
            _chartArea.Parent?.Controls.Remove(_chartArea);
            _centerHost.Controls.Clear();
            _centerHost.Controls.Add(_chartArea);
        }

        _chartArea.Dock = DockStyle.Fill;
        _chart.Focus();
        _statusLeft.Text = "Grafico ativo";
    }

    private void ShowReadingWindow()
    {
        EnsureReadingTabs();

        if (_readingWindow is null || _readingWindow.IsDisposed)
        {
            _readingWindow = new Form
            {
                Text = "Fusion - Leitura",
                Width = 520,
                Height = 760,
                MinimumSize = new Size(420, 520),
                StartPosition = FormStartPosition.Manual,
                BackColor = TerminalTheme.Panel,
                ForeColor = TerminalTheme.Text,
                Font = Font,
            };
            _readingWindow.FormClosing += (_, args) =>
            {
                args.Cancel = true;
                _readingWindow.Hide();
            };
        }

        if (_rightTabs.Parent != _readingWindow)
        {
            if (_rightTabs.Parent == _centerHost && _chartArea is not null)
            {
                _centerHost.Controls.Remove(_rightTabs);
                _centerHost.Controls.Add(_chartArea);
                _chartArea.Dock = DockStyle.Fill;
            }
            _rightTabs.Parent?.Controls.Remove(_rightTabs);
            _rightTabs.Dock = DockStyle.Fill;
            _readingWindow.Controls.Add(_rightTabs);
        }

        if (!_readingWindow.Visible)
        {
            var x = Math.Min(Bounds.Right - 20, Screen.FromControl(this).WorkingArea.Right - _readingWindow.Width - 20);
            var y = Math.Max(Screen.FromControl(this).WorkingArea.Top + 40, Bounds.Top + 80);
            _readingWindow.Location = new Point(Math.Max(20, x), y);
            _readingWindow.Show(this);
        }
        else
        {
            _readingWindow.Activate();
        }
    }

    private void SelectBottomTab(string tabName)
    {
        SetBottomDockVisible(true);
        foreach (TabPage page in _bottomTabs.TabPages)
        {
            if (page.Text == tabName)
            {
                _bottomTabs.SelectedTab = page;
                return;
            }
        }
    }

    private void OpenSimulationFromSignal(SelectedSignal selectedSignal)
    {
        SetBottomDockVisible(true);
        SelectBottomTab("Simulacao");
        var signal = selectedSignal.Signal;
        var settings = _simulationPanel.CurrentSettings();
        var sideSettings = settings with { Side = signal.Side };
        _chart.CreateSimulatedOrderFromSignal(selectedSignal, sideSettings);
        _statusLeft.Text = $"Sinal selecionado: {signal.Symbol} {signal.Timeframe} {signal.Side} {signal.Strategy} | {selectedSignal.Candle.Time:yyyy-MM-dd HH:mm}";
    }

    private sealed record MarketDataPayload(
        string Symbol,
        string Timeframe,
        string[] Symbols,
        IReadOnlyList<Models.Candle> Candles,
        SnapshotResult Snapshot,
        bool ChartChanged
    );

    private void RequestMarketDataLoad(bool refreshSymbols)
    {
        _pendingMarketRefreshSymbols = _pendingMarketRefreshSymbols || refreshSymbols;
        _marketLoadDebounceTimer.Stop();
        _marketLoadDebounceTimer.Start();
    }

    private async void QueueMarketDataLoad(bool refreshSymbols)
    {
        if (IsDisposed)
        {
            return;
        }
        if (_isLoadingMarketData)
        {
            _pendingMarketRefreshSymbols = _pendingMarketRefreshSymbols || refreshSymbols;
            _marketLoadDebounceTimer.Stop();
            _marketLoadDebounceTimer.Start();
            return;
        }

        var requestedSymbol = _symbolCombo.Text.Trim();
        var requestedTimeframe = string.IsNullOrWhiteSpace(_timeframeCombo.Text) ? "M15" : _timeframeCombo.Text.Trim().ToUpperInvariant();
        _isLoadingMarketData = true;
        _statusLeft.Text = $"Carregando {requestedSymbol} {requestedTimeframe}...";

        try
        {
            var payload = await Task.Run(() => BuildMarketDataPayload(requestedSymbol, requestedTimeframe, refreshSymbols));
            if (IsDisposed)
            {
                return;
            }
            ApplyMarketDataPayload(payload, refreshSymbols);
        }
        catch (Exception ex)
        {
            _statusLeft.Text = "Falha ao carregar dados de mercado.";
            _statusRight.Text = ex.Message;
            Program.StartupTrace("QueueMarketDataLoad failed: " + ex);
        }
        finally
        {
            _isLoadingMarketData = false;
        }
    }

    private MarketDataPayload BuildMarketDataPayload(string requestedSymbol, string timeframe, bool refreshSymbols)
    {
        var symbols = refreshSymbols
            ? _loader.Symbols(timeframe)
                .Concat(_snapshotLoader.Symbols(timeframe))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(item => item)
                .ToArray()
            : Array.Empty<string>();

        var symbol = requestedSymbol;
        if (string.IsNullOrWhiteSpace(symbol) || (refreshSymbols && symbols.Length > 0 && !symbols.Contains(symbol, StringComparer.OrdinalIgnoreCase)))
        {
            symbol = symbols.FirstOrDefault(item => string.Equals(item, "XAUUSD", StringComparison.OrdinalIgnoreCase))
                ?? symbols.FirstOrDefault(item => string.Equals(item, "EURUSD", StringComparison.OrdinalIgnoreCase))
                ?? symbols.FirstOrDefault()
                ?? requestedSymbol;
        }

        if (string.IsNullOrWhiteSpace(symbol))
        {
            return new MarketDataPayload("", timeframe, symbols, Array.Empty<Models.Candle>(), SnapshotResult.Empty, false);
        }

        var chartChanged = !symbol.Equals(_lastChartSymbol, StringComparison.OrdinalIgnoreCase)
            || !timeframe.Equals(_lastChartTimeframe, StringComparison.OrdinalIgnoreCase);
        var csvCandles = _loader.Load(symbol, timeframe, 900);
        var snapshot = _snapshotLoader.Load(symbol, timeframe);
        var candles = MergeCandles(csvCandles, snapshot.Candles, 900);
        return new MarketDataPayload(symbol, timeframe, symbols, candles, snapshot, chartChanged);
    }

    private void ApplyMarketDataPayload(MarketDataPayload payload, bool refreshSymbols)
    {
        _suppressMarketTextEvents = true;
        try
        {
            if (!string.IsNullOrWhiteSpace(payload.Symbol) && !payload.Symbol.Equals(_symbolCombo.Text, StringComparison.OrdinalIgnoreCase))
            {
                _symbolCombo.Text = payload.Symbol;
            }
            if (!payload.Timeframe.Equals(_timeframeCombo.Text, StringComparison.OrdinalIgnoreCase))
            {
                _timeframeCombo.Text = payload.Timeframe;
            }
        }
        finally
        {
            _suppressMarketTextEvents = false;
        }

        if (refreshSymbols)
        {
            _navigator.BeginUpdate();
            try
            {
                var assetsNode = _navigator.Nodes["Ativos"];
                assetsNode?.Nodes.Clear();
                foreach (var symbol in payload.Symbols)
                {
                    assetsNode?.Nodes.Add(new TreeNode(symbol) { Tag = symbol });
                }
                assetsNode?.Expand();
            }
            finally
            {
                _navigator.EndUpdate();
            }
        }

        _lastChartSymbol = payload.Symbol;
        _lastChartTimeframe = payload.Timeframe;
        _chart.SetCandles(payload.Candles);
        if (payload.ChartChanged)
        {
            _chart.ResetPriceScale();
        }
        if (!string.IsNullOrWhiteSpace(payload.Symbol))
        {
            _backtestPanel.UpdateContext(payload.Symbol, payload.Timeframe);
        }
        _connection.Text = payload.Snapshot.Candles.Count > 0
            ? $"CSV historico + MT5 live | broker {payload.Snapshot.BrokerSymbol} | {SnapshotAge(payload.Snapshot)}"
            : "CSV historico | aguardando snapshot MT5";
        _statusLeft.Text = string.IsNullOrWhiteSpace(payload.Symbol)
            ? "Nenhum ativo encontrado para o timeframe."
            : $"{payload.Symbol} {payload.Timeframe} | candles={payload.Candles.Count}";
        _statusRight.Text = payload.Candles.Count > 0
            ? $"Primeiro: {payload.Candles[0].Time:yyyy-MM-dd HH:mm} | Ultimo: {payload.Candles[^1].Time:yyyy-MM-dd HH:mm}"
            : "Sem dados";
    }
    private void QueueAnalysisModulesLoad(string symbol, string timeframe)
    {
        var symbolChanged = !symbol.Equals(_lastModuleSymbol, StringComparison.OrdinalIgnoreCase)
            || !timeframe.Equals(_lastModuleTimeframe, StringComparison.OrdinalIgnoreCase);
        var elapsed = DateTime.Now - _lastModuleRefresh;
        if (!symbolChanged && elapsed < TimeSpan.FromSeconds(30))
        {
            return;
        }

        _lastModuleSymbol = symbol;
        _lastModuleTimeframe = timeframe;
        _lastModuleRefresh = DateTime.Now;

        _moduleLoadTimer.Stop();
        _moduleLoadQueue.Clear();
        _moduleLoadQueue.Enqueue(() =>
        {
            var signals = _signalLoader.Load(symbol, timeframe);
            _chart.SetSignals(signals);
            _statusLeft.Text = $"{symbol} {timeframe} | sinais carregados";
        });
        _moduleLoadQueue.Enqueue(() =>
        {
            _probabilityPanel.UpdateSymbol(symbol);
            _statusLeft.Text = $"{symbol} {timeframe} | probabilidades carregadas";
        });
        _moduleLoadQueue.Enqueue(() =>
        {
            _technicalPanel.UpdateSymbol(symbol, timeframe);
            _statusLeft.Text = $"{symbol} {timeframe} | leitura tecnica carregada";
        });
        _moduleLoadQueue.Enqueue(() =>
        {
            _operationalMatrixPanel.Reload();
            _statusLeft.Text = $"{symbol} {timeframe} | matriz operacional carregada";
        });
        _moduleLoadQueue.Enqueue(() =>
        {
            _signalsPanel.UpdateSymbol(symbol);
            _statusLeft.Text = $"{symbol} {timeframe} | painel de sinais carregado";
        });
        _moduleLoadQueue.Enqueue(() =>
        {
            _ordersPanel.UpdateSymbol(symbol);
            _statusLeft.Text = $"{symbol} {timeframe} | ordens e posicoes carregadas";
        });
        _moduleLoadQueue.Enqueue(() =>
        {
            _layersPanel.UpdateSymbol(symbol);
            _eventsPanel.UpdateSymbol(symbol);
            _statusLeft.Text = $"{symbol} {timeframe} | modulos carregados";
        });
        _moduleLoadTimer.Start();
    }

    private void DrainModuleLoadQueue()
    {
        if (_moduleLoadQueue.Count == 0)
        {
            _moduleLoadTimer.Stop();
            return;
        }

        try
        {
            var action = _moduleLoadQueue.Dequeue();
            action();
        }
        catch (Exception ex)
        {
            Program.StartupTrace("DrainModuleLoadQueue failed: " + ex);
            _statusLeft.Text = "Falha ao carregar modulo.";
            _statusRight.Text = ex.Message;
        }

        if (_moduleLoadQueue.Count == 0)
        {
            _moduleLoadTimer.Stop();
        }
    }
    private void LoadSymbols()
    {
        var current = _symbolCombo.Text;
        var timeframe = string.IsNullOrWhiteSpace(_timeframeCombo.Text) ? "M15" : _timeframeCombo.Text.Trim();
        var symbols = _loader.Symbols(timeframe)
            .Concat(_snapshotLoader.Symbols(timeframe))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(item => item)
            .ToArray();

        
        _navigator.BeginUpdate();
        
        var assetsNode = _navigator.Nodes["Ativos"];
        assetsNode?.Nodes.Clear();
        foreach (var symbol in symbols)
        {
            assetsNode?.Nodes.Add(new TreeNode(symbol) { Tag = symbol });
        }
        assetsNode?.Expand();

        var preferred = symbols.FirstOrDefault(item => string.Equals(item, current, StringComparison.OrdinalIgnoreCase))
            ?? symbols.FirstOrDefault(item => string.Equals(item, "XAUUSD", StringComparison.OrdinalIgnoreCase))
            ?? symbols.FirstOrDefault(item => string.Equals(item, "EURUSD", StringComparison.OrdinalIgnoreCase))
            ?? symbols.FirstOrDefault();

        if (preferred is not null)
        {
            _symbolCombo.Text = preferred;
        }
        
        _navigator.EndUpdate();
    }

    private void LoadCandles()
    {
        var symbol = _symbolCombo.Text;
        var timeframe = string.IsNullOrWhiteSpace(_timeframeCombo.Text) ? "M15" : _timeframeCombo.Text.Trim();
        if (string.IsNullOrWhiteSpace(symbol))
        {
            return;
        }

        var chartChanged = !symbol.Equals(_lastChartSymbol, StringComparison.OrdinalIgnoreCase)
            || !timeframe.Equals(_lastChartTimeframe, StringComparison.OrdinalIgnoreCase);
        _lastChartSymbol = symbol;
        _lastChartTimeframe = timeframe;

        var csvCandles = _loader.Load(symbol, timeframe, 900);
        var snapshot = _snapshotLoader.Load(symbol, timeframe);
        var candles = MergeCandles(csvCandles, snapshot.Candles, 900);
        _chart.SetCandles(candles);
        if (chartChanged)
        {
            _chart.ResetPriceScale();
        }
        _backtestPanel.UpdateContext(symbol, timeframe);
        QueueAnalysisModulesLoad(symbol, timeframe);
        _connection.Text = snapshot.Candles.Count > 0
            ? $"CSV historico + MT5 live | broker {snapshot.BrokerSymbol} | {SnapshotAge(snapshot)}"
            : "CSV historico | aguardando snapshot MT5";
        _statusLeft.Text = $"{symbol} {timeframe} | candles={candles.Count}";
        _statusRight.Text = candles.Count > 0
            ? $"Primeiro: {candles[0].Time:yyyy-MM-dd HH:mm} | Ultimo: {candles[^1].Time:yyyy-MM-dd HH:mm}"
            : "Sem dados";
    }


    private void ToggleFusionRobot()
    {
        if (_fusionProcess is not null && !_fusionProcess.HasExited)
        {
            StopFusionRobot();
            return;
        }

        StartFusionRobot();
    }

    private void StartFusionRobot()
    {
        var python = ResolvePythonPath();
        var runFusion = Path.Combine(_repoRoot, "run_fusion.py");
        if (!File.Exists(python) || !File.Exists(runFusion))
        {
            MessageBox.Show(
                $"Nao foi possivel iniciar o robo.\n\nPython: {python}\nrun_fusion.py: {runFusion}",
                "Fusion Robot",
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning
            );
            return;
        }

        Directory.CreateDirectory(Path.Combine(_repoRoot, "logs"));
        var logPath = Path.Combine(_repoRoot, "logs", "fusion_robot_from_terminal.log");
        var errPath = Path.Combine(_repoRoot, "logs", "fusion_robot_from_terminal.err.log");

        var info = new ProcessStartInfo
        {
            FileName = python,
            WorkingDirectory = _repoRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        info.ArgumentList.Add(runFusion);

        try
        {
            var process = new Process { StartInfo = info, EnableRaisingEvents = true };
            process.OutputDataReceived += (_, args) => AppendProcessLog(logPath, args.Data);
            process.ErrorDataReceived += (_, args) => AppendProcessLog(errPath, args.Data);
            process.Exited += (_, _) => BeginInvoke(() =>
            {
                _robotButton.Text = "Iniciar Robo";
                _robotButton.BackColor = TerminalTheme.PositiveSoft;
                _robotStatus.Text = $"Robo: encerrado ({process.ExitCode})";
                _statusLeft.Text = "Fusion robo encerrado.";
                _fusionProcess?.Dispose();
                _fusionProcess = null;
            });
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            _fusionProcess = process;
            _robotButton.Text = "Parar Robo";
            _robotButton.BackColor = TerminalTheme.Negative;
            _robotStatus.Text = $"Robo: rodando PID {process.Id}";
            _statusLeft.Text = "Fusion robo iniciado pelo terminal.";
        }
        catch (Exception ex)
        {
            Program.StartupTrace("StartFusionRobot failed: " + ex);
            MessageBox.Show(ex.ToString(), "Fusion Robot", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void StopFusionRobot()
    {
        try
        {
            if (_fusionProcess is not null && !_fusionProcess.HasExited)
            {
                _fusionProcess.Kill(entireProcessTree: true);
                _fusionProcess.WaitForExit(3000);
            }
        }
        catch (Exception ex)
        {
            Program.StartupTrace("StopFusionRobot failed: " + ex);
        }
        finally
        {
            _fusionProcess?.Dispose();
            _fusionProcess = null;
            _robotButton.Text = "Iniciar Robo";
            _robotButton.BackColor = TerminalTheme.PositiveSoft;
            _robotStatus.Text = "Robo: parado";
            _statusLeft.Text = "Fusion robo parado pelo terminal.";
        }
    }

    private void StartMt5BridgeIfAvailable()
    {
        if (_bridgeProcess is not null && !_bridgeProcess.HasExited)
        {
            return;
        }

        var python = ResolvePythonPath();
        var script = Path.Combine(_repoRoot, "tools", "export_mt5_candles_for_terminal.py");
        if (!File.Exists(python) || !File.Exists(script))
        {
            Program.StartupTrace("MT5 bridge not started: python/script missing");
            return;
        }

        var info = new ProcessStartInfo
        {
            FileName = python,
            WorkingDirectory = _repoRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        info.ArgumentList.Add(script);
        info.ArgumentList.Add("--timeframes");
        info.ArgumentList.Add("M5,M15,M30,H1,H4,D1");
        info.ArgumentList.Add("--bars");
        info.ArgumentList.Add("200");
        info.ArgumentList.Add("--interval");
        info.ArgumentList.Add("1");

        try
        {
            _bridgeProcess = Process.Start(info);
            if (_bridgeProcess is not null)
            {
                Program.StartupTrace("MT5 bridge started pid=" + _bridgeProcess.Id);
            }
        }
        catch (Exception ex)
        {
            Program.StartupTrace("StartMt5BridgeIfAvailable failed: " + ex);
        }
    }

    private string ResolvePythonPath()
    {
        var candidates = new[]
        {
            Path.Combine(_repoRoot, ".venv", "Scripts", "python.exe"),
            Path.Combine(_repoRoot, "venv", "Scripts", "python.exe"),
        };
        return candidates.FirstOrDefault(File.Exists) ?? candidates[0];
    }

    private static void AppendProcessLog(string path, string? line)
    {
        if (line is null)
        {
            return;
        }

        try
        {
            File.AppendAllText(path, line + Environment.NewLine);
        }
        catch
        {
        }
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        StopFusionRobot();
        try
        {
            if (_bridgeProcess is not null && !_bridgeProcess.HasExited)
            {
                _bridgeProcess.Kill(entireProcessTree: true);
            }
            _bridgeProcess?.Dispose();
        }
        catch (Exception ex)
        {
            Program.StartupTrace("Stop bridge failed: " + ex);
        }
        base.OnFormClosing(e);
    }

    private static string SnapshotAge(SnapshotResult snapshot)
    {
        if (!DateTime.TryParse(snapshot.GeneratedAt, out var generatedAt))
        {
            return "snapshot ativo";
        }

        var age = DateTime.Now - generatedAt;
        if (age.TotalSeconds < 0)
        {
            return "snapshot agora";
        }
        return age.TotalSeconds < 60
            ? $"snapshot {Math.Round(age.TotalSeconds)}s"
            : $"snapshot {Math.Round(age.TotalMinutes)}min";
    }

    private void RefreshAnalysisModules(string symbol, string timeframe)
    {
        var symbolChanged = !symbol.Equals(_lastModuleSymbol, StringComparison.OrdinalIgnoreCase)
            || !timeframe.Equals(_lastModuleTimeframe, StringComparison.OrdinalIgnoreCase);
        var elapsed = DateTime.Now - _lastModuleRefresh;
        if (!symbolChanged && elapsed < TimeSpan.FromSeconds(30))
        {
            return;
        }

        _lastModuleSymbol = symbol;
        _lastModuleTimeframe = timeframe;
        _lastModuleRefresh = DateTime.Now;

        var signals = _signalLoader.Load(symbol, timeframe);
        _chart.SetSignals(signals);
        _probabilityPanel.UpdateSymbol(symbol);
        _technicalPanel.UpdateSymbol(symbol, timeframe);
        _operationalMatrixPanel.Reload();
        _signalsPanel.UpdateSymbol(symbol);
        _ordersPanel.UpdateSymbol(symbol);
        _layersPanel.UpdateSymbol(symbol);
        _eventsPanel.UpdateSymbol(symbol);
    }

    private static IReadOnlyList<Models.Candle> MergeCandles(
        IReadOnlyList<Models.Candle> historical,
        IReadOnlyList<Models.Candle> live,
        int maxBars
    )
    {
        if (live.Count == 0)
        {
            return historical;
        }

        var byTime = new SortedDictionary<DateTime, Models.Candle>();
        foreach (var candle in historical)
        {
            byTime[candle.Time] = candle;
        }
        foreach (var candle in live)
        {
            byTime[candle.Time] = candle;
        }
        return CandleFilters.RemoveWeekendCandles(byTime.Values)
            .TakeLast(maxBars)
            .ToArray();
    }

    private static string FindRepoRoot(string start)
    {
        var dir = new DirectoryInfo(start);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine(dir.FullName, "run_fusion.py"))
                && Directory.Exists(Path.Combine(dir.FullName, "fusion")))
            {
                return dir.FullName;
            }
            dir = dir.Parent;
        }
        return Directory.GetCurrentDirectory();
    }
}



