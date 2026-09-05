import os
import json
from pathlib import Path
from typing import Optional

from core.paths import get_config_dir

DEFAULT_CONFIG = {
    "theme": "dark",
    "output_dir": str(Path.home() / "Downloads"),
    "ffmpeg_path": "",
    "auto_cleanup_temp": True,
}

CONFIG_FILE = get_config_dir() / "config.json"


class ConfigManager:
    """Gerencia as preferências e configurações persistentes do aplicativo."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path if config_path is not None else (get_config_dir() / "config.json")
        self._config = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._config.update(data)
            except Exception as e:
                print(f"[ConfigManager] Erro ao carregar config.json: {e}")
        else:
            self.save()

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Erro ao salvar config.json: {e}")

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value):
        self._config[key] = value
        self.save()


config = ConfigManager()
