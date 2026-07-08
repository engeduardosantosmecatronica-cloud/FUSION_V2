using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public enum EventTableMode
{
    Signals,
    Orders,
    Layers,
    Events,
}

public sealed class EventTablePanel : UserControl
{
    private readonly string _root;
    private readonly EventTableMode _mode;
    private readonly Label _source = new();
    private readonly DataGridView _grid = new();

    public EventTablePanel(string root, EventTableMode mode)
    {
        _root = root;
        _mode = mode;
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(8);

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 2,
            ColumnCount = 1,
            BackColor = TerminalTheme.Panel,
        };
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 26));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        _source.Dock = DockStyle.Fill;
        _source.ForeColor = TerminalTheme.Muted;
        _source.Font = new Font("Segoe UI", 8.5f);

        _grid.Dock = DockStyle.Fill;
        _grid.BackgroundColor = TerminalTheme.Background;
        _grid.BorderStyle = BorderStyle.None;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.AllowUserToResizeRows = false;
        _grid.ReadOnly = true;
        _grid.RowHeadersVisible = false;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        _grid.ColumnHeadersHeightSizeMode = DataGridViewColumnHeadersHeightSizeMode.DisableResizing;
        _grid.ColumnHeadersHeight = 24;
        _grid.EnableHeadersVisualStyles = false;
        _grid.GridColor = TerminalTheme.Border;
        _grid.DefaultCellStyle.BackColor = TerminalTheme.Background;
        _grid.DefaultCellStyle.ForeColor = TerminalTheme.Text;
        _grid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(30, 58, 88);
        _grid.DefaultCellStyle.SelectionForeColor = TerminalTheme.Text;
        _grid.ColumnHeadersDefaultCellStyle.BackColor = TerminalTheme.PanelAlt;
        _grid.ColumnHeadersDefaultCellStyle.ForeColor = TerminalTheme.Text;
        _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 8.5f, FontStyle.Bold);

        layout.Controls.Add(_source, 0, 0);
        layout.Controls.Add(_grid, 0, 1);
        Controls.Add(layout);
    }

    public void UpdateSymbol(string symbol)
    {
        var source = FindSource();
        _grid.Columns.Clear();
        _grid.Rows.Clear();
        if (string.IsNullOrWhiteSpace(source))
        {
            _source.Text = $"{Title()} | sem fonte";
            return;
        }

        var rows = LoadRows(source, symbol).ToList();
        _source.Text = $"{Title()} | {symbol} | {Path.GetFileName(source)} | {rows.Count} registros";
        var columns = Columns();
        foreach (var column in columns)
        {
            _grid.Columns.Add(column, column);
        }

        foreach (var row in rows.TakeLast(80).Reverse())
        {
            _grid.Rows.Add(columns.Select(column => row.TryGetValue(column, out var value) ? value : "").ToArray());
        }
    }

    private string Title()
    {
        return _mode switch
        {
            EventTableMode.Signals => "Sinais",
            EventTableMode.Orders => "Ordens",
            EventTableMode.Layers => "Camadas",
            _ => "Eventos",
        };
    }

    private string[] Columns()
    {
        return _mode switch
        {
            EventTableMode.Signals => new[] { "timestamp", "timeframe", "direction", "strategy", "status", "reason" },
            EventTableMode.Orders => new[] { "timestamp", "type", "timeframe", "direction", "status", "reason" },
            EventTableMode.Layers => new[] { "timestamp", "timeframe", "engine", "engine_state", "engine_score", "engine_confidence", "risk_flag" },
            _ => new[] { "timestamp", "type", "timeframe", "direction", "status", "reason" },
        };
    }

    private string FindSource()
    {
        if (_mode == EventTableMode.Layers)
        {
            var dir = Path.Combine(_root, "reports", "shadow_engine_report");
            return Directory.Exists(dir)
                ? Directory.EnumerateFiles(dir, "shadow_engine_engines_*.csv").OrderByDescending(File.GetLastWriteTime).FirstOrDefault() ?? ""
                : "";
        }

        var eventDir = Path.Combine(_root, "reports", "event_bus");
        return Directory.Exists(eventDir)
            ? Directory.EnumerateFiles(eventDir, "event_bus_events_*.csv").OrderByDescending(File.GetLastWriteTime).FirstOrDefault() ?? ""
            : "";
    }

    private IEnumerable<Dictionary<string, string>> LoadRows(string path, string symbol)
    {
        using var reader = new StreamReader(path);
        var header = reader.ReadLine();
        if (string.IsNullOrWhiteSpace(header))
        {
            yield break;
        }

        var headers = SplitCsv(header);
        var recent = new Queue<string>();
        while (!reader.EndOfStream)
        {
            var line = reader.ReadLine();
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }
            recent.Enqueue(line);
            if (recent.Count > 3000)
            {
                recent.Dequeue();
            }
        }

        foreach (var line in recent)
        {
            var parts = SplitCsv(line);
            var row = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < headers.Count && i < parts.Count; i++)
            {
                row[headers[i]] = parts[i];
            }

            if (!MatchSymbol(row, symbol) || !MatchMode(row))
            {
                continue;
            }
            yield return row;
        }
    }

    private static bool MatchSymbol(Dictionary<string, string> row, string symbol)
    {
        return row.TryGetValue("symbol", out var value)
            && value.Equals(symbol, StringComparison.OrdinalIgnoreCase);
    }

    private bool MatchMode(Dictionary<string, string> row)
    {
        if (_mode == EventTableMode.Layers)
        {
            return true;
        }
        row.TryGetValue("type", out var type);
        return _mode switch
        {
            EventTableMode.Signals => type is "SIGNAL" or "DECISION",
            EventTableMode.Orders => type is "ORDER_REQUEST" or "ORDER_RESULT" or "POSITION_UPDATE" or "ACCOUNT_UPDATE",
            EventTableMode.Events => true,
            _ => true,
        };
    }

    private static List<string> SplitCsv(string line)
    {
        var values = new List<string>();
        var current = "";
        var inQuotes = false;
        for (var i = 0; i < line.Length; i++)
        {
            var ch = line[i];
            if (ch == '"')
            {
                if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                {
                    current += '"';
                    i++;
                }
                else
                {
                    inQuotes = !inQuotes;
                }
            }
            else if (ch == ',' && !inQuotes)
            {
                values.Add(current);
                current = "";
            }
            else
            {
                current += ch;
            }
        }
        values.Add(current);
        return values;
    }
}
