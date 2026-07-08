using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Models;

namespace FusionTerminalWindows.Chart;

public sealed class CandleChartControl : Control
{
    private const int LeftAxisWidth = 58;
    private const int PriceAxisWidth = 86;
    private const int TopChromeHeight = 34;
    private const int BottomAxisHeight = 76;
    private readonly List<Candle> _candles = new();
    private readonly List<SignalMarker> _signals = new();
    private readonly List<BacktestTrade> _backtestTrades = new();
    private int _firstVisible;
    private int _visibleCount = 180;
    private int _rightMarginCandles = 18;
    private Point? _dragStart;
    private int _dragFirstVisible;
    private DragMode _dragMode = DragMode.None;
    private double _dragPriceCenter;
    private double _dragPriceSpan;
    private double? _manualPriceMin;
    private double? _manualPriceMax;
    private Point? _mouse;
    private MovingAverageMode _movingAverageMode = MovingAverageMode.None;
    private SimulatedOrder? _simulatedOrder;
    private SelectedSignal? _selectedSignal;
    private bool _simulationPlaying;
    private int _simulationCandleIndex = -1;
    private int _simulationPhase;
    private double? _simulationPrice;
    private double? _activeTrailingStop;
    private string _simulationStatus = "";
    private readonly List<SignalHitBox> _signalHitBoxes = new();

    public event EventHandler<SelectedSignal>? SignalSelected;

