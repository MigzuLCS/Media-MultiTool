import customtkinter as ctk
from typing import Optional, Callable


class ProgressCard(ctk.CTkFrame):
    """Componente de barra de progresso com status, porcentagem e botão de cancelamento."""

    def __init__(
        self,
        master,
        title: str = "Progresso",
        on_cancel: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(master, corner_radius=10, **kwargs)
        self.on_cancel = on_cancel

        self.top_row = ctk.CTkFrame(self, fg_color="transparent")
        self.top_row.pack(fill="x", padx=14, pady=(12, 6))

        self.status_label = ctk.CTkLabel(
            self.top_row,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.pct_label = ctk.CTkLabel(
            self.top_row,
            text="0%",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.pct_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(self, height=12, corner_radius=6)
        self.progress_bar.pack(fill="x", padx=14, pady=(0, 10))
        self.progress_bar.set(0.0)

        self.bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        self.bottom_row.pack(fill="x", padx=14, pady=(0, 12))

        self.detail_label = ctk.CTkLabel(
            self.bottom_row,
            text="Aguardando início...",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.detail_label.pack(side="left", fill="x", expand=True)

        self.cancel_btn = ctk.CTkButton(
            self.bottom_row,
            text="Cancelar",
            width=75,
            height=26,
            fg_color="#8b2500",
            hover_color="#5e1900",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._cancel,
        )
        self.cancel_btn.pack(side="right")
        self.cancel_btn.configure(state="disabled")

    def _cancel(self):
        if self.on_cancel:
            self.on_cancel()
        self.cancel_btn.configure(state="disabled")
        self.detail_label.configure(text="Cancelamento solicitado...")

    def update_progress(self, frac: float, text: str):
        """Atualiza a barra e o texto de progresso (0.0 a 1.0)."""
        safe_frac = max(0.0, min(1.0, frac))
        self.progress_bar.set(safe_frac)
        pct = int(safe_frac * 100)
        self.pct_label.configure(text=f"{pct}%")
        self.detail_label.configure(text=text)
        if safe_frac > 0 and safe_frac < 1.0:
            self.cancel_btn.configure(state="normal")
        else:
            self.cancel_btn.configure(state="disabled")

    def reset(self, initial_text: str = "Pronto para iniciar"):
        self.progress_bar.set(0.0)
        self.pct_label.configure(text="0%")
        self.detail_label.configure(text=initial_text)
        self.cancel_btn.configure(state="disabled")
