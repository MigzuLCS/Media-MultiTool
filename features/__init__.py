"""
Registro central de features e abas do Media MultiTool.

Para adicionar uma nova funcionalidade no futuro:
1. Crie uma classe herdando de BaseFeature (em features/sua_feature.py)
2. Importe-a aqui e adicione à lista AVAILABLE_FEATURES.
A interface gráfica registrará automaticamente o botão na barra lateral e o container de visualização.
"""

from core.module_manager import module_manager
from features.base import BaseFeature
from features.youtube_tab import YouTubeTab
from features.compress_tab import CompressTab
from features.trim_tab import TrimTab
from features.convert_tab import ConvertTab
from features.disk_analyzer_tab import DiskAnalyzerTab
from features.settings_tab import SettingsTab

ALL_FEATURES = [
    YouTubeTab,
    CompressTab,
    TrimTab,
    ConvertTab,
    DiskAnalyzerTab,
    SettingsTab,
]

# Registra todas as ferramentas conhecidas no ModuleManager
for feat_cls in ALL_FEATURES:
    module_manager.register(feat_cls)


class _DynamicFeaturesList(list):
    """
    Lista dinâmica que reflete os módulos atualmente ativos no ModuleManager,
    mantendo total compatibilidade retroativa com código legado.
    """
    def __iter__(self):
        return iter(module_manager.get_active_features())

    def __len__(self):
        return len(module_manager.get_active_features())

    def __getitem__(self, index):
        return module_manager.get_active_features()[index]

    def __contains__(self, item):
        return item in module_manager.get_active_features()

    def __bool__(self):
        return bool(module_manager.get_active_features())


AVAILABLE_FEATURES = _DynamicFeaturesList()

__all__ = ["BaseFeature", "AVAILABLE_FEATURES", "ALL_FEATURES", "module_manager"]
