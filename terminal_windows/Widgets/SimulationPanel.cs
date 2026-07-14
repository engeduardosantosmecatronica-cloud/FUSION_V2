using System.Drawing;
using System.Windows.Forms;
using FusionTerminalWindows.Models;
using FusionTerminalWindows.Theme;

namespace FusionTerminalWindows.Widgets;

public sealed class SimulationPanel : UserControl
{
    private const int ComboWidth = 158;
    private const int NumericWidth = 76;
    private const int RowWidth = 280;
    private const int RowHeight = 30;
    private const int LabelWidth = 94;
    private const int SliderLabelWidth = 94;
    private const int CheckWidth = 82;
    private const int BlockTitleWidth = 230;
    private readonly ComboBox _strategyCombo = Combo();
    private readonly ComboBox _sideCombo = Combo();
    private readonly ComboBox _unitCombo = Combo();
    private readonly NumericUpDown _lotInput = Numeric(0.01m, 100m, 0.01m, 2, 0.01m);
    private readonly CheckBox _slCheck = Check("SL", true);
    private readonly NumericUpDown _slInput = Numeric(1m, 10000m, 1m, 0, 120m);
    private readonly CheckBox _tpCheck = Check("TP", true);
    private readonly NumericUpDown _tpInput = Numeric(1m, 10000m, 1m, 0, 240m);
    private readonly CheckBox _trailingCheck = Check("Ativa", true);
    private readonly NumericUpDown _trailingActivationInput = Numeric(1m, 10000m, 1m, 0, 80m);
    private readonly NumericUpDown _trailingDistanceInput = Numeric(1m, 10000m, 1m, 0, 40m);
    private readonly NumericUpDown _trailingStepInput = Numeric(1m, 1000m, 1m, 0, 5m);
    private readonly TrackBar _speedTrack = Track();

    public event EventHandler<SimulationSettings>? SettingsChanged;
    public event EventHandler? StartRequested;
    public event EventHandler? PauseRequested;
    public event EventHandler? StopRequested;

