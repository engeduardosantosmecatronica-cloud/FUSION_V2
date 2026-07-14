using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Text.RegularExpressions;
using System.Windows.Forms;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class ModuleCatalogPanel : UserControl
{
    private readonly ListBox _modules = new();
    private readonly FlowLayoutPanel _fields = new();
    private readonly Label _title = new();
    private readonly List<ModuleDefinition> _definitions = new();

    public ModuleCatalogPanel()
    {
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Background;
        Padding = new Padding(14);
        BuildLayout();
        LoadCatalog();
    }

    private void BuildLayout()
    {
        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
            ColumnCount = 2,
            RowCount = 2,
        };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 320));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 58));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var heading = new Label
        {
            Text = "CATALOGO DO FUSION CONTROL CENTER",
            Dock = DockStyle.Fill,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI Semibold", 15f, FontStyle.Bold),
            TextAlign = ContentAlignment.MiddleLeft,
            Padding = new Padding(10, 0, 0, 0),
        };
        layout.Controls.Add(heading, 0, 0);
        layout.SetColumnSpan(heading, 2);

        _modules.Dock = DockStyle.Fill;
        _modules.BackColor = TerminalTheme.Panel;
        _modules.ForeColor = TerminalTheme.Text;
        _modules.BorderStyle = BorderStyle.FixedSingle;
        _modules.Font = new Font("Segoe UI", 9.5f);
        _modules.ItemHeight = 28;
        _modules.SelectedIndexChanged += (_, _) => ShowSelectedModule();

        var detail = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(16),
            RowCount = 2,
            ColumnCount = 1,
        };
        detail.RowStyles.Add(new RowStyle(SizeType.Absolute, 48));
        detail.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        _title.Dock = DockStyle.Fill;
        _title.ForeColor = TerminalTheme.Primary;
        _title.Font = new Font("Segoe UI Semibold", 13f, FontStyle.Bold);
        _title.TextAlign = ContentAlignment.MiddleLeft;

        _fields.Dock = DockStyle.Fill;
        _fields.AutoScroll = true;
        _fields.FlowDirection = FlowDirection.TopDown;
        _fields.WrapContents = false;
        _fields.BackColor = TerminalTheme.Panel;

        detail.Controls.Add(_title, 0, 0);
        detail.Controls.Add(_fields, 0, 1);
        layout.Controls.Add(_modules, 0, 1);
        layout.Controls.Add(detail, 1, 1);
        Controls.Add(layout);
    }

    private void LoadCatalog()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "module_catalog.txt");
        if (!File.Exists(path))
        {
            _title.Text = "Catalogo indisponivel";
            return;
        }

        ModuleDefinition? current = null;
        foreach (var rawLine in File.ReadLines(path))
        {
            var line = rawLine.Trim();
            if (line.Length == 0) continue;
            if (line.StartsWith("Estrutura recomendada", StringComparison.OrdinalIgnoreCase)) break;

            if (Regex.IsMatch(line, @"^d+.s"))
            {
                current = new ModuleDefinition(line);
                _definitions.Add(current);
                continue;
            }

            current?.Fields.Add(line.TrimEnd('.'));
        }

        foreach (var definition in _definitions)
        {
            _modules.Items.Add(definition.Title);
        }

        if (_modules.Items.Count > 0) _modules.SelectedIndex = 0;
    }

    private void ShowSelectedModule()
    {
        if (_modules.SelectedIndex < 0 || _modules.SelectedIndex >= _definitions.Count) return;
        var module = _definitions[_modules.SelectedIndex];
        _title.Text = module.Title.ToUpperInvariant();
        _fields.SuspendLayout();
        _fields.Controls.Clear();

        foreach (var field in module.Fields)
        {
            var row = new TableLayoutPanel
            {
                Width = Math.Max(520, _fields.ClientSize.Width - 30),
                Height = 38,
                BackColor = TerminalTheme.PanelSoft,
                Margin = new Padding(0, 0, 0, 5),
                ColumnCount = 2,
                RowCount = 1,
            };
            row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 72));
            row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 28));
            row.Controls.Add(new Label
            {
                Text = field,
                Dock = DockStyle.Fill,
                ForeColor = TerminalTheme.Text,
                TextAlign = ContentAlignment.MiddleLeft,
                Padding = new Padding(10, 0, 4, 0),
                AutoEllipsis = true,
            }, 0, 0);
            row.Controls.Add(new Label
            {
                Text = "AGUARDANDO INTEGRACAO",
                Dock = DockStyle.Fill,
                ForeColor = TerminalTheme.Muted,
                Font = new Font("Segoe UI", 7.5f, FontStyle.Bold),
                TextAlign = ContentAlignment.MiddleRight,
                Padding = new Padding(4, 0, 10, 0),
            }, 1, 0);
            _fields.Controls.Add(row);
        }

        _fields.ResumeLayout();
    }

    private sealed class ModuleDefinition
    {
        public string Title { get; }
        public List<string> Fields { get; } = new();

        public ModuleDefinition(string title) => Title = title;
    }
}