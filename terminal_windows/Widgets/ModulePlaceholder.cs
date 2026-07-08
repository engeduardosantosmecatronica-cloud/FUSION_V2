using System.Drawing;
using System.Windows.Forms;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class ModulePlaceholder : UserControl
{
    public ModulePlaceholder(string title, string description)
    {
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(12);

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 3,
            ColumnCount = 1,
            BackColor = TerminalTheme.Panel,
        };
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        var titleLabel = new Label
        {
            Text = title,
            Dock = DockStyle.Top,
            AutoSize = true,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI", 10.5f, FontStyle.Bold),
            Padding = new Padding(0, 0, 0, 8),
        };

        var descLabel = new Label
        {
            Text = description,
            Dock = DockStyle.Top,
            AutoSize = false,
            Height = 54,
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 9f, FontStyle.Regular),
        };

        var body = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Background,
        };
        body.Paint += (_, e) =>
        {
            using var pen = new Pen(TerminalTheme.Border);
            e.Graphics.DrawRectangle(pen, 0, 0, body.Width - 1, body.Height - 1);
        };

        layout.Controls.Add(titleLabel, 0, 0);
        layout.Controls.Add(descLabel, 0, 1);
        layout.Controls.Add(body, 0, 2);
        Controls.Add(layout);
    }
}
