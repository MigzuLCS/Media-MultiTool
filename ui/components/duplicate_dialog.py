import customtkinter as ctk
from typing import Optional


class DuplicateConflictDialog(ctk.CTkToplevel):
    """
    Diálogo modal para resolução de conflito quando um arquivo já existe na pasta de destino.
    Oferece opções claras e seguras: Substituir, Criar Cópia ou Pular/Cancelar.
    """

    def __init__(self, master, filename: str, folder: str):
        super().__init__(master)
        self.title("Arquivo Já Existente")
        self.geometry("480x230")
        self.resizable(False, False)

        self.result: str = "skip"  # padrão seguro caso a janela seja fechada

        # Configurações de modalidade
        try:
            top_level = master.winfo_toplevel()
            self.transient(top_level)
            self.grab_set()
        except Exception:
            top_level = master

        # Título / Cabeçalho
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=(18, 6))

        ctk.CTkLabel(
            title_frame,
            text="⚠️ Arquivo Já Existe na Pasta",
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w",
        ).pack(fill="x")

        msg_text = "O arquivo abaixo já existe na pasta de destino. Escolha o que deseja fazer:"
        ctk.CTkLabel(
            self,
            text=msg_text,
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"),
            justify="left",
            anchor="w",
            wraplength=440,
        ).pack(fill="x", padx=20, pady=(0, 8))

        # Nome do arquivo em destaque
        pill_frame = ctk.CTkFrame(self, fg_color=("gray85", "gray20"), corner_radius=6)
        pill_frame.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkLabel(
            pill_frame,
            text=f"📁 {filename}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1f6aa5", "#4ea8de"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=6)

        # Barra de Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        # 1. Substituir
        self.btn_overwrite = ctk.CTkButton(
            btn_frame,
            text="🔄 Substituir",
            height=34,
            fg_color=("#c0392b", "#962d22"),
            hover_color=("#a93226", "#78241c"),
            command=lambda: self._choose("overwrite"),
        )
        self.btn_overwrite.pack(side="left", padx=(0, 8), expand=True, fill="x")

        # 2. Criar Cópia (1)
        self.btn_copy = ctk.CTkButton(
            btn_frame,
            text="📋 Criar Cópia",
            height=34,
            fg_color=("#2980b9", "#1f6aa5"),
            hover_color=("#1f6aa5", "#144870"),
            command=lambda: self._choose("copy"),
        )
        self.btn_copy.pack(side="left", padx=(0, 8), expand=True, fill="x")

        # 3. Pular / Cancelar
        self.btn_skip = ctk.CTkButton(
            btn_frame,
            text="❌ Pular",
            height=34,
            fg_color=("gray70", "gray35"),
            hover_color=("gray60", "gray45"),
            text_color=("black", "white"),
            command=lambda: self._choose("skip"),
        )
        self.btn_skip.pack(side="left", expand=True, fill="x")

        # Posicionamento centralizado sobre a janela mãe
        try:
            self.update_idletasks()
            x = top_level.winfo_x() + (top_level.winfo_width() - 480) // 2
            y = top_level.winfo_y() + (top_level.winfo_height() - 230) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", lambda: self._choose("skip"))

    def _choose(self, choice: str):
        self.result = choice
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    @classmethod
    def ask_resolution(cls, master, filename: str, folder: str) -> str:
        """Exibe o diálogo modal e retorna 'overwrite', 'copy' ou 'skip'."""
        try:
            dialog = cls(master, filename, folder)
            dialog.wait_window()
            return dialog.result
        except Exception:
            return "copy"
