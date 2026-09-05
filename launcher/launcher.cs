using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

namespace MediaMultiToolLauncher
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string pythonw = Path.Combine(baseDir, @".venv\Scripts\pythonw.exe");
            string runScript = Path.Combine(baseDir, "run.py");

            if (!File.Exists(pythonw))
            {
                string startBat = Path.Combine(baseDir, "start.bat");
                if (File.Exists(startBat))
                {
                    DialogResult result = MessageBox.Show(
                        "O ambiente virtual Python não foi encontrado.\nDeseja inicializar a configuração agora?",
                        "Media MultiTool",
                        MessageBoxButtons.YesNo,
                        MessageBoxIcon.Question
                    );

                    if (result == DialogResult.Yes)
                    {
                        ProcessStartInfo startPsi = new ProcessStartInfo();
                        startPsi.FileName = startBat;
                        startPsi.WorkingDirectory = baseDir;
                        startPsi.UseShellExecute = true;
                        Process.Start(startPsi);
                    }
                    return;
                }

                MessageBox.Show(
                    "Não foi possível encontrar o ambiente Python (.venv\\Scripts\\pythonw.exe).\nExecute start.bat para configurar o projeto.",
                    "Media MultiTool - Erro",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = pythonw;
            psi.Arguments = "\"" + runScript + "\"";
            psi.WorkingDirectory = baseDir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;

            try
            {
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Falha ao iniciar Media MultiTool:\n" + ex.Message,
                    "Media MultiTool - Erro",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }
    }
}