    public SimulationPanel()
    {
        Dock = DockStyle.Fill;
        BackColor = TerminalTheme.Panel;
        Padding = new Padding(8);

        var layout = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            BackColor = TerminalTheme.Panel,
            ColumnCount = 4,
            RowCount = 1,
        };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 24));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 25));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 31));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 20));

        layout.Controls.Add(BuildOrderBlock(), 0, 0);
        layout.Controls.Add(BuildRiskBlock(), 1, 0);
        layout.Controls.Add(BuildTrailingBlock(), 2, 0);
        layout.Controls.Add(BuildActionBlock(), 3, 0);
        Controls.Add(layout);
        BindChanges(this);
    }

    public SimulationSettings CurrentSettings()
    {
        return new SimulationSettings(
            _strategyCombo.Text,
            ParseSide(_sideCombo.Text),
            _lotInput.Value,
            _slCheck.Checked,
            _slInput.Value,
            _tpCheck.Checked,
            _tpInput.Value,
            _unitCombo.Text == "Pontos" ? SimulationUnit.Points : SimulationUnit.Pips,
            _trailingCheck.Checked,
            _trailingActivationInput.Value,
            _trailingDistanceInput.Value,
            _trailingStepInput.Value,
            _speedTrack.Value
        );
    }

    private Control BuildOrderBlock()
    {
        var block = Block("Ordem");
        AddComboRow(block, "Estrategia", _strategyCombo, new[] { "Cruzamento", "Inside bar", "Breakout", "Fusion sinal" });
        AddComboRow(block, "Lado", _sideCombo, new[] { "Auto", "BUY", "SELL" });
        AddNumericRow(block, "Lote", _lotInput);
        return block;
    }

    private Control BuildRiskBlock()
    {
        var block = Block("Risco");
        AddCheckNumericRow(block, _slCheck, _slInput);
        AddCheckNumericRow(block, _tpCheck, _tpInput);
        AddComboRow(block, "Unidade", _unitCombo, new[] { "Pips", "Pontos" });
        return block;
    }

    private Control BuildTrailingBlock()
    {
        var block = Block("Trailing");
        AddCheckNumericRow(block, _trailingCheck, _trailingActivationInput);
        AddNumericRow(block, "Dist.", _trailingDistanceInput);
        AddNumericRow(block, "Passo", _trailingStepInput);
        AddTrackRow(block, "Veloc.", _speedTrack);
        return block;
    }

    private Control BuildActionBlock()
    {
        var block = Block("Controle");
        var buttons = new FlowLayoutPanel
        {
            Dock = DockStyle.Top,
            AutoSize = true,
            WrapContents = true,
            BackColor = TerminalTheme.Panel,
        };
        var start = ActionButton("Iniciar", TerminalTheme.Positive);
        var pause = ActionButton("Pausar", TerminalTheme.Primary);
        var stop = ActionButton("Parar", TerminalTheme.Negative);
        start.Click += (_, _) => StartRequested?.Invoke(this, EventArgs.Empty);
        pause.Click += (_, _) => PauseRequested?.Invoke(this, EventArgs.Empty);
        stop.Click += (_, _) => StopRequested?.Invoke(this, EventArgs.Empty);
        buttons.Controls.Add(start);
        buttons.Controls.Add(pause);
        buttons.Controls.Add(stop);
        buttons.Controls.Add(ActionButton("Reset", TerminalTheme.Border));
        block.Controls.Add(buttons);

        var hint = new Label
        {
            Dock = DockStyle.Top,
            Height = 48,
            Text = "Clique em uma seta no grafico para carregar a ordem simulada.",
            ForeColor = TerminalTheme.Muted,
            Font = new Font("Segoe UI", 8.5f),
            Padding = new Padding(0, 8, 0, 0),
        };
        block.Controls.Add(hint);
        return block;
    }

    private void BindChanges(Control parent)
    {
        foreach (Control control in parent.Controls)
        {
            if (control is ComboBox combo)
            {
                combo.SelectedIndexChanged += (_, _) => SettingsChanged?.Invoke(this, CurrentSettings());
            }
            else if (control is NumericUpDown numeric)
            {
                numeric.ValueChanged += (_, _) => SettingsChanged?.Invoke(this, CurrentSettings());
            }
            else if (control is CheckBox check)
            {
                check.CheckedChanged += (_, _) => SettingsChanged?.Invoke(this, CurrentSettings());
            }
            else if (control is TrackBar track)
            {
                track.ValueChanged += (_, _) => SettingsChanged?.Invoke(this, CurrentSettings());
            }
            if (control.HasChildren)
            {
                BindChanges(control);
            }
        }
    }

    private static FlowLayoutPanel Block(string title)
    {
        var block = new FlowLayoutPanel
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.TopDown,
            WrapContents = false,
            AutoScroll = true,
            BackColor = TerminalTheme.Panel,
            Padding = new Padding(6),
            Margin = new Padding(3),
        };
        block.Paint += (_, e) =>
        {
            using var pen = new Pen(TerminalTheme.Border);
            e.Graphics.DrawRectangle(pen, 0, 0, block.Width - 1, block.Height - 1);
        };
        block.Controls.Add(new Label
        {
            Text = title,
            Width = BlockTitleWidth,
            Height = 22,
            ForeColor = TerminalTheme.Text,
            Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
        });
        return block;
    }

    private static void AddComboRow(Control parent, string label, ComboBox combo, string[] items)
    {
        combo.Items.AddRange(items);
        combo.SelectedIndex = 0;
        parent.Controls.Add(Row(label, combo));
    }

    private static void AddCheckNumericRow(Control parent, CheckBox check, NumericUpDown numeric, string? note = null)
    {
        var panel = RowPanel();
        panel.Controls.Add(check);
        panel.Controls.Add(numeric);
        if (!string.IsNullOrWhiteSpace(note))
        {
            panel.Controls.Add(new Label
            {
                Text = note,
                Width = 56,
                ForeColor = TerminalTheme.Muted,
                Padding = new Padding(4, 5, 0, 0),
            });
        }
        parent.Controls.Add(panel);
    }

    private static void AddNumericRow(Control parent, string label, NumericUpDown numeric)
    {
        parent.Controls.Add(Row(label, numeric));
    }

    private static void AddTrackRow(Control parent, string label, TrackBar track)
    {
        parent.Controls.Add(Row(label, track, SliderLabelWidth));
    }

    private static ComboBox Combo()
    {
        return new ComboBox
        {
            DropDownStyle = ComboBoxStyle.DropDownList,
            Width = ComboWidth,
            BackColor = TerminalTheme.Background,
            ForeColor = TerminalTheme.Text,
        };
    }

    private static CheckBox Check(string text, bool isChecked)
    {
        return new CheckBox
        {
            Text = text,
            Checked = isChecked,
            Width = CheckWidth,
            ForeColor = TerminalTheme.Text,
            BackColor = TerminalTheme.Panel,
        };
    }

    private static TrackBar Track()
    {
        return new TrackBar
        {
            Width = 138,
            Minimum = 1,
            Maximum = 10,
            Value = 5,
            TickStyle = TickStyle.None,
            BackColor = TerminalTheme.Panel,
        };
    }

    private static NumericUpDown Numeric(decimal min, decimal max, decimal increment, int decimals, decimal value)
    {
        return new NumericUpDown
        {
            Width = NumericWidth,
            Minimum = min,
            Maximum = max,
            Increment = increment,
            DecimalPlaces = decimals,
            Value = value,
            BackColor = TerminalTheme.Background,
            ForeColor = TerminalTheme.Text,
        };
    }

    private static Control Row(string label, Control input, int labelWidth = LabelWidth)
    {
        var panel = RowPanel();
        panel.Controls.Add(new Label
        {
            Text = label,
            Width = labelWidth,
            ForeColor = TerminalTheme.Muted,
            Padding = new Padding(0, 5, 0, 0),
        });
        panel.Controls.Add(input);
        return panel;
    }

    private static FlowLayoutPanel RowPanel()
    {
        return new FlowLayoutPanel
        {
            Width = RowWidth,
            Height = RowHeight,
            WrapContents = false,
            BackColor = TerminalTheme.Panel,
            Margin = new Padding(0, 1, 0, 1),
        };
    }

    private static Button ActionButton(string text, Color color)
    {
        return new Button
        {
            Text = text,
            Width = 70,
            Height = 26,
            FlatStyle = FlatStyle.Flat,
            BackColor = color,
            ForeColor = Color.White,
            Margin = new Padding(0, 0, 6, 6),
        };
    }

    private static SimulationSide ParseSide(string value)
    {
        return value switch
        {
            "BUY" => SimulationSide.Buy,
            "SELL" => SimulationSide.Sell,
            _ => SimulationSide.Auto,
        };
    }
}

