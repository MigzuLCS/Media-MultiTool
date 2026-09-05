import os
import sys
from pathlib import Path
import customtkinter as ctk
from tkinter import messagebox
from typing import Dict, Optional

from core.config import config
from core.ffmpeg_manager import ffmpeg_manager
from features import AVAILABLE_FEATURES
from features.base import BaseFeature


class MainWindow(ctk.CTk):
    """Janela principal do Media MultiTool com barra lateral dinâmica e modular."""

    def __init__(self):
        # Identidade do processo no Windows (para ícone próprio na barra de tarefas)
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MigzuLCS.MediaMultiTool.1.0")
            except Exception:
                pass

        super().__init__()

        # Configurações iniciais da janela
        self.title("Media MultiTool — Central de Mídia Desktop")
        self.geometry("1020x700")
        self.minsize(860, 580)

        # Configurar ícone da janela
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Aplicar tema salvo
        theme = config.get("theme", "dark")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")

        # Configurar layout grid 1x2 (Sidebar | Conteúdo)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.feature_instances: Dict[str, BaseFeature] = {}
        self.feature_frames: Dict[str, ctk.CTkFrame] = {}
        self.sidebar_buttons: Dict[str, ctk.CTkButton] = {}
        self.current_feature_id: Optional[str] = None

        # Fila thread-safe para comunicação entre threads de segundo plano e a interface gráfica
        import queue
        self._gui_queue = queue.Queue()
        self.bind("<<DispatchGUI>>", self._process_gui_queue)
        self._poll_gui_queue()

        self._build_sidebar()
        self._build_content_area()

        # Selecionar a primeira feature por padrão
        if AVAILABLE_FEATURES:
            first_feature_id = AVAILABLE_FEATURES[0].id
            self.switch_tab(first_feature_id)

    def _build_sidebar(self):
        """Constrói a barra lateral de navegação."""
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(len(AVAILABLE_FEATURES) + 3, weight=1)

        # Logo / Título
        logo_lbl = ctk.CTkLabel(
            self.sidebar,
            text="🎬 Media MultiTool",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        logo_lbl.grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        version_lbl = ctk.CTkLabel(
            self.sidebar,
            text="v1.0.0 • Modular & Extensível",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        version_lbl.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        # Botões de Navegação dinâmicos
        for idx, feat_cls in enumerate(AVAILABLE_FEATURES):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{feat_cls.icon}  {feat_cls.title}",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
                height=38,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray25"),
                command=lambda fid=feat_cls.id: self.switch_tab(fid),
            )
            btn.grid(row=idx + 2, column=0, padx=12, pady=4, sticky="ew")
            self.sidebar_buttons[feat_cls.id] = btn

        # Rodapé da sidebar com status do FFmpeg
        ff_found = ffmpeg_manager.is_available()
        status_text = "🟢 FFmpeg Pronto" if ff_found else "⚠️ FFmpeg Ausente"
        status_color = "#2ecc71" if ff_found else "#f39c12"

        self.ff_badge = ctk.CTkLabel(
            self.sidebar,
            text=status_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=status_color,
        )
        self.ff_badge.grid(row=len(AVAILABLE_FEATURES) + 4, column=0, padx=20, pady=(10, 20), sticky="s")

    def _build_content_area(self):
        """Área central onde as ferramentas serão exibidas."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.grid_rowconfigure(0, weight=1)
        self.content_container.grid_columnconfigure(0, weight=1)

    def switch_tab(self, feature_id: str):
        """Alterna a tela para a ferramenta selecionada."""
        if self.current_feature_id == feature_id:
            return

        # Desmontar aba anterior
        if self.current_feature_id and self.current_feature_id in self.feature_instances:
            self.feature_instances[self.current_feature_id].on_unmount()
            if self.current_feature_id in self.feature_frames:
                self.feature_frames[self.current_feature_id].grid_forget()

        # Atualizar estilo dos botões na sidebar
        for fid, btn in self.sidebar_buttons.items():
            if fid == feature_id:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        # Criar instância da feature caso ainda não tenha sido carregada (Lazy Loading)
        if feature_id not in self.feature_instances:
            target_cls = next((cls for cls in AVAILABLE_FEATURES if cls.id == feature_id), None)
            if target_cls:
                instance = target_cls(master=self.content_container, main_window=self)
                frame = instance.render(self.content_container)
                self.feature_instances[feature_id] = instance
                self.feature_frames[feature_id] = frame

        # Exibir a nova tela
        if feature_id in self.feature_frames:
            self.feature_frames[feature_id].grid(row=0, column=0, sticky="nsew")
            self.feature_instances[feature_id].on_mount()
            self.current_feature_id = feature_id

    def show_toast(self, title: str, message: str, kind: str = "info"):
        """Exibe diálogos de aviso amigáveis."""
        if kind == "error":
            messagebox.showerror(title, message, parent=self)
        elif kind == "success":
            messagebox.showinfo(title, message, parent=self)
        else:
            messagebox.showinfo(title, message, parent=self)

    def dispatch_gui(self, callback):
        """Executa um callback de forma 100% thread-safe na thread da interface gráfica."""
        self._gui_queue.put(callback)

    def _poll_gui_queue(self):
        try:
            if not self.winfo_exists():
                return
            self._process_gui_queue()
            if self.winfo_exists():
                self.after(25, self._poll_gui_queue)
        except Exception:
            pass

    def _process_gui_queue(self, event=None):
        while not self._gui_queue.empty():
            try:
                fn = self._gui_queue.get_nowait()
                fn()
            except Exception as e:
                import traceback
                print(f"[GUI Dispatch Error] {e}")
                traceback.print_exc()
