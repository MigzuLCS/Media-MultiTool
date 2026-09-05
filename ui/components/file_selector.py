import customtkinter as ctk
from tkinter import filedialog
from typing import Optional, Callable, List, Tuple


class FileSelector(ctk.CTkFrame):
    """Componente para seleção de arquivo ou diretório com botão de busca e suporte a filtros."""

    def __init__(
        self,
        master,
        label: str = "Arquivo:",
        mode: str = "file",  # 'file', 'save_file' ou 'dir'
        filetypes: Optional[List[Tuple[str, str]]] = None,
        default_path: str = "",
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.mode = mode
        self.filetypes = filetypes or [("Todos os Arquivos", "*.*")]
        self.on_change = on_change

        self.label_widget = ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.label_widget.pack(fill="x", padx=2, pady=(0, 4))

        self.input_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.input_frame.pack(fill="x")

        self.path_entry = ctk.CTkEntry(
            self.input_frame,
            placeholder_text="Nenhum arquivo selecionado...",
            font=ctk.CTkFont(size=12),
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._last_notified_path = default_path
        if default_path:
            self.path_entry.insert(0, default_path)

        self.path_entry.bind("<Return>", lambda e: self._on_entry_commit())
        self.path_entry.bind("<FocusOut>", lambda e: self._on_entry_commit())

        self.browse_btn = ctk.CTkButton(
            self.input_frame,
            text="Procurar...",
            width=90,
            command=self._browse,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.browse_btn.pack(side="right")

    def _browse(self):
        selected = None
        if self.mode == "dir":
            selected = filedialog.askdirectory(title="Selecione a Pasta")
        elif self.mode == "save_file":
            selected = filedialog.asksaveasfilename(
                title="Salvar como",
                filetypes=self.filetypes,
            )
        else:
            selected = filedialog.askopenfilename(
                title="Selecione o Arquivo",
                filetypes=self.filetypes,
            )

        if selected:
            self.set_path(selected)

    def set_path(self, path: str):
        self._last_notified_path = path
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, path)
        if self.on_change:
            self.on_change(path)

    def _on_entry_commit(self):
        current = self.get_path()
        if current and current != self._last_notified_path:
            self._last_notified_path = current
            if self.on_change:
                self.on_change(current)

    def get_path(self) -> str:
        return self.path_entry.get().strip()
