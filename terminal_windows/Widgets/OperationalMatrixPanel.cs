using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Data;
using FusionTerminalWindows.Models;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class OperationalMatrixPanel : UserControl
{
    private static readonly string[] Timeframes = { "M5", "M15", "M30", "H1", "H4", "D1" };
    private readonly OperationalStatusLoader _loader;
    private readonly Label _source = new();
    private readonly Label _summary = new();
    private readonly DataGridView _grid = new();
    private IReadOnlyList<OperationalRow> _rows = Array.Empty<OperationalRow>();

    public OperationalMatrixPanel(string root)
    {
        _loader = new OperationalStatusLoader(root);
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(8);
        BuildUi();
        Reload();
    }

    public void Reload()
    {
        _rows = _loader.Load(out var source, out var reasonCounts);
        _source.Text = string.IsNullOrWhiteSpace(source)
            ? "Matriz operacional | sem fonte shadow_engine_events"
            : $"Matriz operacional | {Path.GetFileName(source)} | {_rows.Count} ativos";
        _summary.Text = reasonCounts.Count == 0
            ? "Resumo dos motivos acionaveis: -"
            : "Resumo dos motivos acionaveis: " + string.Join(" | ", reasonCounts.Select(item => $"{item.Key}:{item.Value}"));
        RenderRows(_rows);
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
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 30));
        shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));

        var top = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.PanelAlt,
            Padding = new Padding(8, 5, 8, 3),
            WrapContents = false,
        };
        var reload = new Button
        {
            Text = "Recarregar",
            Width = 88,
            Height = 24,
            FlatStyle = FlatStyle.Flat,
            BackColor = TerminalTheme.Panel,
            ForeColor = TerminalTheme.Text,
        };
        reload.Click += (_, _) => Reload();
        _source.AutoSize = true;
        _source.ForeColor = TerminalTheme.Muted;
        _source.Padding = new Padding(8, 4, 0, 0);
        top.Controls.Add(reload);
        top.Controls.Add(_source);

        ConfigureGrid();
        _summary.Dock = DockStyle.Fill;
        _summary.ForeColor = TerminalTheme.Muted;
        _summary.Font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
        _summary.Padding = new Padding(8, 8, 8, 0);
        _summary.AutoEllipsis = true;

        shell.Controls.Add(top, 0, 0);
        shell.Controls.Add(_grid, 0, 1);
        shell.Controls.Add(_summary, 0, 2);
        Controls.Add(shell);
    }

    private void ConfigureGrid()
    {
        _grid.Dock = DockStyle.Fill;
        _grid.BackgroundColor = TerminalTheme.Background;
        _grid.BorderStyle = BorderStyle.None;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.ReadOnly = true;
        _grid.RowHeadersVisible = false;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        _grid.EnableHeadersVisualStyles = false;
        _grid.GridColor = TerminalTheme.Border;
        _grid.DefaultCellStyle.BackColor = TerminalTheme.Background;
        _grid.DefaultCellStyle.ForeColor = TerminalTheme.Text;
        _grid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(30, 58, 88);
        _grid.ColumnHeadersDefaultCellStyle.BackColor = TerminalTheme.PanelAlt;
        _grid.ColumnHeadersDefaultCellStyle.ForeColor = TerminalTheme.Text;
        _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
        _grid.CellToolTipTextNeeded += (_, args) =>
        {
            if (args.RowIndex < 0 || args.RowIndex >= _rows.Count || args.ColumnIndex < 1 || args.ColumnIndex > Timeframes.Length)
            {
                return;
            }
            var tf = Timeframes[args.ColumnIndex - 1];
            if (_rows[args.RowIndex].Cells.TryGetValue(tf, out var cell))
            {
                args.ToolTipText = $"{_rows[args.RowIndex].Symbol} {tf} {cell.Side} {cell.Decision}\n{cell.Strategy}\n{cell.Reason}";
            }
        };
    }

    private void RenderRows(IReadOnlyList<OperationalRow> rows)
    {
        _grid.Columns.Clear();
        _grid.Rows.Clear();
        _grid.Columns.Add("symbol", "ATIVO");
        foreach (var timeframe in Timeframes)
        {
            _grid.Columns.Add(timeframe, timeframe);
        }
        _grid.Columns.Add("reasons", "MOTIVOS");
        _grid.Columns[0].FillWeight = 72;
        for (var i = 1; i <= Timeframes.Length; i++)
        {
            _grid.Columns[i].FillWeight = 76;
        }
        _grid.Columns[^1].FillWeight = 260;

        foreach (var row in rows)
        {
            var values = new List<string> { row.Symbol };
            values.AddRange(Timeframes.Select(tf => row.Cells.TryGetValue(tf, out var cell) ? CellText(cell) : "-/-"));
            values.Add(row.Reasons);
            var index = _grid.Rows.Add(values.ToArray());
            _grid.Rows[index].Cells[0].Style.Font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
            for (var col = 1; col <= Timeframes.Length; col++)
            {
                var tf = Timeframes[col - 1];
                if (!row.Cells.TryGetValue(tf, out var cell))
                {
                    _grid.Rows[index].Cells[col].Style.ForeColor = TerminalTheme.Muted;
                    continue;
                }
                var style = _grid.Rows[index].Cells[col].Style;
                style.ForeColor = CellForeColor(cell);
                style.BackColor = CellBackColor(cell);
                style.Font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
            }
            _grid.Rows[index].Cells[^1].Style.ForeColor = TerminalTheme.Muted;
        }
    }

    private static string CellText(OperationalCell cell)
    {
        var max = Math.Max(cell.PBuy, cell.PSell);
        if (cell.Side == "BUY")
        {
            return $"B:{max:0.000}";
        }
        if (cell.Side == "SELL")
        {
            return $"S:{max:0.000}";
        }
        return $"{cell.PBuy:0.000}/{cell.PSell:0.000}";
    }

    private static Color CellForeColor(OperationalCell cell)
    {
        if (cell.Side == "BUY")
        {
            return TerminalTheme.Positive;
        }
        if (cell.Side == "SELL")
        {
            return TerminalTheme.Negative;
        }
        return TerminalTheme.Muted;
    }

    private static Color CellBackColor(OperationalCell cell)
    {
        if (cell.Decision == "ALLOW")
        {
            return cell.Side == "BUY" ? Color.FromArgb(14, 58, 38) : Color.FromArgb(70, 24, 34);
        }
        if (cell.Decision == "BLOCK")
        {
            return Color.FromArgb(42, 31, 28);
        }
        return TerminalTheme.Background;
    }
}
