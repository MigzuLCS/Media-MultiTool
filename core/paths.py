import os
import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Retorna o diretório raiz da aplicação de forma consistente.
    Em modo empacotado (PyInstaller / sys.frozen), retorna o diretório onde o executável reside.
    Em modo desenvolvimento, retorna a raiz do repositório.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_assets_dir() -> Path:
    """
    Retorna o diretório de assets (ícones, imagens).
    Verifica se os assets estão na pasta temporária do PyInstaller (_MEIPASS)
    ou na pasta raiz do aplicativo.
    """
    # 1. Modo OneFile do PyInstaller
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundle_assets = Path(meipass) / "assets"
        if bundle_assets.exists():
            return bundle_assets

    # 2. Modo Onedir ou Modo Desenvolvimento
    root_assets = get_app_root() / "assets"
    return root_assets


def get_config_dir() -> Path:
    """
    Retorna o diretório para salvar configurações (config.json).
    - Se houver um config.json na pasta do executável (modo portátil) ou em dev, usa local.
    - Caso contrário, em modo instalado, usa %APPDATA%/Media MultiTool para preservar permissões.
    """
    app_root = get_app_root()
    local_cfg = app_root / "config.json"

    if not getattr(sys, "frozen", False) or local_cfg.exists():
        return app_root

    app_data = Path(os.environ.get("APPDATA", Path.home())) / "Media MultiTool"
    try:
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data
    except Exception:
        return app_root
