using System;
using System.IO;
using System.Windows.Forms;

namespace FusionTerminalWindows;

internal static class Program
{
    private static readonly string StartupLog = Path.Combine(AppContext.BaseDirectory, "terminal_windows_startup.log");

    internal static void StartupTrace(string message)
    {
        try
        {
            File.AppendAllText(StartupLog, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} | {message}{Environment.NewLine}");
        }
        catch
        {
        }
    }

    [STAThread]
    private static void Main()
    {
        try
        {
            StartupTrace("Main start");
            ApplicationConfiguration.Initialize();
            StartupTrace("ApplicationConfiguration ok");
            Application.Run(new MainForm());
            StartupTrace("Application.Run returned");
        }
        catch (Exception ex)
        {
            StartupTrace("Fatal: " + ex);
            MessageBox.Show(ex.ToString(), "Fusion Terminal Windows", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}