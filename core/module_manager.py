import os
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Type, Callable, Tuple

from core.paths import get_config_dir, get_app_root
from core.ffmpeg_manager import ffmpeg_manager


@dataclass
class ModuleInfo:
    id: str
    title: str
    icon: str
    description: str
    category: str = "Geral"
    is_core: bool = False
    requires_ffmpeg: bool = False
    requires_ytdlp: bool = False
    estimated_size_mb: float = 0.0
    enabled: bool = True
    feature_class: Optional[Type] = None


class ModuleManager:
    """
    Gerenciador central de módulos do Media MultiTool.
    Controla quais módulos estão registrados, instalados e ativados pelo usuário
    ou pelo instalador (via modules.json).
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir if config_dir is not None else get_config_dir()
        self.app_root = get_app_root()
        self._registry: Dict[str, ModuleInfo] = {}
        self._enabled_ids: set[str] = set()
        self._has_loaded_manifest = False
        self._listeners: List[Callable[[], None]] = []

    @property
    def manifest_path(self) -> Path:
        """
        Caminho do arquivo modules.json.
        Verifica primeiro se existe um modules.json na pasta de instalação (criado pelo Setup).
        Caso contrário, usa a pasta de configurações do usuário.
        """
        app_manifest = self.app_root / "modules.json"
        if app_manifest.exists():
            return app_manifest
        return self.config_dir / "modules.json"

    def register(self, feature_class: Type) -> ModuleInfo:
        """Registra uma classe de feature como módulo disponível."""
        feat_id = getattr(feature_class, "id", "unknown")
        title = getattr(feature_class, "title", feat_id.title())
        icon = getattr(feature_class, "icon", "⚙️")
        desc = getattr(feature_class, "description", "")
        category = getattr(feature_class, "category", "Geral")
        is_core = getattr(feature_class, "is_core", False)
        req_ffmpeg = getattr(feature_class, "requires_ffmpeg", False)
        req_ytdlp = getattr(feature_class, "requires_ytdlp", False)
        size_mb = getattr(feature_class, "estimated_size_mb", 0.0)

        info = ModuleInfo(
            id=feat_id,
            title=title,
            icon=icon,
            description=desc,
            category=category,
            is_core=is_core,
            requires_ffmpeg=req_ffmpeg,
            requires_ytdlp=req_ytdlp,
            estimated_size_mb=size_mb,
            enabled=True,
            feature_class=feature_class,
        )

        self._registry[feat_id] = info
        return info

    def load_manifest(self):
        """Carrega a seleção de módulos a partir de modules.json."""
        manifest = self.manifest_path
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Formato 1: {"enabled_modules": ["youtube", "convert"]}
                if "enabled_modules" in data and isinstance(data["enabled_modules"], list):
                    self._enabled_ids = set(data["enabled_modules"])
                # Formato 2: {"modules": {"youtube": true, "convert": false}}
                elif "modules" in data and isinstance(data["modules"], dict):
                    self._enabled_ids = {
                        mid for mid, val in data["modules"].items()
                        if (val is True or (isinstance(val, dict) and val.get("enabled", True)))
                    }
                else:
                    self._enabled_ids = set(self._registry.keys())

                self._has_loaded_manifest = True
            except Exception as e:
                print(f"[ModuleManager] Erro ao carregar {manifest}: {e}")
                self._enabled_ids = set(self._registry.keys())
        else:
            # Sem arquivo de manifesto prévio: todos os módulos registrados ficam ativos por padrão
            self._enabled_ids = set(self._registry.keys())

        # Módulos marcados como core (ex: configurações) são SEMPRE ativados obrigatoriamente
        for mid, info in self._registry.items():
            if info.is_core:
                self._enabled_ids.add(mid)
            info.enabled = mid in self._enabled_ids

    def save_manifest(self):
        """Persiste a seleção de módulos em modules.json."""
        manifest = self.manifest_path
        try:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": "1.0",
                "enabled_modules": sorted(list(self._enabled_ids)),
            }
            with open(manifest, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ModuleManager] Erro ao salvar {manifest}: {e}")

    def get_all_modules(self) -> List[ModuleInfo]:
        """Retorna todos os módulos registrados."""
        if not self._has_loaded_manifest:
            self.load_manifest()
        return list(self._registry.values())

    def get_active_modules(self) -> List[ModuleInfo]:
        """Retorna apenas os módulos habilitados."""
        if not self._has_loaded_manifest:
            self.load_manifest()
        return [info for info in self._registry.values() if info.enabled]

    def get_active_features(self) -> List[Type]:
        """Retorna as classes de features ativas para exibição na UI."""
        active = self.get_active_modules()
        return [m.feature_class for m in active if m.feature_class is not None]

    def is_module_enabled(self, module_id: str) -> bool:
        if not self._has_loaded_manifest:
            self.load_manifest()
        return module_id in self._enabled_ids

    def enable_module(self, module_id: str) -> bool:
        """Habilita um módulo."""
        if module_id in self._registry:
            self._enabled_ids.add(module_id)
            self._registry[module_id].enabled = True
            self.save_manifest()
            self._notify_listeners()
            return True
        return False

    def disable_module(self, module_id: str) -> bool:
        """Desabilita um módulo (a menos que seja core)."""
        if module_id in self._registry:
            if self._registry[module_id].is_core:
                return False  # Módulos essenciais não podem ser desativados
            self._enabled_ids.discard(module_id)
            self._registry[module_id].enabled = False
            self.save_manifest()
            self._notify_listeners()
            return True
        return False

    def toggle_module(self, module_id: str) -> bool:
        """Alterna o estado de um módulo."""
        if self.is_module_enabled(module_id):
            return self.disable_module(module_id)
        else:
            return self.enable_module(module_id)

    def set_enabled_modules(self, module_ids: List[str]):
        """Define o conjunto de módulos habilitados de uma só vez."""
        new_set = set(module_ids)
        # Preserva os módulos essenciais (core)
        for mid, info in self._registry.items():
            if info.is_core:
                new_set.add(mid)

        self._enabled_ids = new_set
        for mid, info in self._registry.items():
            info.enabled = mid in self._enabled_ids

        self.save_manifest()
        self._notify_listeners()

    def check_dependencies(self, module_id: str) -> Tuple[bool, List[str]]:
        """
        Verifica se as dependências externas do módulo estão satisfeitas.
        Retorna (sucesso, lista_de_faltantes).
        """
        info = self._registry.get(module_id)
        if not info:
            return True, []

        missing = []
        if info.requires_ffmpeg and not ffmpeg_manager.is_available():
            missing.append("FFmpeg")

        if info.requires_ytdlp:
            try:
                import yt_dlp
            except ImportError:
                missing.append("yt-dlp")

        return len(missing) == 0, missing

    def add_listener(self, callback: Callable[[], None]):
        """Registra um ouvinte para alterações no estado dos módulos."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self):
        for cb in list(self._listeners):
            try:
                cb()
            except Exception as e:
                print(f"[ModuleManager Listener Error] {e}")


module_manager = ModuleManager()
