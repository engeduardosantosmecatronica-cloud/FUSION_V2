using System;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class ProbabilityPanel : UserControl
{
    private static readonly string[] Timeframes = { "M5", "M15", "M30", "H1", "H4", "D1" };
    private readonly string _root;
    private readonly TableLayoutPanel _rows;
    private readonly Label _source;

    public ProbabilityPanel(string root)
    {
        _root = root;
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(10);

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            ColumnCount = 1,
            RowCount = 2,
        };
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        _source = new Label
        {
            Dock = DockStyle.Top,
            Height = 28,
            ForeColor = TerminalTheme.Muted,
            Text = "Aguardando ativo...",
        };
        _rows = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            ColumnCount = 1,
            RowCount = 0,
            AutoScroll = true,
        };

        layout.Controls.Add(_source, 0, 0);
        layout.Controls.Add(_rows, 0, 1);
        Controls.Add(layout);
    }

    public void UpdateSymbol(string symbol)
    {
        _rows.SuspendLayout();
        _rows.Controls.Clear();
        _rows.RowStyles.Clear();

        var sourceFile = FindLatestSource();
        if (string.IsNullOrWhiteSpace(sourceFile))
        {
            _source.Text = "Sem relatorio de probabilidades.";
            AddMessage("Nenhum arquivo shadow_engine_events encontrado.");
            _rows.ResumeLayout();
            return;
        }

        var rows = LoadLatestRows(sourceFile, symbol);
        _source.Text = $"{symbol} | fonte: {Path.GetFileName(sourceFile)}";

        foreach (var timeframe in Timeframes)
        {
            rows.TryGetValue(timeframe, out var row);
            AddProbabilityCard(timeframe, row);
        }
        _rows.ResumeLayout();
    }

    private string FindLatestSource()
    {
        var dir = Path.Combine(_root, "reports", "shadow_engine_report");
        if (!Directory.Exists(dir))
        {
            return "";
        }

        return Directory.EnumerateFiles(dir, "shadow_engine_events_*tail500.csv")
            .Concat(Directory.EnumerateFiles(dir, "shadow_engine_events_*tail300.csv"))
            .Concat(Directory.EnumerateFiles(dir, "shadow_engine_events_*.csv"))
            .OrderByDescending(File.GetLastWriteTime)
            .FirstOrDefault() ?? "";
    }

    private static Dictionary<string, ProbabilityRow> LoadLatestRows(string path, string symbol)
    {
        var result = new Dictionary<string, ProbabilityRow>(StringComparer.OrdinalIgnoreCase);
        using var reader = new StreamReader(path);
        var header = reader.ReadLine();
        if (string.IsNullOrWhiteSpace(header))
        {
            return result;
        }

        var map = SplitCsv(header)
            .Select((name, index) => new { name, index })
            .ToDictionary(item => item.name, item => item.index, StringComparer.OrdinalIgnoreCase);

        while (!reader.EndOfStream)
        {
            var line = reader.ReadLine();
            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }
            var parts = SplitCsv(line);
            if (!Value(parts, map, "symbol").Equals(symbol, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }

            var row = new ProbabilityRow(
                Value(parts, map, "timestamp"),
                Value(parts, map, "timeframe"),
                Value(parts, map, "side"),
                Parse(Value(parts, map, "p_buy")),
                Parse(Value(parts, map, "p_sell")),
                Value(parts, map, "decision"),
                Value(parts, map, "reason"),
                Parse(Value(parts, map, "tradeability_score")),
                Parse(Value(parts, map, "conflict_score"))
            );
            if (!string.IsNullOrWhiteSpace(row.Timeframe))
            {
                result[row.Timeframe] = row;
            }
        }
        return result;
    }

    private void AddProbabilityCard(string timeframe, ProbabilityRow? row)
    {
        var panel = new TableLayoutPanel
        {
            Dock = DockStyle.Top,
            Height = 76,
            ColumnCount = 4,
            RowCount = 2,
            BackColor = TerminalTheme.Background,
            Margin = new Padding(0, 0, 0, 8),
            Padding = new Padding(8),
        };
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 46));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 38));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 32));
        panel.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 30));

        var timeframeLabel = MakeLabel(timeframe, TerminalTheme.Text, 10f, FontStyle.Bold);
        panel.Controls.Add(timeframeLabel, 0, 0);
        panel.SetRowSpan(timeframeLabel, 2);

        if (row is null)
        {
            var emptyLabel = MakeLabel("sem dados", TerminalTheme.Muted);
            panel.Controls.Add(emptyLabel, 1, 0);
            panel.SetColumnSpan(emptyLabel, 3);
        }
        else
        {
            var sideColor = row.Side.Equals("BUY", StringComparison.OrdinalIgnoreCase) ? TerminalTheme.Positive : TerminalTheme.Negative;
            panel.Controls.Add(MakeLabel($"BUY {row.PBuy:0.000}", TerminalTheme.Positive), 1, 0);
            panel.Controls.Add(MakeLabel($"SELL {row.PSell:0.000}", TerminalTheme.Negative), 2, 0);
            panel.Controls.Add(MakeLabel(row.Side, sideColor, 9f, FontStyle.Bold), 3, 0);
            panel.Controls.Add(MakeLabel($"trade {row.Tradeability:0.000}", TerminalTheme.Muted), 1, 1);
            panel.Controls.Add(MakeLabel($"conflito {row.Conflict:0.000}", TerminalTheme.Muted), 2, 1);
            panel.Controls.Add(MakeLabel(row.Decision, TerminalTheme.Muted), 3, 1);
            panel.Tag = row.Reason;
        }

        _rows.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        _rows.Controls.Add(panel);
    }

    private void AddMessage(string text)
    {
        _rows.Controls.Add(MakeLabel(text, TerminalTheme.Muted));
    }

    private static Label MakeLabel(string value, Color color, float size = 8.5f, FontStyle style = FontStyle.Regular)
    {
        return new Label
        {
            Text = string.IsNullOrWhiteSpace(value) ? "-" : value,
            Dock = DockStyle.Fill,
            AutoEllipsis = true,
            ForeColor = color,
            Font = new Font("Segoe UI", size, style),
            TextAlign = ContentAlignment.MiddleLeft,
        };
    }

    private static string Value(IReadOnlyList<string> parts, Dictionary<string, int> map, string name)
    {
        return map.TryGetValue(name, out var index) && index >= 0 && index < parts.Count
            ? parts[index]
            : "";
    }

    private static double Parse(string value)
    {
        return double.TryParse(value, NumberStyles.Float, CultureInfo.InvariantCulture, out var parsed)
            ? parsed
            : 0.0;
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

    private sealed record ProbabilityRow(
        string Timestamp,
        string Timeframe,
        string Side,
        double PBuy,
        double PSell,
        string Decision,
        string Reason,
        double Tradeability,
        double Conflict
    );
}
