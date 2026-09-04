import os
import sys
from pathlib import Path

# Garantir que a raiz do projeto esteja no PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import customtkinter as ctk
    import yt_dlp
except ImportError as e:
    print(f"[ERRO DE INICIALIZAÇÃO] Faltam dependências essenciais: {e}")
    print("Execute: .venv\\Scripts\\pip install -r requirements.txt")
    sys.exit(1)

from ui.main_window import MainWindow


def main():
    """Inicia a interface gráfica do Media MultiTool."""
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
