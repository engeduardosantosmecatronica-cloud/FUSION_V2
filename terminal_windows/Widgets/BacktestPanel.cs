using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Data;
using FusionTerminalWindows.Models;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class BacktestPanel : UserControl
{
    private readonly BacktestTradeLoader _loader;
    private readonly ComboBox _strategy = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 190 };
    private readonly ComboBox _result = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 92 };
    private readonly DateTimePicker _from = new() { Width = 126, Format = DateTimePickerFormat.Short, ShowCheckBox = true };
    private readonly DateTimePicker _to = new() { Width = 126, Format = DateTimePickerFormat.Short, ShowCheckBox = true };
    private readonly CheckBox _onlyChart = new() { Text = "Somente ativo/TF atual", Checked = true, AutoSize = true, ForeColor = TerminalTheme.Text };
    private readonly Label _source = new();
    private readonly Label _summary = new();
    private readonly EquityCurveControl _equity = new() { Dock = DockStyle.Fill };
    private readonly DataGridView _tradesGrid = new();
    private IReadOnlyList<BacktestTrade> _allTrades = Array.Empty<BacktestTrade>();
    private string _symbol = "";
    private string _timeframe = "";

    public event EventHandler<IReadOnlyList<BacktestTrade>>? TradesApplied;

    public BacktestPanel(string root)
    {
        _loader = new BacktestTradeLoader(root);
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(8);
        BuildUi();
        ReloadSource();
    }

    public void UpdateContext(string symbol, string timeframe)
    {
        _symbol = symbol;
        _timeframe = timeframe;
        ApplyFilters(pushToChart: false);
    }

    private void BuildUi()
    {
        var shell = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 3,
            ColumnCount = 1,
            BackColor = TerminalTheme.Panel,
        };
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 40));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 92));
        shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var toolbar = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.PanelAlt,
            Padding = new Padding(8, 6, 8, 4),
            WrapContents = false,
        };
        var reload = Button("Recarregar", 88);
        var apply = Button("Aplicar no grafico", 126);
        var clear = Button("Limpar grafico", 96);
        reload.Click += (_, _) => ReloadSource();
        apply.Click += (_, _) => ApplyFilters(pushToChart: true);
        clear.Click += (_, _) => TradesApplied?.Invoke(this, Array.Empty<BacktestTrade>());
        _result.Items.AddRange(new object[] { "Todos", "Win", "Loss" });
        _result.SelectedIndex = 0;
        _strategy.SelectedIndexChanged += (_, _) => ApplyFilters(pushToChart: false);
        _result.SelectedIndexChanged += (_, _) => ApplyFilters(pushToChart: false);
        _from.ValueChanged += (_, _) => ApplyFilters(pushToChart: false);
        _to.ValueChanged += (_, _) => ApplyFilters(pushToChart: false);
        _onlyChart.CheckedChanged += (_, _) => ApplyFilters(pushToChart: false);

        toolbar.Controls.Add(Label("Estrategia"));
        toolbar.Controls.Add(_strategy);
        toolbar.Controls.Add(Label("Resultado"));
        toolbar.Controls.Add(_result);
        toolbar.Controls.Add(Label("Inicio"));
        toolbar.Controls.Add(_from);
        toolbar.Controls.Add(Label("Fim"));
        toolbar.Controls.Add(_to);
        toolbar.Controls.Add(_onlyChart);
        toolbar.Controls.Add(reload);
        toolbar.Controls.Add(apply);
        toolbar.Controls.Add(clear);

        var summaryPanel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 2,
            ColumnCount = 2,
            BackColor = TerminalTheme.Background,
            Padding = new Padding(8),
        };
        summaryPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 70));
        summaryPanel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30));
        summaryPanel.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        summaryPanel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        _source.Dock = DockStyle.Fill;
        _source.ForeColor = TerminalTheme.Muted;
        _summary.Dock = DockStyle.Fill;
        _summary.ForeColor = TerminalTheme.Text;
        _summary.Font = new Font("Segoe UI", 9.5f, FontStyle.Bold);
        summaryPanel.Controls.Add(_source, 0, 0);
        summaryPanel.Controls.Add(_summary, 0, 1);
        summaryPanel.Controls.Add(_equity, 1, 0);
        summaryPanel.SetRowSpan(_equity, 2);

        ConfigureGrid(_tradesGrid);
        shell.Controls.Add(toolbar, 0, 0);
        shell.Controls.Add(summaryPanel, 0, 1);
        shell.Controls.Add(_tradesGrid, 0, 2);
        Controls.Add(shell);
    }

    private void ReloadSource()
    {
        _allTrades = _loader.Load();
        var strategies = _allTrades.Select(item => item.Strategy)
            .Where(item => !string.IsNullOrWhiteSpace(item))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(item => item)
            .Cast<object>()
            .Prepend("Todas")
            .ToArray();
        _strategy.Items.Clear();
        _strategy.Items.AddRange(strategies);
        _strategy.SelectedIndex = 0;
        if (_allTrades.Count > 0)
        {
            _from.Value = _allTrades.Min(item => item.EntryTime).Date;
            _to.Value = _allTrades.Max(item => item.ExitTime).Date;
        }
        _source.Text = File.Exists(_loader.DefaultPath)
            ? $"{Path.GetFileName(_loader.DefaultPath)} | {_allTrades.Count} operacoes"
            : "Arquivo de trades de backtest nao encontrado.";
        ApplyFilters(pushToChart: false);
    }

    private void ApplyFilters(bool pushToChart)
    {
        IEnumerable<BacktestTrade> rows = _allTrades;
        if (_onlyChart.Checked && !string.IsNullOrWhiteSpace(_symbol))
        {
            rows = rows.Where(item =>
                item.Symbol.Equals(_symbol, StringComparison.OrdinalIgnoreCase)
                && item.Timeframe.Equals(_timeframe, StringComparison.OrdinalIgnoreCase));
        }

        if (_from.Checked)
        {
            rows = rows.Where(item => item.EntryTime.Date >= _from.Value.Date);
        }
        if (_to.Checked)
        {
            rows = rows.Where(item => item.EntryTime.Date <= _to.Value.Date);
        }

        var strategy = _strategy.SelectedItem?.ToString() ?? "Todas";
        if (!strategy.Equals("Todas", StringComparison.OrdinalIgnoreCase))
        {
            rows = rows.Where(item => item.Strategy.Equals(strategy, StringComparison.OrdinalIgnoreCase));
        }

        var result = _result.SelectedItem?.ToString() ?? "Todos";
        if (result.Equals("Win", StringComparison.OrdinalIgnoreCase))
        {
            rows = rows.Where(item => item.IsWin);
        }
        else if (result.Equals("Loss", StringComparison.OrdinalIgnoreCase))
        {
            rows = rows.Where(item => !item.IsWin);
        }

        var selected = rows.OrderBy(item => item.EntryTime).ToArray();
        var perf = BacktestTradeLoader.Performance(selected);
        _summary.Text =
            $"Trades {perf.Trades} | Win {perf.WinRate:0.0}% | Net {perf.NetPnl:0.##} pts | PF {perf.ProfitFactor:0.00} | " +
            $"Avg {perf.AveragePnl:0.##} | DD {perf.MaxDrawdown:0.##} | Best {perf.BestTrade:0.##} | Worst {perf.WorstTrade:0.##}";
        _equity.SetTrades(selected);
        RenderTrades(selected);
        if (pushToChart)
        {
            TradesApplied?.Invoke(this, selected);
        }
    }

    private void RenderTrades(IReadOnlyList<BacktestTrade> rows)
    {
        _tradesGrid.Columns.Clear();
        _tradesGrid.Rows.Clear();
        var columns = new[] { "Ativo", "TF", "Estrategia", "Entrada", "Saida", "Lado", "Entry", "Exit", "Pnl", "Resultado", "Motivo" };
        foreach (var column in columns)
        {
            _tradesGrid.Columns.Add(column, column);
        }

        foreach (var trade in rows.TakeLast(400).Reverse())
        {
            var index = _tradesGrid.Rows.Add(
                trade.Symbol,
                trade.Timeframe,
                trade.Strategy,
                trade.EntryTime.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture),
                trade.ExitTime.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture),
                trade.Side,
                trade.EntryPrice.ToString("0.#####", CultureInfo.InvariantCulture),
                trade.ExitPrice.ToString("0.#####", CultureInfo.InvariantCulture),
                trade.PnlPoints.ToString("0.##", CultureInfo.InvariantCulture),
                trade.IsWin ? "WIN" : "LOSS",
                trade.Reason
            );
            _tradesGrid.Rows[index].Cells[8].Style.ForeColor = trade.IsWin ? TerminalTheme.Positive : TerminalTheme.Negative;
            _tradesGrid.Rows[index].Cells[9].Style.ForeColor = trade.IsWin ? TerminalTheme.Positive : TerminalTheme.Negative;
        }
    }

    private static void ConfigureGrid(DataGridView grid)
    {
        grid.Dock = DockStyle.Fill;
        grid.BackgroundColor = TerminalTheme.Background;
        grid.BorderStyle = BorderStyle.None;
        grid.AllowUserToAddRows = false;
        grid.AllowUserToDeleteRows = false;
        grid.ReadOnly = true;
        grid.RowHeadersVisible = false;
        grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        grid.EnableHeadersVisualStyles = false;
        grid.GridColor = TerminalTheme.Border;
        grid.DefaultCellStyle.BackColor = TerminalTheme.Background;
        grid.DefaultCellStyle.ForeColor = TerminalTheme.Text;
        grid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(30, 58, 88);
        grid.ColumnHeadersDefaultCellStyle.BackColor = TerminalTheme.PanelAlt;
        grid.ColumnHeadersDefaultCellStyle.ForeColor = TerminalTheme.Text;
    }

    private static Label Label(string text) => new()
    {
        Text = text,
        AutoSize = true,
        ForeColor = TerminalTheme.Text,
        Padding = new Padding(8, 6, 4, 0),
    };

    private static Button Button(string text, int width) => new()
    {
        Text = text,
        Width = width,
        Height = 26,
        FlatStyle = FlatStyle.Flat,
        BackColor = TerminalTheme.Panel,
        ForeColor = TerminalTheme.Text,
    };

    private sealed class EquityCurveControl : Control
    {
        private IReadOnlyList<double> _equity = Array.Empty<double>();

        public void SetTrades(IReadOnlyList<BacktestTrade> trades)
        {
            var values = new List<double> { 0 };
            var sum = 0.0;
            foreach (var trade in trades.OrderBy(item => item.ExitTime))
            {
                sum += trade.PnlPoints;
                values.Add(sum);
            }
            _equity = values;
            Invalidate();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            var g = e.Graphics;
            g.Clear(TerminalTheme.Background);
            if (_equity.Count < 2)
            {
                return;
            }

            var min = Math.Min(0, _equity.Min());
            var max = Math.Max(0, _equity.Max());
            var span = Math.Max(1, max - min);
            var plot = new RectangleF(4, 4, Width - 8, Height - 8);
            using var grid = new Pen(TerminalTheme.Border);
            using var zero = new Pen(Color.FromArgb(90, 100, 116));
            using var line = new Pen(TerminalTheme.Primary, 2f);
            var zeroY = Y(0);
            g.DrawLine(zero, plot.Left, zeroY, plot.Right, zeroY);
            for (var i = 1; i < 4; i++)
            {
                var y = plot.Top + plot.Height * i / 4f;
                g.DrawLine(grid, plot.Left, y, plot.Right, y);
            }

            PointF? prev = null;
            for (var i = 0; i < _equity.Count; i++)
            {
                var x = plot.Left + plot.Width * i / Math.Max(1, _equity.Count - 1);
                var y = Y(_equity[i]);
                if (prev.HasValue)
                {
                    g.DrawLine(line, prev.Value, new PointF(x, y));
                }
                prev = new PointF(x, y);
            }

            float Y(double value) => plot.Bottom - (float)((value - min) / span * plot.Height);
        }
    }
}
