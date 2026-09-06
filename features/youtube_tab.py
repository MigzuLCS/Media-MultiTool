import os
from pathlib import Path
import customtkinter as ctk

from features.base import BaseFeature
from ui.components.file_selector import FileSelector
from ui.components.progress_card import ProgressCard
from core.downloader import youtube_downloader
from core.tasks import task_manager
from core.config import config


class YouTubeTab(BaseFeature):
    id = "youtube"
    title = "YouTube Downloader"
    icon = "📥"
    description = "Baixe vídeos em alta resolução ou extraia faixas de áudio em MP3."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho da aba
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="📥 Baixar do YouTube / Web",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        desc_lbl = ctk.CTkLabel(
            self.frame,
            text="Cole o link do vídeo para baixar em MP4 (com qualidade selecionável) ou converter direto para MP3.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 16))

        # Campo da URL
        url_lbl = ctk.CTkLabel(
            self.frame,
            text="URL do Vídeo:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        url_lbl.pack(fill="x", pady=(0, 4))

        self.url_entry = ctk.CTkEntry(
            self.frame,
            placeholder_text="https://www.youtube.com/watch?v=...",
            font=ctk.CTkFont(size=13),
            height=38,
        )
        self.url_entry.pack(fill="x", pady=(0, 16))

        # Configurações de Formato e Qualidade
        opts_frame = ctk.CTkFrame(self.frame)
        opts_frame.pack(fill="x", pady=(0, 16), padx=2)

        # Modo (Vídeo vs Áudio)
        mode_box = ctk.CTkFrame(opts_frame, fg_color="transparent")
        mode_box.pack(side="left", fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            mode_box,
            text="Tipo de Mídia:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.mode_var = ctk.StringVar(value="video")
        self.mode_selector = ctk.CTkSegmentedButton(
            mode_box,
            values=["Vídeo (MP4)", "Áudio (MP3)"],
            command=self._on_mode_change,
        )
        self.mode_selector.set("Vídeo (MP4)")
        self.mode_selector.pack(fill="x")

        # Qualidade de Vídeo
        self.quality_box = ctk.CTkFrame(opts_frame, fg_color="transparent")
        self.quality_box.pack(side="right", fill="both", expand=True, padx=14, pady=12)

        self.quality_lbl = ctk.CTkLabel(
            self.quality_box,
            text="Qualidade Máxima:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.quality_lbl.pack(fill="x", pady=(0, 4))

        self.quality_var = ctk.StringVar(value="best")
        self.quality_menu = ctk.CTkOptionMenu(
            self.quality_box,
            values=["Melhor Disponível", "1080p (Full HD)", "720p (HD)", "480p (SD)"],
            command=self._on_quality_change,
        )
        self.quality_menu.pack(fill="x")

        # Seletor de Pasta de Saída
        default_dir = config.get("output_dir", str(Path.home() / "Downloads"))
        self.output_selector = FileSelector(
            self.frame,
            label="Salvar na Pasta:",
            mode="dir",
            default_path=default_dir,
        )
        self.output_selector.pack(fill="x", pady=(0, 20))

        # Botão de Ação
        self.action_btn = ctk.CTkButton(
            self.frame,
            text="Baixar Mídia Agora",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_download,
        )
        self.action_btn.pack(fill="x", pady=(0, 16))

        # Card de Progresso
        self.progress_card = ProgressCard(
            self.frame,
            title="Progresso do Download",
            on_cancel=self._cancel_download,
        )
        self.progress_card.pack(fill="x", pady=(0, 10))

        return self.frame

    def _on_mode_change(self, value: str):
        if "Áudio" in value:
            self.mode_var.set("audio")
            self.quality_menu.configure(state="disabled")
            self.quality_lbl.configure(text_color="gray")
        else:
            self.mode_var.set("video")
            self.quality_menu.configure(state="normal")
            self.quality_lbl.configure(text_color=("black", "white"))

    def _on_quality_change(self, value: str):
        mapping = {
            "Melhor Disponível": "best",
            "1080p (Full HD)": "1080p",
            "720p (HD)": "720p",
            "480p (SD)": "480p",
        }
        self.quality_var.set(mapping.get(value, "best"))

    def _start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.show_error("URL Vazia", "Por favor, insira o link de um vídeo do YouTube.")
            return

        # Limpa parâmetros de mix / playlist caso a URL aponte para um vídeo individual
        cleaned_url = youtube_downloader.clean_url(url)
        if cleaned_url != url:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, cleaned_url)
            url = cleaned_url

        if youtube_downloader.is_playlist_url(url):
            self.show_error(
                "Link de Playlist Não Suportado",
                "O link inserido aponta para uma playlist completa. Por favor, utilize o link de um vídeo ou música individual."
            )
            return

        out_dir = self.output_selector.get_path()
        if not out_dir or not Path(out_dir).exists():
            self.show_error("Pasta Inválida", "A pasta de destino especificada não existe.")
            return

        self.action_btn.configure(state="disabled", text="Baixando...")
        self.progress_card.reset("Conectando ao servidor...")

        mode = self.mode_var.get()
        quality = self.quality_var.get()

        def task_target(on_progress=None, cancel_event=None):
            return youtube_downloader.download(
                url=url,
                output_dir=out_dir,
                mode=mode,
                quality=quality,
                on_progress=on_progress,
                cancel_event=cancel_event,
            )

        def on_prog(frac, msg):
            self.dispatch_gui(lambda: self.progress_card.update_progress(frac, msg))

        def on_succ(filepath):
            self.dispatch_gui(lambda: self._on_success(filepath))

        def on_err(exc):
            self.dispatch_gui(lambda: self._on_error(exc))

        task_manager.run_task(
            name="youtube_download",
            target=task_target,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_success(self, filepath: str):
        self.action_btn.configure(state="normal", text="Baixar Mídia Agora")
        filename = Path(filepath).name
        self.show_success("Download Concluído", f"Arquivo salvo com sucesso:\n{filename}")

    def _on_error(self, exc: Exception):
        self.action_btn.configure(state="normal", text="Baixar Mídia Agora")
        self.progress_card.update_progress(0.0, "Erro durante o download.")
        self.show_error("Erro no Download", str(exc))

    def _cancel_download(self):
        task_manager.cancel_task("youtube_download")
        self.action_btn.configure(state="normal", text="Baixar Mídia Agora")
