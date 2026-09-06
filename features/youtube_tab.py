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
    title = "Downloader Web"
    icon = "📥"
    description = "Baixe vídeos e músicas de YouTube, Spotify, TikTok, Instagram, Twitter/X e mais."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho da aba
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="📥 Downloader Universal da Web",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        desc_lbl = ctk.CTkLabel(
            self.frame,
            text="Baixe vídeos em alta resolução ou extraia áudio MP3 com capas e tags de gênero automáticas.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 16))

        # Cabeçalho do Campo da URL com Badge Dinâmico
        url_header = ctk.CTkFrame(self.frame, fg_color="transparent")
        url_header.pack(fill="x", pady=(0, 4))

        url_lbl = ctk.CTkLabel(
            url_header,
            text="URL da Mídia:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        url_lbl.pack(side="left")

        self.platform_badge = ctk.CTkLabel(
            url_header,
            text="🌐 Web / Universal",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("gray85", "gray25"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.platform_badge.pack(side="right")

        self.playlist_btn = ctk.CTkButton(
            url_header,
            text="📑 Baixar Playlist",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=26,
            corner_radius=6,
            fg_color=("#1f6aa5", "#144870"),
            hover_color=("#144870", "#0e3350"),
            command=self._download_playlist_click,
        )
        # O botão permanece desempacotado até uma playlist ser detectada na URL

        self.url_entry = ctk.CTkEntry(
            self.frame,
            placeholder_text="https://... (YouTube, Spotify, TikTok, Instagram, Twitter/X, etc.)",
            font=ctk.CTkFont(size=13),
            height=38,
        )
        self.url_entry.pack(fill="x", pady=(0, 6))
        self.url_entry.bind("<KeyRelease>", lambda e: self._on_url_input_changed())

        # Chips visuais com plataformas suportadas
        chips_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        chips_frame.pack(fill="x", pady=(0, 16))
        supported_platforms = ["YouTube", "Spotify", "TikTok", "Instagram", "X (Twitter)", "Reddit", "Twitch"]
        for p in supported_platforms:
            chip = ctk.CTkLabel(
                chips_frame,
                text=p,
                font=ctk.CTkFont(size=11),
                text_color="gray",
                fg_color=("gray90", "gray20"),
                corner_radius=4,
                padx=6,
                pady=1,
            )
            chip.pack(side="left", padx=(0, 6))

        # Configurações de Formato e Qualidade
        opts_frame = ctk.CTkFrame(self.frame)
        opts_frame.pack(fill="x", pady=(0, 14), padx=2)

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

        # Checkbox de Enriquecimento e Gênero Musical
        self.auto_tag_var = ctk.BooleanVar(value=True)
        self.auto_tag_cb = ctk.CTkCheckBox(
            self.frame,
            text="Identificar metadados e gênero musical automaticamente (Tags ID3 + Capa)",
            variable=self.auto_tag_var,
            font=ctk.CTkFont(size=12),
        )
        self.auto_tag_cb.pack(fill="x", pady=(0, 16))

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

    def _on_url_input_changed(self):
        url = self.url_entry.get().strip()
        plat = youtube_downloader.detect_platform(url)

        if plat == "spotify":
            self.platform_badge.configure(text="🟢 Spotify (Áudio)", text_color="#1DB954")
            self.playlist_btn.pack_forget()
            if self.mode_var.get() != "audio":
                self.mode_selector.set("Áudio (MP3)")
                self._on_mode_change("Áudio (MP3)")
        elif plat == "youtube":
            self.platform_badge.configure(text="🔴 YouTube", text_color="#FF4444")
            # Exibe o botão de playlist na região do cabeçalho se houver playlist/mix na URL
            if youtube_downloader.has_playlist(url):
                if youtube_downloader.is_mix_playlist(url):
                    self.playlist_btn.configure(text="📑 Baixar Mix (Máx 20 faixas)")
                else:
                    self.playlist_btn.configure(text="📑 Baixar Playlist Completa")
                self.playlist_btn.pack(side="right", padx=(0, 8))
            else:
                self.playlist_btn.pack_forget()
        elif plat == "tiktok":
            self.platform_badge.configure(text="⚫ TikTok", text_color="#00F2FE")
            self.playlist_btn.pack_forget()
        elif plat == "instagram":
            self.platform_badge.configure(text="🟣 Instagram", text_color="#E1306C")
            self.playlist_btn.pack_forget()
        elif plat == "twitter_x":
            self.platform_badge.configure(text="🐦 Twitter / X", text_color="#1DA1F2")
            self.playlist_btn.pack_forget()
        elif plat == "reddit":
            self.platform_badge.configure(text="🟠 Reddit", text_color="#FF4500")
            self.playlist_btn.pack_forget()
        elif plat == "twitch":
            self.platform_badge.configure(text="🟣 Twitch", text_color="#9146FF")
            self.playlist_btn.pack_forget()
        elif plat == "soundcloud":
            self.platform_badge.configure(text="🟠 SoundCloud", text_color="#FF5500")
            self.playlist_btn.pack_forget()
        else:
            self.platform_badge.configure(text="🌐 Web / Universal", text_color=("gray40", "gray70"))
            self.playlist_btn.pack_forget()

    def _on_mode_change(self, value: str):
        if "Áudio" in value:
            self.mode_var.set("audio")
            self.quality_menu.configure(state="disabled")
            self.quality_lbl.configure(text_color="gray")
            self.auto_tag_cb.configure(state="normal")
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

    def _download_playlist_click(self):
        self._start_download(is_playlist=True)

    def _start_download(self, is_playlist: bool = False):
        url = self.url_entry.get().strip()
        if not url:
            self.show_error("URL Vazia", "Por favor, insira o link da mídia para download.")
            return

        plat = youtube_downloader.detect_platform(url)

        # Se for link do YouTube e o usuário clicou no botão de download normal:
        if plat == "youtube":
            if not is_playlist:
                if youtube_downloader.is_playlist_url(url):
                    # Se for URL de playlist pura (sem vídeo individual), ativa modo playlist automaticamente
                    is_playlist = True
                else:
                    # Limpa parâmetros de mix / playlist para baixar apenas o vídeo individual
                    cleaned_url = youtube_downloader.clean_url(url)
                    if cleaned_url != url:
                        self.url_entry.delete(0, "end")
                        self.url_entry.insert(0, cleaned_url)
                        url = cleaned_url

        out_dir = self.output_selector.get_path()
        if not out_dir or not Path(out_dir).exists():
            self.show_error("Pasta Inválida", "A pasta de destino especificada não existe.")
            return

        btn_text = "Baixando Playlist..." if is_playlist else "Baixando..."
        self.action_btn.configure(state="disabled", text=btn_text)
        self.playlist_btn.configure(state="disabled")
        self.progress_card.reset("Conectando ao servidor...")

        mode = self.mode_var.get()
        quality = self.quality_var.get()
        auto_tag = self.auto_tag_var.get()

        def task_target(on_progress=None, cancel_event=None):
            return youtube_downloader.download(
                url=url,
                output_dir=out_dir,
                mode=mode,
                quality=quality,
                auto_tag=auto_tag,
                is_playlist=is_playlist,
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
            name="media_download",
            target=task_target,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_success(self, filepath: str):
        self.action_btn.configure(state="normal", text="Baixar Mídia Agora")
        self.playlist_btn.configure(state="normal")
        p = Path(filepath)
        if p.is_dir():
            self.show_success("Download Concluído", f"Playlist salva com sucesso na pasta:\n{filepath}")
        else:
            self.show_success("Download Concluído", f"Arquivo salvo com sucesso:\n{p.name}")

    def _on_error(self, exc: Exception):
        self.action_btn.configure(state="normal", text="Baixar Mídia Agora")
        self.playlist_btn.configure(state="normal")
        self.progress_card.update_progress(0.0, "Erro durante o download.")
        self.show_error("Erro no Download", str(exc))

    def _cancel_download(self):
        task_manager.cancel_task("media_download")
        self.action_btn.configure(state="normal", text="Baixar Mídia Agora")
        self.playlist_btn.configure(state="normal")
