using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Data;
using FusionTerminalWindows.Models;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class TechnicalAnalysisPanel : UserControl
{
    private readonly CsvCandleLoader _csvLoader;
    private readonly TerminalSnapshotLoader _snapshotLoader;
    private readonly Label _source = new();
    private readonly TableLayoutPanel _rankingRows = new();
    private readonly GaugeControl _summaryGauge = new() { Dock = DockStyle.Fill };
    private readonly GaugeControl _oscillatorGauge = new() { Dock = DockStyle.Fill };
    private readonly GaugeControl _movingAverageGauge = new() { Dock = DockStyle.Fill };
    private readonly DataGridView _oscillatorGrid = new();
    private readonly DataGridView _movingAverageGrid = new();

    public TechnicalAnalysisPanel(string root)
    {
        _csvLoader = new CsvCandleLoader(root);
        _snapshotLoader = new TerminalSnapshotLoader(root);
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(10);
        BuildUi();
    }

    public void UpdateSymbol(string symbol, string timeframe)
    {
        var symbols = _csvLoader.Symbols(timeframe)
            .Concat(_snapshotLoader.Symbols(timeframe))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(item => item)
            .ToArray();

        var rows = symbols
            .Select(item => BuildAnalysis(item, timeframe, 360))
            .Where(item => item is not null)
            .Cast<TechnicalSnapshot>()
            .OrderByDescending(item => Math.Max(item.LongPercent, item.ShortPercent))
            .ThenBy(item => item.Symbol)
            .Take(28)
            .ToArray();

        var selected = BuildAnalysis(symbol, timeframe, 520);
        _source.Text = selected is null
            ? $"{symbol} {timeframe} | sem candles suficientes"
            : $"{symbol} {timeframe} | Long {selected.LongPercent:0}% / Short {selected.ShortPercent:0}% | {selected.Signal}";

        RenderRanking(rows);
        RenderSelected(selected);
    }

    private void BuildUi()
    {
        var shell = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 2,
            BackColor = TerminalTheme.Panel,
        };
        shell.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 420));
        shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 28));
        shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        _source.Dock = DockStyle.Fill;
        _source.ForeColor = TerminalTheme.Muted;
        _source.Font = new Font("Segoe UI", 8.5f);
        shell.Controls.Add(_source, 0, 0);
        shell.SetColumnSpan(_source, 2);

        var ranking = BuildRankingPanel();
        var detail = BuildDetailPanel();
        shell.Controls.Add(ranking, 0, 1);
        shell.Controls.Add(detail, 1, 1);
        Controls.Add(shell);
    }

    private Control BuildRankingPanel()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 2,
            ColumnCount = 1,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(0, 0, 10, 0),
        };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 26));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var header = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 4,
            BackColor = TerminalTheme.PanelAlt,
            Padding = new Padding(8, 4, 8, 0),
        };
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 28));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 26));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 16));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30));
        header.Controls.Add(Header("Symbol"), 0, 0);
        header.Controls.Add(Header("Signal"), 1, 0);
        header.Controls.Add(Header("Long"), 2, 0);
        header.Controls.Add(Header("Short"), 3, 0);

        _rankingRows.Dock = DockStyle.Fill;
        _rankingRows.AutoScroll = true;
        _rankingRows.BackColor = TerminalTheme.Background;
        _rankingRows.ColumnCount = 1;

        panel.Controls.Add(header, 0, 0);
        panel.Controls.Add(_rankingRows, 0, 1);
        return panel;
    }

    private Control BuildDetailPanel()
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 2,
            ColumnCount = 1,
            BackColor = TerminalTheme.Panel,
        };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 230));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var gauges = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 3,
            RowCount = 1,
            BackColor = TerminalTheme.Panel,
        };
        gauges.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 34));
        gauges.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 33));
        gauges.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 33));
        gauges.Controls.Add(WrapGauge("Sumario", _summaryGauge), 0, 0);
        gauges.Controls.Add(WrapGauge("Osciladores", _oscillatorGauge), 1, 0);
        gauges.Controls.Add(WrapGauge("Medias Moveis", _movingAverageGauge), 2, 0);

        var tables = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 1,
            BackColor = TerminalTheme.Panel,
        };
        tables.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        tables.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 50));
        tables.Controls.Add(WrapGrid("Osciladores", _oscillatorGrid), 0, 0);
        tables.Controls.Add(WrapGrid("Medias Moveis", _movingAverageGrid), 1, 0);

        panel.Controls.Add(gauges, 0, 0);
        panel.Controls.Add(tables, 0, 1);
        return panel;
    }

    private void RenderRanking(IReadOnlyList<TechnicalSnapshot> rows)
    {
        _rankingRows.SuspendLayout();
        _rankingRows.Controls.Clear();
        _rankingRows.RowStyles.Clear();
        foreach (var row in rows)
        {
            var item = new TableLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 39,
                ColumnCount = 4,
                BackColor = TerminalTheme.Background,
                Padding = new Padding(8, 5, 8, 3),
                Margin = new Padding(0, 0, 0, 1),
            };
            item.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 28));
            item.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 26));
            item.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 16));
            item.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30));

            item.Controls.Add(Cell(row.Symbol, TerminalTheme.Text, FontStyle.Bold), 0, 0);
            item.Controls.Add(Cell(row.Signal, SignalColor(row.Signal), FontStyle.Bold), 1, 0);
            item.Controls.Add(Cell($"{row.LongPercent:0}%", TerminalTheme.Positive, FontStyle.Bold), 2, 0);
            item.Controls.Add(new LongShortBar(row.LongPercent, row.ShortPercent) { Dock = DockStyle.Fill }, 3, 0);
            _rankingRows.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            _rankingRows.Controls.Add(item);
        }
        _rankingRows.ResumeLayout();
    }

    private void RenderSelected(TechnicalSnapshot? selected)
    {
        if (selected is null)
        {
            _summaryGauge.SetState("Sem dados", 0, 0, 0);
            _oscillatorGauge.SetState("Sem dados", 0, 0, 0);
            _movingAverageGauge.SetState("Sem dados", 0, 0, 0);
            FillGrid(_oscillatorGrid, Array.Empty<IndicatorRow>());
            FillGrid(_movingAverageGrid, Array.Empty<IndicatorRow>());
            return;
        }

        _summaryGauge.SetState(selected.Signal, selected.LongPercent, selected.BuyVotes, selected.NeutralVotes);
        _oscillatorGauge.SetState(selected.OscillatorSignal, selected.OscillatorLongPercent, selected.OscillatorBuyVotes, selected.OscillatorNeutralVotes);
        _movingAverageGauge.SetState(selected.MovingAverageSignal, selected.MovingAverageLongPercent, selected.MovingAverageBuyVotes, selected.MovingAverageNeutralVotes);
        FillGrid(_oscillatorGrid, selected.Oscillators);
        FillGrid(_movingAverageGrid, selected.MovingAverages);
    }

    private TechnicalSnapshot? BuildAnalysis(string symbol, string timeframe, int maxBars)
    {
        var candles = LoadCandles(symbol, timeframe, maxBars);
        if (candles.Count < 60)
        {
            return null;
        }

        var closes = candles.Select(item => item.Close).ToArray();
        var highs = candles.Select(item => item.High).ToArray();
        var lows = candles.Select(item => item.Low).ToArray();
        var last = closes[^1];

        var oscillators = new[]
        {
            Indicator("RSI (14)", Rsi(closes, 14), value => value > 60 ? "BUY" : value < 40 ? "SELL" : "NEUTRAL"),
            Indicator("Estocastico %K (14)", Stochastic(highs, lows, closes, 14), value => value > 70 ? "BUY" : value < 30 ? "SELL" : "NEUTRAL"),
            Indicator("CCI (20)", Cci(highs, lows, closes, 20), value => value > 100 ? "BUY" : value < -100 ? "SELL" : "NEUTRAL"),
            Indicator("Momentum (10)", last - closes[^11], value => value > 0 ? "BUY" : value < 0 ? "SELL" : "NEUTRAL"),
            Indicator("MACD hist (12,26,9)", MacdHistogram(closes), value => value > 0 ? "BUY" : value < 0 ? "SELL" : "NEUTRAL"),
        };

        var movingAverages = new[]
        {
            MaRow("EMA 9", last, EmaLast(closes, 9)),
            MaRow("EMA 21", last, EmaLast(closes, 21)),
            MaRow("EMA 50", last, EmaLast(closes, 50)),
            MaRow("SMA 20", last, SmaLast(closes, 20)),
            MaRow("SMA 50", last, SmaLast(closes, 50)),
            MaRow("SMA 100", last, SmaLast(closes, 100)),
            MaRow("SMA 200", last, SmaLast(closes, 200)),
        };

        var all = oscillators.Concat(movingAverages).ToArray();
        var longPercent = VotePercent(all, "BUY");
        var shortPercent = VotePercent(all, "SELL");
        var oscLong = VotePercent(oscillators, "BUY");
        var maLong = VotePercent(movingAverages, "BUY");
        return new TechnicalSnapshot(
            symbol,
            SignalFrom(longPercent, shortPercent),
            longPercent,
            shortPercent,
            SignalFrom(oscLong, VotePercent(oscillators, "SELL")),
            oscLong,
            SignalFrom(maLong, VotePercent(movingAverages, "SELL")),
            maLong,
            all.Count(item => item.Action == "BUY"),
            all.Count(item => item.Action == "NEUTRAL"),
            oscillators.Count(item => item.Action == "BUY"),
            oscillators.Count(item => item.Action == "NEUTRAL"),
            movingAverages.Count(item => item.Action == "BUY"),
            movingAverages.Count(item => item.Action == "NEUTRAL"),
            oscillators,
            movingAverages
        );
    }

    private IReadOnlyList<Candle> LoadCandles(string symbol, string timeframe, int maxBars)
    {
        var csv = _csvLoader.Load(symbol, timeframe, maxBars);
        var live = _snapshotLoader.Load(symbol, timeframe).Candles;
        if (live.Count == 0)
        {
            return csv;
        }

        var byTime = new SortedDictionary<DateTime, Candle>();
        foreach (var candle in csv)
        {
            byTime[candle.Time] = candle;
        }
        foreach (var candle in live)
        {
            byTime[candle.Time] = candle;
        }
        return CandleFilters.RemoveWeekendCandles(byTime.Values).TakeLast(maxBars).ToArray();
    }

    private static IndicatorRow Indicator(string name, double value, Func<double, string> action)
    {
        return new IndicatorRow(name, value.ToString("0.#####", CultureInfo.InvariantCulture), action(value));
    }

    private static IndicatorRow MaRow(string name, double last, double value)
    {
        var action = last > value ? "BUY" : last < value ? "SELL" : "NEUTRAL";
        return new IndicatorRow(name, value.ToString("0.#####", CultureInfo.InvariantCulture), action);
    }

    private static double VotePercent(IReadOnlyList<IndicatorRow> rows, string action)
    {
        return rows.Count == 0 ? 0 : rows.Count(item => item.Action == action) * 100.0 / rows.Count;
    }

    private static string SignalFrom(double longPercent, double shortPercent)
    {
        var diff = longPercent - shortPercent;
        if (diff >= 45) return "Strong Buy";
        if (diff >= 12) return "Buy";
        if (diff <= -45) return "Strong Sell";
        if (diff <= -12) return "Sell";
        return "Neutral";
    }

    private static Color SignalColor(string signal)
    {
        return signal.Contains("Buy", StringComparison.OrdinalIgnoreCase) ? TerminalTheme.Positive
            : signal.Contains("Sell", StringComparison.OrdinalIgnoreCase) ? TerminalTheme.Negative
            : TerminalTheme.Muted;
    }

    private static double SmaLast(IReadOnlyList<double> values, int period)
    {
        if (values.Count < period) return values[^1];
        return values.Skip(values.Count - period).Average();
    }

    private static double EmaLast(IReadOnlyList<double> values, int period)
    {
        if (values.Count == 0) return 0;
        var k = 2.0 / (period + 1);
        var ema = values[0];
        for (var i = 1; i < values.Count; i++)
        {
            ema = values[i] * k + ema * (1 - k);
        }
        return ema;
    }

    private static double Rsi(IReadOnlyList<double> values, int period)
    {
        if (values.Count <= period) return 50;
        double gains = 0;
        double losses = 0;
        for (var i = values.Count - period; i < values.Count; i++)
        {
            var diff = values[i] - values[i - 1];
            if (diff >= 0) gains += diff;
            else losses -= diff;
        }
        if (losses <= 0) return 100;
        var rs = gains / losses;
        return 100 - 100 / (1 + rs);
    }

    private static double Stochastic(IReadOnlyList<double> highs, IReadOnlyList<double> lows, IReadOnlyList<double> closes, int period)
    {
        if (closes.Count < period) return 50;
        var high = highs.Skip(highs.Count - period).Max();
        var low = lows.Skip(lows.Count - period).Min();
        return Math.Abs(high - low) < 0.0000001 ? 50 : (closes[^1] - low) / (high - low) * 100;
    }

    private static double Cci(IReadOnlyList<double> highs, IReadOnlyList<double> lows, IReadOnlyList<double> closes, int period)
    {
        if (closes.Count < period) return 0;
        var typical = highs.Zip(lows, (h, l) => (h, l)).Zip(closes, (hl, c) => (hl.h + hl.l + c) / 3.0).ToArray();
        var recent = typical.TakeLast(period).ToArray();
        var sma = recent.Average();
        var meanDeviation = recent.Select(item => Math.Abs(item - sma)).Average();
        return meanDeviation <= 0 ? 0 : (recent[^1] - sma) / (0.015 * meanDeviation);
    }

    private static double MacdHistogram(IReadOnlyList<double> values)
    {
        if (values.Count < 35) return 0;
        var macd = new List<double>();
        for (var i = 0; i < values.Count; i++)
        {
            var slice = values.Take(i + 1).ToArray();
            macd.Add(EmaLast(slice, 12) - EmaLast(slice, 26));
        }
        return macd[^1] - EmaLast(macd, 9);
    }

    private static Label Header(string text) => new()
    {
        Text = text,
        Dock = DockStyle.Fill,
        ForeColor = TerminalTheme.Text,
        Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
        TextAlign = ContentAlignment.MiddleLeft,
    };

    private static Label Cell(string text, Color color, FontStyle style = FontStyle.Regular) => new()
    {
        Text = text,
        Dock = DockStyle.Fill,
        ForeColor = color,
        Font = new Font("Segoe UI", 8.5f, style),
        TextAlign = ContentAlignment.MiddleLeft,
        AutoEllipsis = true,
    };

    private static Control WrapGauge(string title, GaugeControl gauge)
    {
        var panel = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 2, ColumnCount = 1, BackColor = TerminalTheme.Panel, Padding = new Padding(8) };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 22));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        panel.Controls.Add(Header(title), 0, 0);
        panel.Controls.Add(gauge, 0, 1);
        return panel;
    }

    private static Control WrapGrid(string title, DataGridView grid)
    {
        ConfigureGrid(grid);
        var panel = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 2, ColumnCount = 1, BackColor = TerminalTheme.Panel, Padding = new Padding(8) };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 24));
        panel.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        panel.Controls.Add(Header(title), 0, 0);
        panel.Controls.Add(grid, 0, 1);
        return panel;
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

    private static void FillGrid(DataGridView grid, IReadOnlyList<IndicatorRow> rows)
    {
        grid.Columns.Clear();
        grid.Rows.Clear();
        grid.Columns.Add("name", "Nome");
        grid.Columns.Add("value", "Valor");
        grid.Columns.Add("action", "Acao");
        foreach (var row in rows)
        {
            var index = grid.Rows.Add(row.Name, row.Value, ActionLabel(row.Action));
            grid.Rows[index].Cells[2].Style.ForeColor = row.Action == "BUY" ? TerminalTheme.Positive
                : row.Action == "SELL" ? TerminalTheme.Negative
                : TerminalTheme.Muted;
        }
    }

    private static string ActionLabel(string action) => action switch
    {
        "BUY" => "Vies de alta",
        "SELL" => "Tendencia de Baixa",
        _ => "Tendencia Neutra",
    };

    private sealed record TechnicalSnapshot(
        string Symbol,
        string Signal,
        double LongPercent,
        double ShortPercent,
        string OscillatorSignal,
        double OscillatorLongPercent,
        string MovingAverageSignal,
        double MovingAverageLongPercent,
        int BuyVotes,
        int NeutralVotes,
        int OscillatorBuyVotes,
        int OscillatorNeutralVotes,
        int MovingAverageBuyVotes,
        int MovingAverageNeutralVotes,
        IReadOnlyList<IndicatorRow> Oscillators,
        IReadOnlyList<IndicatorRow> MovingAverages
    );

    private sealed record IndicatorRow(string Name, string Value, string Action);

    private sealed class LongShortBar : Control
    {
        private readonly double _longPercent;
        private readonly double _shortPercent;

        public LongShortBar(double longPercent, double shortPercent)
        {
            _longPercent = Math.Clamp(longPercent, 0, 100);
            _shortPercent = Math.Clamp(shortPercent, 0, 100);
            Height = 18;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            var g = e.Graphics;
            g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
            var bar = new RectangleF(0, Height / 2f - 4, Width - 38, 8);
            using var red = new SolidBrush(TerminalTheme.Negative);
            using var green = new SolidBrush(TerminalTheme.Positive);
            using var muted = new SolidBrush(Color.FromArgb(45, 58, 76));
            g.FillRoundedRectangle(muted, bar, 4);
            var longWidth = (float)(bar.Width * _longPercent / 100.0);
            if (longWidth > 0)
            {
                g.FillRoundedRectangle(green, new RectangleF(bar.X, bar.Y, longWidth, bar.Height), 4);
            }
            var shortWidth = Math.Max(0, bar.Width - longWidth);
            if (shortWidth > 0)
            {
                g.FillRoundedRectangle(red, new RectangleF(bar.X + longWidth, bar.Y, shortWidth, bar.Height), 4);
            }
            using var font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
            using var brush = new SolidBrush(TerminalTheme.Negative);
            g.DrawString($"{_shortPercent:0}%", font, brush, bar.Right + 6, 0);
        }
    }

    private sealed class GaugeControl : Control
    {
        private string _state = "Neutral";
        private double _longPercent;
        private int _buyVotes;
        private int _neutralVotes;

        public void SetState(string state, double longPercent, int buyVotes, int neutralVotes)
        {
            _state = state;
            _longPercent = Math.Clamp(longPercent, 0, 100);
            _buyVotes = buyVotes;
            _neutralVotes = neutralVotes;
            Invalidate();
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            var g = e.Graphics;
            g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
            g.Clear(TerminalTheme.Panel);
            var w = Width;
            var h = Height;
            var rect = new RectangleF(20, 20, Math.Max(20, w - 40), Math.Max(20, h * 1.3f));
            using var basePen = new Pen(Color.FromArgb(48, 60, 78), 14);
            using var activePen = new Pen(SignalColor(_state), 14);
            g.DrawArc(basePen, rect, 180, 180);
            g.DrawArc(activePen, rect, 180, (float)(_longPercent * 1.8));

            var angle = Math.PI * (1 + _longPercent / 100.0);
            var center = new PointF(rect.Left + rect.Width / 2, rect.Top + rect.Height / 2);
            var radius = rect.Width * 0.34f;
            var end = new PointF(center.X + (float)Math.Cos(angle) * radius, center.Y + (float)Math.Sin(angle) * radius);
            using var needle = new Pen(Color.FromArgb(226, 232, 240), 3);
            g.DrawLine(needle, center, end);
            using var dot = new SolidBrush(Color.FromArgb(226, 232, 240));
            g.FillEllipse(dot, center.X - 5, center.Y - 5, 10, 10);

            using var titleFont = new Font("Segoe UI", 13f, FontStyle.Bold);
            using var smallFont = new Font("Segoe UI", 8.5f, FontStyle.Bold);
            using var stateBrush = new SolidBrush(SignalColor(_state));
            using var mutedBrush = new SolidBrush(TerminalTheme.Muted);
            var label = _state.Replace("Strong ", "Strong ");
            var size = g.MeasureString(label, titleFont);
            g.DrawString(label, titleFont, stateBrush, (w - size.Width) / 2, h - 58);
            g.DrawString($"Alta {_buyVotes}   Neutro {_neutralVotes}", smallFont, mutedBrush, 18, h - 28);
        }
    }
}

internal static class GraphicsRoundedExtensions
{
    public static void FillRoundedRectangle(this Graphics graphics, Brush brush, RectangleF bounds, float radius)
    {
        using var path = new System.Drawing.Drawing2D.GraphicsPath();
        var diameter = radius * 2;
        path.AddArc(bounds.X, bounds.Y, diameter, diameter, 180, 90);
        path.AddArc(bounds.Right - diameter, bounds.Y, diameter, diameter, 270, 90);
        path.AddArc(bounds.Right - diameter, bounds.Bottom - diameter, diameter, diameter, 0, 90);
        path.AddArc(bounds.X, bounds.Bottom - diameter, diameter, diameter, 90, 90);
        path.CloseFigure();
        graphics.FillPath(brush, path);
    }
}
