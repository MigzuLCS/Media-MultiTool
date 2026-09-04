import os
from pathlib import Path
import customtkinter as ctk

from features.base import BaseFeature
from ui.components.file_selector import FileSelector
from ui.components.progress_card import ProgressCard
from core.ffmpeg_manager import ffmpeg_manager
from core.transformer import media_transformer
from core.tasks import task_manager


class TrimTab(BaseFeature):
    id = "trim"
    title = "Corte Rápido"
    icon = "✂️"
    description = "Corte trechos de vídeos instantaneamente sem perder qualidade ou com precisão de frame."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="✂️ Corte Rápido de Vídeos e Áudios",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        desc_lbl = ctk.CTkLabel(
            self.frame,
            text="Defina o ponto inicial e final para extrair apenas a parte que você quer do arquivo.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 16))

        # Seletor de arquivo de entrada
        self.input_selector = FileSelector(
            self.frame,
            label="Arquivo de Vídeo / Áudio:",
            mode="file",
            filetypes=[
                ("Vídeos e Áudios Suportados", "*.mp4;*.mkv;*.mov;*.avi;*.webm;*.mp3;*.wav;*.m4a"),
                ("Todos os Arquivos", "*.*"),
            ],
            on_change=self._on_input_file_selected,
        )
        self.input_selector.pack(fill="x", pady=(0, 12))

        # Card de informações do arquivo
        self.info_frame = ctk.CTkFrame(self.frame)
        self.info_frame.pack(fill="x", pady=(0, 16), padx=2)

        self.info_lbl = ctk.CTkLabel(
            self.info_frame,
            text="Selecione um arquivo para ver sua duração e características.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            padx=14,
            pady=10,
            anchor="w",
        )
        self.info_lbl.pack(fill="x")

        # Configuração de Pontos de Corte (Início e Fim)
        time_frame = ctk.CTkFrame(self.frame)
        time_frame.pack(fill="x", pady=(0, 16), padx=2)

        # Início
        start_box = ctk.CTkFrame(time_frame, fg_color="transparent")
        start_box.pack(side="left", fill="x", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            start_box,
            text="Tempo Inicial (HH:MM:SS):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.start_entry = ctk.CTkEntry(start_box, placeholder_text="00:00:00")
        self.start_entry.insert(0, "00:00:00")
        self.start_entry.pack(fill="x")

        # Fim
        end_box = ctk.CTkFrame(time_frame, fg_color="transparent")
        end_box.pack(side="right", fill="x", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            end_box,
            text="Tempo Final (HH:MM:SS):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.end_entry = ctk.CTkEntry(end_box, placeholder_text="00:00:30")
        self.end_entry.insert(0, "00:00:30")
        self.end_entry.pack(fill="x")

        # Modo de Corte
        mode_box = ctk.CTkFrame(self.frame)
        mode_box.pack(fill="x", pady=(0, 16), padx=2)

        ctk.CTkLabel(
            mode_box,
            text="Modo de Operação:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 6))

        self.lossless_switch = ctk.CTkSwitch(
            mode_box,
            text="⚡ Modo Lossless Ultra-Rápido (-c copy: sem reencodar, < 1 segundo, sem perda)",
            font=ctk.CTkFont(size=12),
        )
        self.lossless_switch.select()
        self.lossless_switch.pack(fill="x", padx=14, pady=(0, 12))

        # Seletor de saída
        self.output_selector = FileSelector(
            self.frame,
            label="Salvar Arquivo Cortado como:",
            mode="save_file",
            filetypes=[("Mesmo formato", "*.*")],
        )
        self.output_selector.pack(fill="x", pady=(0, 20))

        # Botão de Ação
        self.action_btn = ctk.CTkButton(
            self.frame,
            text="Cortar Vídeo Agora",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_trim,
        )
        self.action_btn.pack(fill="x", pady=(0, 16))

        # Card de Progresso
        self.progress_card = ProgressCard(
            self.frame,
            title="Progresso do Corte",
            on_cancel=self._cancel_trim,
        )
        self.progress_card.pack(fill="x", pady=(0, 10))

        return self.frame

    def _on_input_file_selected(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            return

        p = Path(filepath)
        suggested_out = str(p.parent / f"{p.stem}_cortado{p.suffix}")
        self.output_selector.set_path(suggested_out)

        info = ffmpeg_manager.get_media_info(filepath)
        dur = info.get("duration_str", "00:00:00")
        size = info.get("size_mb", 0.0)
        res = info.get("resolution", "N/A")

        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, dur)

        info_text = f"⏱️ Mídia Detectada: Duração Total: {dur} | Tamanho: {size:.1f} MB | Resolução: {res}"
        self.info_lbl.configure(text=info_text, text_color=("black", "white"))

    def _start_trim(self):
        input_file = self.input_selector.get_path()
        output_file = self.output_selector.get_path()
        start_t = self.start_entry.get().strip() or "00:00:00"
        end_t = self.end_entry.get().strip() or "00:00:10"

        if not input_file or not Path(input_file).exists():
            self.show_error("Arquivo Inválido", "Selecione um arquivo de mídia existente.")
            return

        if not output_file:
            self.show_error("Destino Inválido", "Especifique o arquivo de destino.")
            return

        if not ffmpeg_manager.is_available():
            self.show_error(
                "FFmpeg Ausente",
                "FFmpeg não foi detectado! Acesse a aba 'Configurações' para baixá-lo com 1 clique.",
            )
            return

        is_lossless = bool(self.lossless_switch.get())
        self.action_btn.configure(state="disabled", text="Cortando Mídia...")
        self.progress_card.reset("Iniciando corte...")

        def task_target(on_progress=None, cancel_event=None):
            return media_transformer.trim_video(
                input_path=input_file,
                output_path=output_file,
                start_time=start_t,
                end_time=end_t,
                lossless=is_lossless,
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
            name="video_trim",
            target=task_target,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_success(self, filepath: str):
        self.action_btn.configure(state="normal", text="Cortar Vídeo Agora")
        self.show_success("Corte Concluído!", f"Trecho salvo com sucesso em:\n{Path(filepath).name}")

    def _on_error(self, exc: Exception):
        self.action_btn.configure(state="normal", text="Cortar Vídeo Agora")
        self.progress_card.update_progress(0.0, "Falha ao cortar vídeo.")
        self.show_error("Erro no Corte", str(exc))

    def _cancel_trim(self):
        task_manager.cancel_task("video_trim")
        self.action_btn.configure(state="normal", text="Cortar Vídeo Agora")
