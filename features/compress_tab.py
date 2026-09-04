import os
from pathlib import Path
import customtkinter as ctk

from features.base import BaseFeature
from ui.components.file_selector import FileSelector
from ui.components.progress_card import ProgressCard
from core.ffmpeg_manager import ffmpeg_manager
from core.transformer import media_transformer
from core.tasks import task_manager
from core.config import config


class CompressTab(BaseFeature):
    id = "compress"
    title = "Compressor de Vídeo"
    icon = "📉"
    description = "Reduza o tamanho de vídeos com presets inteligentes para Discord, WhatsApp ou taxa CRF."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="📉 Reduzir Tamanho de Vídeos",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        desc_lbl = ctk.CTkLabel(
            self.frame,
            text="Comprima vídeos para caber em limites de envio (Discord, WhatsApp, e-mail) mantendo boa qualidade visual.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 16))

        # Seletor de arquivo de entrada
        self.input_selector = FileSelector(
            self.frame,
            label="Vídeo Original:",
            mode="file",
            filetypes=[
                ("Vídeos Suportados", "*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.wmv"),
                ("Todos os Arquivos", "*.*"),
            ],
            on_change=self._on_input_file_selected,
        )
        self.input_selector.pack(fill="x", pady=(0, 12))

        # Card de informações da mídia
        self.info_frame = ctk.CTkFrame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 16), padx=2)

        self.info_lbl = ctk.CTkLabel(
            self.info_frame,
            text="Selecione um vídeo para visualizar o tamanho, duração e resolução.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            padx=14,
            pady=10,
            anchor="w",
        )
        self.info_lbl.pack(fill="x")

        # Opções de Compressão
        opts_box = ctk.CTkFrame(self.frame)
        opts_box.pack(fill="x", pady=(0, 16), padx=2)

        # Presets de Tamanho
        ctk.CTkLabel(
            opts_box,
            text="Preset de Tamanho Alvo:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 6))

        self.preset_var = ctk.StringVar(value="Discord (25 MB)")
        self.preset_selector = ctk.CTkSegmentedButton(
            opts_box,
            values=["Discord (25 MB)", "WhatsApp (16 MB)", "Email (10 MB)", "Nitro (50 MB)", "Personalizado"],
            command=self._on_preset_change,
        )
        self.preset_selector.set("Discord (25 MB)")
        self.preset_selector.pack(fill="x", padx=14, pady=(0, 12))

        # Configurações Avançadas (Tamanho custom / Codec)
        advanced_row = ctk.CTkFrame(opts_box, fg_color="transparent")
        advanced_row.pack(fill="x", padx=14, pady=(0, 12))

        # Campo tamanho customizado
        self.custom_size_frame = ctk.CTkFrame(advanced_row, fg_color="transparent")
        self.custom_size_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.custom_size_lbl = ctk.CTkLabel(
            self.custom_size_frame,
            text="Tamanho Alvo (MB):",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        self.custom_size_lbl.pack(fill="x")

        self.custom_size_entry = ctk.CTkEntry(
            self.custom_size_frame,
            placeholder_text="Ex: 20",
        )
        self.custom_size_entry.insert(0, "25")
        self.custom_size_entry.configure(state="disabled")
        self.custom_size_entry.pack(fill="x")

        # Seletor de Codec
        codec_frame = ctk.CTkFrame(advanced_row, fg_color="transparent")
        codec_frame.pack(side="right", fill="x", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            codec_frame,
            text="Codec de Vídeo:",
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x")

        self.codec_menu = ctk.CTkOptionMenu(
            codec_frame,
            values=["H.264 (Compatibilidade Universal)", "H.265 / HEVC (Mais Compacto)"],
        )
        self.codec_menu.pack(fill="x")

        # Seletor de destino
        self.output_selector = FileSelector(
            self.frame,
            label="Salvar Arquivo Comprimido como:",
            mode="save_file",
            filetypes=[("Vídeo MP4", "*.mp4")],
        )
        self.output_selector.pack(fill="x", pady=(0, 20))

        # Botão de Ação
        self.action_btn = ctk.CTkButton(
            self.frame,
            text="Iniciar Compressão",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_compression,
        )
        self.action_btn.pack(fill="x", pady=(0, 16))

        # Card de Progresso
        self.progress_card = ProgressCard(
            self.frame,
            title="Progresso da Compressão",
            on_cancel=self._cancel_compression,
        )
        self.progress_card.pack(fill="x", pady=(0, 10))

        return self.frame

    def _on_preset_change(self, value: str):
        if value == "Personalizado":
            self.custom_size_entry.configure(state="normal")
            self.custom_size_lbl.configure(text_color=("black", "white"))
        else:
            self.custom_size_entry.configure(state="disabled")
            self.custom_size_lbl.configure(text_color="gray")
            mapping = {
                "Discord (25 MB)": "25",
                "WhatsApp (16 MB)": "16",
                "Email (10 MB)": "10",
                "Nitro (50 MB)": "50",
            }
            if value in mapping:
                self.custom_size_entry.configure(state="normal")
                self.custom_size_entry.delete(0, "end")
                self.custom_size_entry.insert(0, mapping[value])
                self.custom_size_entry.configure(state="disabled")

    def _on_input_file_selected(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            return

        p = Path(filepath)
        # Preencher sugestão de saída automaticamente
        suggested_out = str(p.parent / f"{p.stem}_comprimido.mp4")
        self.output_selector.set_path(suggested_out)

        # Atualizar metadados
        info = ffmpeg_manager.get_media_info(filepath)
        dur = info.get("duration_str", "00:00:00")
        size = info.get("size_mb", 0.0)
        res = info.get("resolution", "N/A")
        vcodec = info.get("video_codec") or "Desconhecido"

        info_text = f"📹 Informações do Vídeo: {size:.1f} MB | Duração: {dur} | Resolução: {res} | Codec: {vcodec}"
        self.info_lbl.configure(text=info_text, text_color=("black", "white"))

    def _start_compression(self):
        input_file = self.input_selector.get_path()
        output_file = self.output_selector.get_path()

        if not input_file or not Path(input_file).exists():
            self.show_error("Arquivo Ausente", "Selecione um arquivo de vídeo válido para comprimir.")
            return

        if not output_file:
            self.show_error("Destino Ausente", "Defina onde o vídeo comprimido deve ser salvo.")
            return

        if not ffmpeg_manager.is_available():
            self.show_error(
                "FFmpeg Ausente",
                "FFmpeg não foi detectado! Acesse a aba 'Configurações' para baixá-lo com 1 clique.",
            )
            return

        try:
            target_mb = float(self.custom_size_entry.get().strip() or "25")
        except ValueError:
            self.show_error("Valor Inválido", "Insira um número válido para o tamanho alvo em MB.")
            return

        codec = "libx265" if "H.265" in self.codec_menu.get() else "libx264"

        self.action_btn.configure(state="disabled", text="Comprimindo Vídeo...")
        self.progress_card.reset("Iniciando codificação FFmpeg...")

        def task_target(on_progress=None, cancel_event=None):
            return media_transformer.compress_video(
                input_path=input_file,
                output_path=output_file,
                mode="target_size",
                target_size_mb=target_mb,
                codec=codec,
                preset="medium",
                on_progress=on_progress,
                cancel_event=cancel_event,
            )

        def on_prog(frac, msg):
            self.frame.after(0, lambda: self.progress_card.update_progress(frac, msg))

        def on_succ(res):
            self.frame.after(0, lambda: self._on_success(res))

        def on_err(exc):
            self.frame.after(0, lambda: self._on_error(exc))

        task_manager.run_task(
            name="video_compression",
            target=task_target,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_success(self, filepath: str):
        self.action_btn.configure(state="normal", text="Iniciar Compressão")
        size_after = Path(filepath).stat().st_size / (1024 * 1024) if Path(filepath).exists() else 0
        self.show_success(
            "Compressão Finalizada!",
            f"Arquivo gerado com sucesso:\n{Path(filepath).name}\nTamanho final: {size_after:.1f} MB",
        )

    def _on_error(self, exc: Exception):
        self.action_btn.configure(state="normal", text="Iniciar Compressão")
        self.progress_card.update_progress(0.0, "Falha na compressão.")
        self.show_error("Erro na Compressão", str(exc))

    def _cancel_compression(self):
        task_manager.cancel_task("video_compression")
        self.action_btn.configure(state="normal", text="Iniciar Compressão")
