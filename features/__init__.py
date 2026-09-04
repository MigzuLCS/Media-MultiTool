"""
Registro central de features e abas do Media MultiTool.

Para adicionar uma nova funcionalidade no futuro:
1. Crie uma classe herdando de BaseFeature (em features/sua_feature.py)
2. Importe-a aqui e adicione à lista AVAILABLE_FEATURES.
A interface gráfica registrará automaticamente o botão na barra lateral e o container de visualização.
"""

from features.base import BaseFeature
from features.youtube_tab import YouTubeTab
from features.compress_tab import CompressTab
from features.trim_tab import TrimTab
from features.convert_tab import ConvertTab
from features.settings_tab import SettingsTab

AVAILABLE_FEATURES = [
    YouTubeTab,
    CompressTab,
    TrimTab,
    ConvertTab,
    SettingsTab,
]

__all__ = ["BaseFeature", "AVAILABLE_FEATURES"]