    public CandleChartControl()
    {
        DoubleBuffered = true;
        BackColor = Color.FromArgb(7, 14, 23);
        ForeColor = Color.FromArgb(226, 232, 240);
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true);
    }

    public void SetCandles(IReadOnlyList<Candle> candles)
    {
        var wasAtEnd = _candles.Count == 0 || _firstVisible >= MaxFirstVisible() - 1;
        _candles.Clear();
        _candles.AddRange(candles);
        _visibleCount = Math.Clamp(_visibleCount, 40, Math.Max(40, _candles.Count));
        _firstVisible = wasAtEnd
            ? MaxFirstVisible()
            : Math.Clamp(_firstVisible, 0, MaxFirstVisible());
        Invalidate();
    }

    public void SetSignals(IReadOnlyList<SignalMarker> signals)
    {
        _signals.Clear();
        _signals.AddRange(signals);
        Invalidate();
    }

    public void SetBacktestTrades(IReadOnlyList<BacktestTrade> trades)
    {
        _backtestTrades.Clear();
        _backtestTrades.AddRange(trades);
        Invalidate();
    }

    [Browsable(false)]
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public int RightMarginCandles
    {
        get => _rightMarginCandles;
        set
        {
            var wasAtEnd = _firstVisible >= MaxFirstVisible() - 1;
            _rightMarginCandles = Math.Clamp(value, 0, 120);
            _firstVisible = wasAtEnd
                ? MaxFirstVisible()
                : Math.Clamp(_firstVisible, 0, MaxFirstVisible());
            Invalidate();
        }
    }

    [Browsable(false)]
    [DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public MovingAverageMode MovingAverageMode
    {
        get => _movingAverageMode;
        set
        {
            _movingAverageMode = value;
            Invalidate();
        }
    }

    public void ResetViewToLatest()
    {
        if (_candles.Count == 0)
        {
            return;
        }

        _firstVisible = MaxFirstVisible();
        _manualPriceMin = null;
        _manualPriceMax = null;
        Invalidate();
    }

    public void ResetPriceScale()
    {
        _manualPriceMin = null;
        _manualPriceMax = null;
        Invalidate();
    }

    public void ZoomIn()
    {
        ZoomTimeAxis(0.72, 0.5);
    }

    public void ZoomOut()
    {
        ZoomTimeAxis(1.38, 0.5);
    }

    public void CreateSimulatedOrder(SimulationSettings settings)
    {
        if (_candles.Count == 0)
        {
            return;
        }

        var last = _candles[^1];
        var side = settings.Side == SimulationSide.Auto
            ? (last.Close >= last.Open ? SimulationSide.Buy : SimulationSide.Sell)
            : settings.Side;
        _simulatedOrder = new SimulatedOrder(last.Symbol, last.Time, last.Close, last.Decimals, last.PointValue, side, settings);
        ResetSimulationCursor(last.Time);
        Invalidate();
    }

    public void CreateSimulatedOrderFromSignal(SelectedSignal selectedSignal, SimulationSettings settings)
    {
        var candle = selectedSignal.Candle;
        _selectedSignal = selectedSignal;
        var side = selectedSignal.Signal.Side == SimulationSide.Auto
            ? (candle.Close >= candle.Open ? SimulationSide.Buy : SimulationSide.Sell)
            : selectedSignal.Signal.Side;
        _simulatedOrder = new SimulatedOrder(candle.Symbol, candle.Time, candle.Close, candle.Decimals, candle.PointValue, side, settings with { Side = side });
        ResetSimulationCursor(candle.Time);
        Invalidate();
    }

    public void UpdateSimulationSettings(SimulationSettings settings)
    {
        if (_simulatedOrder is null)
        {
            return;
        }

        _simulatedOrder = _simulatedOrder with { Settings = settings };
        Invalidate();
    }

    public void StartSimulationPlayback()
    {
        if (_simulatedOrder is null)
        {
            return;
        }
        if (_simulationCandleIndex < 0)
        {
            ResetSimulationCursor(_simulatedOrder.EntryTime);
        }
        _simulationPlaying = true;
        _simulationStatus = "simulando";
        Invalidate();
    }

    public void PauseSimulationPlayback()
    {
        _simulationPlaying = false;
        _simulationStatus = "pausado";
        Invalidate();
    }

    public void StopSimulationPlayback()
    {
        _simulationPlaying = false;
        if (_simulatedOrder is not null)
        {
            ResetSimulationCursor(_simulatedOrder.EntryTime);
        }
        _simulationStatus = "parado";
        Invalidate();
    }

    public int SimulationTimerInterval()
    {
        var speed = _simulatedOrder?.Settings.Speed ?? 5;
        return Math.Clamp(650 - speed * 55, 80, 650);
    }

    public void StepSimulationPlayback()
    {
        if (!_simulationPlaying || _simulatedOrder is null || _simulationCandleIndex < 0 || _candles.Count == 0)
        {
            return;
        }
        if (_simulationCandleIndex >= _candles.Count)
        {
            _simulationPlaying = false;
            _simulationStatus = "fim do historico";
            Invalidate();
            return;
        }

        var candle = _candles[_simulationCandleIndex];
        var sequence = _simulatedOrder.IsBuy
            ? new[] { candle.Open, candle.Low, candle.High, candle.Close }
            : new[] { candle.Open, candle.High, candle.Low, candle.Close };
        _simulationPrice = sequence[Math.Clamp(_simulationPhase, 0, 3)];
        UpdateTrailingStop(_simulationPrice.Value);
        if (ShouldStopSimulation(_simulationPrice.Value, out var reason))
        {
            _simulationPlaying = false;
            _simulationStatus = reason;
            Invalidate();
            return;
        }

        _simulationPhase++;
        if (_simulationPhase >= 4)
        {
            _simulationPhase = 0;
            _simulationCandleIndex++;
        }
        Invalidate();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        g.SmoothingMode = SmoothingMode.None;
        g.Clear(BackColor);

        var plot = PlotRect();
        DrawChrome(g, plot);
        if (_candles.Count == 0)
        {
            DrawCentered(g, "Sem candles carregados");
            return;
        }

        var visibleDataCount = VisibleDataCount();
        var last = Math.Min(_candles.Count, _firstVisible + visibleDataCount);
        if (last <= _firstVisible)
        {
            return;
        }

        var visible = _candles.GetRange(_firstVisible, last - _firstVisible);
        var (minLow, maxHigh) = PriceRange(visible);

        DrawGrid(g, plot, minLow, maxHigh);
        DrawCandles(g, plot, visible, minLow, maxHigh, _rightMarginCandles);
        DrawSimulationHighlight(g, plot, visible);
        DrawMovingAverages(g, plot, visible, minLow, maxHigh);
        DrawBacktestTrades(g, plot, visible, minLow, maxHigh);
        DrawSignalMarkers(g, plot, visible, minLow, maxHigh);
        DrawSimulatedOrder(g, plot, minLow, maxHigh);
        DrawSimulationPrice(g, plot, minLow, maxHigh);
        DrawPriceAxis(g, plot, minLow, maxHigh);
        DrawTimeAxis(g, plot, visible);
        DrawCrosshair(g, plot, visible, minLow, maxHigh);
    }

    protected override void OnMouseWheel(MouseEventArgs e)
    {
        if (_candles.Count == 0)
        {
            return;
        }

        var step = Math.Max(1, VisibleDataCount() / 10);
        var direction = e.Delta > 0 ? 1 : -1;
        _firstVisible = Math.Clamp(_firstVisible + direction * step, 0, MaxFirstVisible());
        Invalidate();
    }

    protected override void OnMouseDown(MouseEventArgs e)
    {
        if (e.Button == MouseButtons.Left)
        {
            var selectedSignal = HitTestSignal(e.Location);
            if (selectedSignal is not null)
            {
                SignalSelected?.Invoke(this, selectedSignal);
                return;
            }

            _dragStart = e.Location;
            _dragFirstVisible = _firstVisible;
            if (PriceAxisRect().Contains(e.Location))
            {
                var visible = VisibleCandles();
                var range = PriceRange(visible);
                _dragMode = DragMode.PriceScale;
                _dragPriceCenter = (range.Min + range.Max) / 2.0;
                _dragPriceSpan = Math.Max(range.Max - range.Min, 0.00001);
                Cursor = Cursors.SizeNS;
            }
            else
            {
                _dragMode = DragMode.TimePan;
                Cursor = Cursors.Hand;
            }
        }
        else if (e.Button == MouseButtons.Middle)
        {
            _dragStart = e.Location;
            var visible = VisibleCandles();
            var range = PriceRange(visible);
            _dragMode = DragMode.PricePan;
            _dragPriceCenter = (range.Min + range.Max) / 2.0;
            _dragPriceSpan = Math.Max(range.Max - range.Min, 0.00001);
            Cursor = Cursors.SizeAll;
        }
    }

    protected override void OnMouseUp(MouseEventArgs e)
    {
        _dragStart = null;
        _dragMode = DragMode.None;
        Cursor = Cursors.Default;
    }

    protected override void OnMouseMove(MouseEventArgs e)
    {
        _mouse = e.Location;
        if (_dragStart.HasValue && _candles.Count > 0)
        {
            if (_dragMode == DragMode.PriceScale)
            {
                var dy = e.Y - _dragStart.Value.Y;
                var factor = Math.Exp(dy / 180.0);
                var span = Math.Clamp(_dragPriceSpan * factor, _dragPriceSpan * 0.02, _dragPriceSpan * 50.0);
                _manualPriceMin = _dragPriceCenter - span / 2.0;
                _manualPriceMax = _dragPriceCenter + span / 2.0;
            }
            else if (_dragMode == DragMode.PricePan)
            {
                var dy = e.Y - _dragStart.Value.Y;
                var plot = PlotRect();
                var priceDelta = dy / Math.Max(1.0, plot.Height) * _dragPriceSpan;
                var center = _dragPriceCenter + priceDelta;
                _manualPriceMin = center - _dragPriceSpan / 2.0;
                _manualPriceMax = center + _dragPriceSpan / 2.0;
            }
            else if (_dragMode == DragMode.TimePan)
            {
                var plot = PlotRect();
                var candleWidth = Math.Max(1.0, plot.Width / Math.Max(1, _visibleCount));
                var delta = (int)Math.Round((_dragStart.Value.X - e.X) / candleWidth);
                _firstVisible = Math.Clamp(_dragFirstVisible + delta, 0, MaxFirstVisible());
            }
        }
        else
        {
            Cursor = PriceAxisRect().Contains(e.Location) ? Cursors.SizeNS : Cursors.Default;
        }
        Invalidate();
    }

    protected override void OnMouseLeave(EventArgs e)
    {
        _mouse = null;
        Invalidate();
    }

    private RectangleF PlotRect()
    {
        return new RectangleF(
            LeftAxisWidth,
            TopChromeHeight,
            Math.Max(10, Width - LeftAxisWidth - PriceAxisWidth),
            Math.Max(10, Height - BottomAxisHeight)
        );
    }

    private RectangleF PriceAxisRect()
    {
        var plot = PlotRect();
        return new RectangleF(plot.Right, plot.Top, PriceAxisWidth, plot.Height);
    }

    private List<Candle> VisibleCandles()
    {
        if (_candles.Count == 0)
        {
            return new List<Candle>();
        }
        var last = Math.Min(_candles.Count, _firstVisible + VisibleDataCount());
        if (last <= _firstVisible)
        {
            return new List<Candle>();
        }
        return _candles.GetRange(_firstVisible, last - _firstVisible);
    }

    private (double Min, double Max) PriceRange(IReadOnlyList<Candle> visible)
    {
        if (_manualPriceMin.HasValue && _manualPriceMax.HasValue && _manualPriceMax > _manualPriceMin)
        {
            return (_manualPriceMin.Value, _manualPriceMax.Value);
        }
        if (visible.Count == 0)
        {
            return (0.0, 1.0);
        }
        var minLow = visible.Min(item => item.Low);
        var maxHigh = visible.Max(item => item.High);
        foreach (var level in SimulationLevels())
        {
            minLow = Math.Min(minLow, level.Price);
            maxHigh = Math.Max(maxHigh, level.Price);
        }
        var span = Math.Max(maxHigh - minLow, 0.00001);
        return (minLow - span * 0.08, maxHigh + span * 0.08);
    }

    private int VisibleDataCount()
    {
        return Math.Max(1, _visibleCount - _rightMarginCandles);
    }

    private int MaxFirstVisible()
    {
        return Math.Max(0, _candles.Count - VisibleDataCount());
    }

    private void ZoomTimeAxis(double factor, double anchorRatio)
    {
        if (_candles.Count == 0)
        {
            return;
        }

        var oldCount = VisibleDataCount();
        var oldMaxFirst = MaxFirstVisible();
        var wasAtEnd = _firstVisible >= oldMaxFirst - 2;
        _visibleCount = Math.Clamp((int)Math.Round(_visibleCount * factor), 25, Math.Max(25, _candles.Count));
        anchorRatio = Math.Clamp(anchorRatio, 0.0, 1.0);
        if (wasAtEnd)
        {
            _firstVisible = MaxFirstVisible();
        }
        else
        {
            var anchor = _firstVisible + (int)Math.Round(oldCount * anchorRatio);
            _firstVisible = Math.Clamp(anchor - (int)Math.Round(VisibleDataCount() * anchorRatio), 0, MaxFirstVisible());
        }
        Invalidate();
    }

    private static void DrawChrome(Graphics g, RectangleF plot)
    {
        using var border = new Pen(Color.FromArgb(42, 57, 78));
        g.DrawRectangle(border, plot.X, plot.Y, plot.Width, plot.Height);
    }

    private void DrawCandles(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles, double min, double max, int rightMarginCandles)
    {
        var slots = Math.Max(1, candles.Count + rightMarginCandles);
        var candleSlot = plot.Width / slots;
        var bodyWidth = Math.Max(2, Math.Min(32, candleSlot * 0.72f));
        using var upBrush = new SolidBrush(Color.FromArgb(0, 215, 178));
        using var downBrush = new SolidBrush(Color.FromArgb(255, 77, 109));
        using var outline = new Pen(Color.FromArgb(245, 245, 245), 1f);

        for (var i = 0; i < candles.Count; i++)
        {
            var candle = candles[i];
            var x = plot.Left + i * candleSlot + candleSlot / 2f;
            var highY = PriceToY(candle.High, plot, min, max);
            var lowY = PriceToY(candle.Low, plot, min, max);
            var openY = PriceToY(candle.Open, plot, min, max);
            var closeY = PriceToY(candle.Close, plot, min, max);
            var top = Math.Min(openY, closeY);
            var height = Math.Max(1, Math.Abs(closeY - openY));
            var brush = candle.Close >= candle.Open ? upBrush : downBrush;

            g.DrawLine(outline, x, highY, x, lowY);
            g.FillRectangle(brush, x - bodyWidth / 2f, top, bodyWidth, height);
            g.DrawRectangle(outline, x - bodyWidth / 2f, top, bodyWidth, height);
        }
    }

    private void DrawSimulationHighlight(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles)
    {
        if (_simulationCandleIndex < _firstVisible || _simulationCandleIndex >= _firstVisible + candles.Count)
        {
            return;
        }
        var localIndex = _simulationCandleIndex - _firstVisible;
        var slots = Math.Max(1, candles.Count + _rightMarginCandles);
        var candleSlot = plot.Width / slots;
        var x = plot.Left + localIndex * candleSlot;
        using var brush = new SolidBrush(Color.FromArgb(35, 250, 204, 21));
        using var pen = new Pen(Color.FromArgb(250, 204, 21), 1f);
        var rect = new RectangleF(x, plot.Top, candleSlot, plot.Height);
        g.FillRectangle(brush, rect);
        g.DrawRectangle(pen, rect.X, rect.Y, rect.Width, rect.Height);
    }

    private void DrawGrid(Graphics g, RectangleF plot, double min, double max)
    {
        using var minor = new Pen(Color.FromArgb(26, 38, 55));
        using var major = new Pen(Color.FromArgb(44, 61, 84));
        for (var i = 1; i < 8; i++)
        {
            var y = plot.Top + plot.Height * i / 8f;
            g.DrawLine(i % 2 == 0 ? major : minor, plot.Left, y, plot.Right, y);
        }
        for (var i = 1; i < 10; i++)
        {
            var x = plot.Left + plot.Width * i / 10f;
            g.DrawLine(i % 2 == 0 ? major : minor, x, plot.Top, x, plot.Bottom);
        }
    }

    private void DrawMovingAverages(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles, double min, double max)
    {
        if (_movingAverageMode == MovingAverageMode.None || candles.Count < 2)
        {
            return;
        }

        DrawAverageLine(g, plot, candles, min, max, 9, Color.FromArgb(30, 180, 255));
        DrawAverageLine(g, plot, candles, min, max, 21, Color.FromArgb(255, 183, 0));
        DrawAverageLine(g, plot, candles, min, max, 50, Color.FromArgb(218, 72, 255));
    }

    private void DrawSignalMarkers(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles, double min, double max)
    {
        _signalHitBoxes.Clear();
        if (_signals.Count == 0 || candles.Count == 0)
        {
            return;
        }

        var firstTime = candles[0].Time;
        var lastTime = candles[^1].Time;
        var visibleSignals = _signals
            .Where(signal => signal.Time >= firstTime.AddDays(-1) && signal.Time <= lastTime.AddDays(1))
            .ToArray();
        if (visibleSignals.Length == 0)
        {
            return;
        }

        var slots = Math.Max(1, candles.Count + _rightMarginCandles);
        var candleSlot = plot.Width / slots;
        foreach (var signal in visibleSignals)
        {
            var index = FindNearestCandleIndex(candles, signal.Time);
            if (index < 0)
            {
                continue;
            }

            var candle = candles[index];
            var x = plot.Left + index * candleSlot + candleSlot / 2f;
            var isBuy = signal.Side == SimulationSide.Buy;
            var anchorPrice = isBuy ? candle.Low : candle.High;
            var y = PriceToY(anchorPrice, plot, min, max) + (isBuy ? 14 : -14);
            var color = isBuy ? Color.FromArgb(34, 197, 94) : Color.FromArgb(239, 68, 68);
            var isSelected = IsSelectedSignal(signal, candle);
            DrawArrow(g, x, y, isBuy, color, isSelected);
            _signalHitBoxes.Add(new SignalHitBox(new RectangleF(x - 10, y - 10, 20, 20), signal, candle));
        }
    }

    private void DrawBacktestTrades(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles, double min, double max)
    {
        if (_backtestTrades.Count == 0 || candles.Count == 0)
        {
            return;
        }

        var firstTime = candles[0].Time.AddDays(-2);
        var lastTime = candles[^1].Time.AddDays(2);
        var visibleTrades = _backtestTrades
            .Where(trade => trade.ExitTime >= firstTime && trade.EntryTime <= lastTime)
            .TakeLast(250)
            .ToArray();
        if (visibleTrades.Length == 0)
        {
            return;
        }

        var slots = Math.Max(1, candles.Count + _rightMarginCandles);
        var candleSlot = plot.Width / slots;
        using var winPen = new Pen(Color.FromArgb(34, 197, 94), 1.8f);
        using var lossPen = new Pen(Color.FromArgb(239, 68, 68), 1.8f);
        using var slPen = new Pen(Color.FromArgb(239, 68, 68), 1f) { DashStyle = DashStyle.Dash };
        using var tpPen = new Pen(Color.FromArgb(34, 197, 94), 1f) { DashStyle = DashStyle.Dash };
        using var labelFont = new Font("Segoe UI", 8f, FontStyle.Bold);

        foreach (var trade in visibleTrades)
        {
            var entryIndex = FindNearestCandleIndex(candles, trade.EntryTime);
            var exitIndex = FindNearestCandleIndex(candles, trade.ExitTime);
            if (entryIndex < 0 && exitIndex < 0)
            {
                continue;
            }
            entryIndex = entryIndex < 0 ? 0 : entryIndex;
            exitIndex = exitIndex < 0 ? candles.Count - 1 : exitIndex;
            var x1 = plot.Left + entryIndex * candleSlot + candleSlot / 2f;
            var x2 = plot.Left + exitIndex * candleSlot + candleSlot / 2f;
            var y1 = PriceToY(trade.EntryPrice, plot, min, max);
            var y2 = PriceToY(trade.ExitPrice, plot, min, max);
            var pen = trade.IsWin ? winPen : lossPen;
            var color = trade.IsWin ? Color.FromArgb(34, 197, 94) : Color.FromArgb(239, 68, 68);
            g.DrawLine(pen, x1, y1, x2, y2);
            DrawArrow(g, x1, trade.IsBuy ? y1 + 13 : y1 - 13, trade.IsBuy, trade.IsBuy ? Color.FromArgb(34, 197, 94) : Color.FromArgb(249, 115, 22), false);

            using var exitBrush = new SolidBrush(color);
            using var exitOutline = new Pen(Color.White, 1f);
            g.FillEllipse(exitBrush, x2 - 4, y2 - 4, 8, 8);
            g.DrawEllipse(exitOutline, x2 - 4, y2 - 4, 8, 8);

            var left = Math.Min(x1, x2);
            var right = Math.Max(x1, x2);
            if (trade.StopLoss > 0)
            {
                var y = PriceToY(trade.StopLoss, plot, min, max);
                g.DrawLine(slPen, left, y, right, y);
            }
            if (trade.TakeProfit > 0)
            {
                var y = PriceToY(trade.TakeProfit, plot, min, max);
                g.DrawLine(tpPen, left, y, right, y);
            }

            using var textBrush = new SolidBrush(color);
            var label = trade.IsBuy ? "Buy" : "Sell";
            var exitLabel = trade.IsBuy ? "SellToCover" : "BuyToCover";
            g.DrawString($"{label} ({trade.PnlPoints:0})", labelFont, textBrush, x1 + 5, y1 + (trade.IsBuy ? -28 : 10));
            g.DrawString(exitLabel, labelFont, textBrush, x2 + 5, y2 + (trade.IsBuy ? 10 : -28));
        }
    }

    private bool IsSelectedSignal(SignalMarker signal, Candle candle)
    {
        return _selectedSignal is not null
            && _selectedSignal.Signal.Time == signal.Time
            && _selectedSignal.Signal.Symbol.Equals(signal.Symbol, StringComparison.OrdinalIgnoreCase)
            && _selectedSignal.Signal.Timeframe.Equals(signal.Timeframe, StringComparison.OrdinalIgnoreCase)
            && _selectedSignal.Candle.Time == candle.Time;
    }

    private SelectedSignal? HitTestSignal(Point location)
    {
        foreach (var hitBox in _signalHitBoxes.AsEnumerable().Reverse())
        {
            if (hitBox.Bounds.Contains(location))
            {
                return new SelectedSignal(hitBox.Signal, hitBox.Candle);
            }
        }
        return null;
    }

    private static int FindNearestCandleIndex(IReadOnlyList<Candle> candles, DateTime time)
    {
        var best = -1;
        var bestDistance = TimeSpan.MaxValue;
        for (var i = 0; i < candles.Count; i++)
        {
            var distance = (candles[i].Time - time).Duration();
            if (distance < bestDistance)
            {
                bestDistance = distance;
                best = i;
            }
        }
        return bestDistance <= TimeSpan.FromDays(1) ? best : -1;
    }

    private static void DrawArrow(Graphics g, float x, float y, bool isBuy, Color color, bool selected)
    {
        var half = selected ? 10f : 7f;
        var tip = selected ? 13f : 9f;
        var baseOffset = selected ? 7f : 5f;
        var points = isBuy
            ? new[]
            {
                new PointF(x, y - tip),
                new PointF(x - half, y + baseOffset),
                new PointF(x + half, y + baseOffset),
            }
            : new[]
            {
                new PointF(x, y + tip),
                new PointF(x - half, y - baseOffset),
                new PointF(x + half, y - baseOffset),
            };

        using var brush = new SolidBrush(color);
        using var outline = new Pen(selected ? Color.FromArgb(250, 204, 21) : Color.White, selected ? 2f : 1f);
        g.FillPolygon(brush, points);
        g.DrawPolygon(outline, points);
    }

    private void DrawAverageLine(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles, double min, double max, int period, Color color)
    {
        if (candles.Count < period)
        {
            return;
        }

        var values = _movingAverageMode == MovingAverageMode.Exponential
            ? ExponentialAverage(candles, period)
            : SimpleAverage(candles, period);
        var slots = Math.Max(1, candles.Count + _rightMarginCandles);
        var candleSlot = plot.Width / slots;
        using var pen = new Pen(color, 1.4f);
        PointF? previous = null;
        for (var i = 0; i < values.Length; i++)
        {
            if (!values[i].HasValue)
            {
                previous = null;
                continue;
            }

            var x = plot.Left + i * candleSlot + candleSlot / 2f;
            var y = PriceToY(values[i]!.Value, plot, min, max);
            var point = new PointF(x, y);
            if (previous.HasValue)
            {
                g.DrawLine(pen, previous.Value, point);
            }
            previous = point;
        }
    }

    private static double?[] SimpleAverage(IReadOnlyList<Candle> candles, int period)
    {
        var result = new double?[candles.Count];
        var sum = 0.0;
        for (var i = 0; i < candles.Count; i++)
        {
            sum += candles[i].Close;
            if (i >= period)
            {
                sum -= candles[i - period].Close;
            }
            if (i >= period - 1)
            {
                result[i] = sum / period;
            }
        }
        return result;
    }

    private static double?[] ExponentialAverage(IReadOnlyList<Candle> candles, int period)
    {
        var result = new double?[candles.Count];
        var multiplier = 2.0 / (period + 1);
        var seed = 0.0;
        for (var i = 0; i < candles.Count; i++)
        {
            if (i < period)
            {
                seed += candles[i].Close;
                if (i == period - 1)
                {
                    result[i] = seed / period;
                }
                continue;
            }
            result[i] = (candles[i].Close - result[i - 1]!.Value) * multiplier + result[i - 1]!.Value;
        }
        return result;
    }

    private void DrawPriceAxis(Graphics g, RectangleF plot, double min, double max)
    {
        using var brush = new SolidBrush(ForeColor);
        for (var i = 0; i <= 6; i++)
        {
            var value = max - (max - min) * i / 6.0;
            var y = PriceToY(value, plot, min, max);
            g.DrawString(value.ToString("0.#####"), Font, brush, plot.Right + 8, y - 8);
        }
    }

    private void DrawSimulatedOrder(Graphics g, RectangleF plot, double min, double max)
    {
        if (_simulatedOrder is null)
        {
            return;
        }

        foreach (var level in SimulationLevels())
        {
            var y = PriceToY(level.Price, plot, min, max);
            if (y < plot.Top - 20 || y > plot.Bottom + 20)
            {
                continue;
            }

            var isEntry = level.Name == "Entrada";
            using var pen = new Pen(level.Color, isEntry ? 2.8f : level.IsDashed ? 1.2f : 1.8f);
            if (level.IsDashed)
            {
                pen.DashStyle = DashStyle.Dash;
            }
            g.DrawLine(pen, plot.Left, y, plot.Right, y);
            DrawLineLabel(g, plot, y, level);
        }
    }

    private void DrawSimulationPrice(Graphics g, RectangleF plot, double min, double max)
    {
        if (_simulatedOrder is null || !_simulationPrice.HasValue)
        {
            return;
        }
        var y = PriceToY(_simulationPrice.Value, plot, min, max);
        using var pen = new Pen(Color.FromArgb(250, 204, 21), 1.8f);
        g.DrawLine(pen, plot.Left, y, plot.Right, y);
        var pnl = SimulatedPnlInUnits(_simulationPrice.Value);
        var text = $"{pnl:+0.0;-0.0;0.0} | {_simulationStatus}";
        using var font = new Font("Segoe UI", 8f, FontStyle.Bold);
        using var back = new SolidBrush(Color.FromArgb(220, 8, 13, 22));
        using var brush = new SolidBrush(pnl >= 0 ? Color.FromArgb(34, 197, 94) : Color.FromArgb(239, 68, 68));
        var size = g.MeasureString(text, font);
        var rect = new RectangleF(plot.Left + 8, y - 11, size.Width + 8, 20);
        g.FillRectangle(back, rect);
        g.DrawString(text, font, brush, rect.X + 4, rect.Y + 2);
    }

    private void DrawLineLabel(Graphics g, RectangleF plot, float y, SimulationLevel level)
    {
        var text = $"{level.Name} {level.Price:0.#####} ({level.Offset:0.#})";
        using var font = new Font("Segoe UI", 8f, FontStyle.Bold);
        var size = g.MeasureString(text, font);
        var rect = new RectangleF(plot.Right - size.Width - 8, y - 11, size.Width + 7, 20);
        using var back = new SolidBrush(Color.FromArgb(210, 8, 13, 22));
        using var brush = new SolidBrush(level.Color);
        using var border = new Pen(level.Color);
        g.FillRectangle(back, rect);
        g.DrawRectangle(border, rect.X, rect.Y, rect.Width, rect.Height);
        g.DrawString(text, font, brush, rect.X + 4, rect.Y + 2);
    }

    private IEnumerable<SimulationLevel> SimulationLevels()
    {
        if (_simulatedOrder is null)
        {
            yield break;
        }

        var settings = _simulatedOrder.Settings;
        var step = SimulationStep(_simulatedOrder, settings);
        var direction = _simulatedOrder.IsBuy ? 1.0 : -1.0;
        yield return new SimulationLevel("Entrada", _simulatedOrder.EntryPrice, 0.0, Color.FromArgb(255, 255, 255), false);

        if (settings.UseStopLoss)
        {
            var offset = (double)settings.StopLoss;
            yield return new SimulationLevel("SL", _simulatedOrder.EntryPrice - direction * offset * step, -offset, Color.FromArgb(239, 68, 68), false);
        }

        if (settings.UseTakeProfit)
        {
            var offset = (double)settings.TakeProfit;
            yield return new SimulationLevel("TP", _simulatedOrder.EntryPrice + direction * offset * step, offset, Color.FromArgb(34, 197, 94), false);
        }

        if (settings.UseTrailing)
        {
            var activation = (double)settings.TrailingActivation;
            var distance = (double)settings.TrailingDistance;
            yield return new SimulationLevel("Trail ativo", _simulatedOrder.EntryPrice + direction * activation * step, activation, Color.FromArgb(56, 189, 248), true);
            var trailPrice = _activeTrailingStop ?? _simulatedOrder.EntryPrice - direction * distance * step;
            yield return new SimulationLevel("Trail dist.", trailPrice, SimulatedPnlInUnits(trailPrice), Color.FromArgb(250, 204, 21), true);
        }
    }

    private void ResetSimulationCursor(DateTime time)
    {
        _simulationCandleIndex = Math.Max(0, _candles.FindIndex(candle => candle.Time >= time));
        if (_simulationCandleIndex < 0)
        {
            _simulationCandleIndex = _candles.Count > 0 ? _candles.Count - 1 : -1;
        }
        _simulationPhase = 0;
        _simulationPrice = _simulatedOrder?.EntryPrice;
        _activeTrailingStop = null;
        _simulationStatus = "pronto";
    }

    private void UpdateTrailingStop(double price)
    {
        if (_simulatedOrder is null || !_simulatedOrder.Settings.UseTrailing)
        {
            return;
        }

        var settings = _simulatedOrder.Settings;
        var step = SimulationStep(_simulatedOrder, settings);
        var activation = (double)settings.TrailingActivation * step;
        var distance = (double)settings.TrailingDistance * step;
        var favorable = _simulatedOrder.IsBuy
            ? price - _simulatedOrder.EntryPrice
            : _simulatedOrder.EntryPrice - price;
        if (favorable < activation)
        {
            return;
        }

        var candidate = _simulatedOrder.IsBuy ? price - distance : price + distance;
        _activeTrailingStop = _activeTrailingStop is null
            ? candidate
            : _simulatedOrder.IsBuy
                ? Math.Max(_activeTrailingStop.Value, candidate)
                : Math.Min(_activeTrailingStop.Value, candidate);
    }

    private bool ShouldStopSimulation(double price, out string reason)
    {
        reason = "";
        if (_simulatedOrder is null)
        {
            return false;
        }

        foreach (var level in SimulationLevels())
        {
            if (level.Name == "Entrada" || level.Name == "Trail ativo")
            {
                continue;
            }
            var hit = _simulatedOrder.IsBuy ? price <= level.Price : price >= level.Price;
            if (level.Name == "TP")
            {
                hit = _simulatedOrder.IsBuy ? price >= level.Price : price <= level.Price;
            }
            if (hit)
            {
                reason = level.Name;
                return true;
            }
        }
        return false;
    }

    private double SimulatedPnlInUnits(double price)
    {
        if (_simulatedOrder is null)
        {
            return 0.0;
        }
        var step = SimulationStep(_simulatedOrder, _simulatedOrder.Settings);
        var raw = _simulatedOrder.IsBuy
            ? price - _simulatedOrder.EntryPrice
            : _simulatedOrder.EntryPrice - price;
        return raw / step;
    }

    private static double SimulationStep(SimulatedOrder order, SimulationSettings settings)
    {
        var point = settings.Unit == SimulationUnit.Points
            ? PointSize(order)
            : PipSize(order);
        return Math.Max(point, 0.00000001);
    }

    private static double PointSize(SimulatedOrder order)
    {
        if (order.PointValue > 0)
        {
            return order.PointValue;
        }
        return Math.Pow(10, -Math.Max(0, Math.Min(8, order.Decimals)));
    }

    private static double PipSize(SimulatedOrder order)
    {
        var point = PointSize(order);
        return order.Decimals is 3 or 5 ? point * 10.0 : point;
    }

    private void DrawTimeAxis(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles)
    {
        using var brush = new SolidBrush(ForeColor);
        var steps = Math.Min(7, candles.Count);
        for (var i = 0; i < steps; i++)
        {
            var idx = (int)Math.Round(i * (candles.Count - 1) / Math.Max(1.0, steps - 1));
            var slots = Math.Max(1, candles.Count + _rightMarginCandles);
            var x = plot.Left + plot.Width * idx / slots;
            var text = candles[idx].Time.ToString("dd/MM HH:mm");
            g.DrawString(text, Font, brush, x - 34, plot.Bottom + 10);
        }
    }

    private void DrawCrosshair(Graphics g, RectangleF plot, IReadOnlyList<Candle> candles, double min, double max)
    {
        if (!_mouse.HasValue || !plot.Contains(_mouse.Value))
        {
            return;
        }

        using var pen = new Pen(Color.FromArgb(130, 148, 163), 1f) { DashStyle = DashStyle.Dash };
        g.DrawLine(pen, _mouse.Value.X, plot.Top, _mouse.Value.X, plot.Bottom);
        g.DrawLine(pen, plot.Left, _mouse.Value.Y, plot.Right, _mouse.Value.Y);

        var slots = Math.Max(1, candles.Count + _rightMarginCandles);
        var idx = Math.Clamp((int)Math.Floor((_mouse.Value.X - plot.Left) / Math.Max(1, plot.Width) * slots), 0, candles.Count - 1);
        var candle = candles[idx];
        var price = max - ((_mouse.Value.Y - plot.Top) / plot.Height) * (max - min);
        using var brush = new SolidBrush(Color.White);
        g.DrawString($"{candle.Symbol} {candle.Time:yyyy-MM-dd HH:mm}  O {candle.Open:0.#####} H {candle.High:0.#####} L {candle.Low:0.#####} C {candle.Close:0.#####} | {price:0.#####}", Font, brush, 12, 10);
    }

    private void DrawCentered(Graphics g, string text)
    {
        using var brush = new SolidBrush(ForeColor);
        var size = g.MeasureString(text, Font);
        g.DrawString(text, Font, brush, (Width - size.Width) / 2f, (Height - size.Height) / 2f);
    }

    private static float PriceToY(double price, RectangleF plot, double min, double max)
    {
        return plot.Bottom - (float)((price - min) / Math.Max(0.00000001, max - min) * plot.Height);
    }

    private enum DragMode
    {
        None,
        TimePan,
        PriceScale,
        PricePan,
    }
}

internal sealed record SimulationLevel(string Name, double Price, double Offset, Color Color, bool IsDashed);
internal sealed record SignalHitBox(RectangleF Bounds, SignalMarker Signal, Candle Candle);

public enum MovingAverageMode
{
    None,
    Simple,
    Exponential,
}
