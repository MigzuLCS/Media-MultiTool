from abc import ABC, abstractmethod
import customtkinter as ctk
from typing import Optional


class BaseFeature(ABC):
    """
    Classe base para todas as abas e ferramentas do Media MultiTool.
    Qualquer nova ferramenta deve herdar desta classe e implementar 'render'.
    """

    id: str = "base_feature"
    title: str = "Ferramenta"
    icon: str = "⚙️"
    description: str = "Descrição da ferramenta"

    def __init__(self, master: ctk.CTkFrame, main_window):
        self.master = master
        self.main_window = main_window
        self.frame: Optional[ctk.CTkFrame] = None

    @abstractmethod
    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        """
        Constrói a interface visual da ferramenta dentro do parent especificado
        e retorna o frame principal da tela.
        """
        pass

    def on_mount(self):
        """Chamado quando a aba é selecionada/exibida pelo usuário."""
        pass

    def on_unmount(self):
        """Chamado quando o usuário troca para outra aba."""
        pass

    def show_info(self, title: str, message: str):
        """Exibe mensagem informativa na janela principal."""
        if hasattr(self.main_window, "show_toast"):
            self.main_window.show_toast(title, message, "info")

    def show_error(self, title: str, message: str):
        """Exibe mensagem de erro na janela principal."""
        if hasattr(self.main_window, "show_toast"):
            self.main_window.show_toast(title, message, "error")

    def show_success(self, title: str, message: str):
        """Exibe mensagem de sucesso na janela principal."""
        if hasattr(self.main_window, "show_toast"):
            self.main_window.show_toast(title, message, "success")

    def dispatch_gui(self, callback):
        """Executa um callback de forma segura na thread principal da GUI."""
        if hasattr(self.main_window, "dispatch_gui"):
            self.main_window.dispatch_gui(callback)
        elif self.frame:
            try:
                self.frame.after(0, callback)
            except Exception:
                callback()
        else:
            callback()
