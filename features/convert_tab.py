import os
from pathlib import Path
import customtkinter as ctk

from features.base import BaseFeature
from ui.components.file_selector import FileSelector
from ui.components.progress_card import ProgressCard
from core.ffmpeg_manager import ffmpeg_manager
from core.transformer import media_transformer
from core.tasks import task_manager


class ConvertTab(BaseFeature):
    id = "convert"
    title = "Conversor de Mídia"
    icon = "🔄"
    description = "Converta MP4 para GIF de alta qualidade, extraia áudio MP3/WAV ou alterne formatos."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="🔄 Conversor Multifunções",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        desc_lbl = ctk.CTkLabel(
            self.frame,
            text="Crie GIFs animados em alta definição, extraia faixas sonoras em MP3/WAV ou mude o formato do vídeo.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 16))

        # Seletor de arquivo de entrada
        self.input_selector = FileSelector(
            self.frame,
            label="Arquivo de Entrada:",
            mode="file",
            filetypes=[
                ("Todos os Formatos de Mídia", "*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.wav;*.mp3"),
                ("Todos os Arquivos", "*.*"),
            ],
            on_change=self._on_input_file_selected,
        )
        self.input_selector.pack(fill="x", pady=(0, 12))

        # Tipo de Conversão
        type_frame = ctk.CTkFrame(self.frame)
        type_frame.pack(fill="x", pady=(0, 16), padx=2)

        ctk.CTkLabel(
            type_frame,
            text="Escolha a Transformação Desejada:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 6))

        self.conv_type_menu = ctk.CTkOptionMenu(
            type_frame,
            values=[
                "MP4 para GIF Animado (Alta Definição)",
                "Vídeo para MP3 (Extrair Áudio)",
                "Vídeo para WAV (Áudio Sem Perdas)",
                "Converter Container para MP4",
            ],
            command=self._on_type_change,
        )
        self.conv_type_menu.pack(fill="x", padx=14, pady=(0, 12))

        # Painel Dinâmico de Opções da Conversão
        self.dynamic_options_box = ctk.CTkFrame(self.frame)
        self.dynamic_options_box.pack(fill="x", pady=(0, 16), padx=2)
        self._build_gif_options()

        # Seletor de Saída
        self.output_selector = FileSelector(
            self.frame,
            label="Salvar Arquivo Convertido como:",
            mode="save_file",
        )
        self.output_selector.pack(fill="x", pady=(0, 20))

        # Botão de Ação
        self.action_btn = ctk.CTkButton(
            self.frame,
            text="Iniciar Conversão",
            height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_conversion,
        )
        self.action_btn.pack(fill="x", pady=(0, 16))

        # Card de Progresso
        self.progress_card = ProgressCard(
            self.frame,
            title="Progresso da Conversão",
            on_cancel=self._cancel_conversion,
        )
        self.progress_card.pack(fill="x", pady=(0, 10))

        return self.frame

    def _clear_dynamic_options(self):
        for widget in self.dynamic_options_box.winfo_children():
            widget.destroy()

    def _build_gif_options(self):
        self._clear_dynamic_options()
        row = ctk.CTkFrame(self.dynamic_options_box, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        # FPS
        fps_box = ctk.CTkFrame(row, fg_color="transparent")
        fps_box.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(fps_box, text="Taxa de Quadros (FPS):", font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(fill="x")
        self.gif_fps = ctk.CTkOptionMenu(fps_box, values=["10 fps", "15 fps (Recomendado)", "20 fps", "24 fps"])
        self.gif_fps.set("15 fps (Recomendado)")
        self.gif_fps.pack(fill="x")

        # Largura / Resolução
        res_box = ctk.CTkFrame(row, fg_color="transparent")
        res_box.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(res_box, text="Largura Máxima:", font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(fill="x")
        self.gif_width = ctk.CTkOptionMenu(res_box, values=["320 px (Leve)", "480 px (Médio)", "640 px (HD)"])
        self.gif_width.set("480 px (Médio)")
        self.gif_width.pack(fill="x")

    def _build_mp3_options(self):
        self._clear_dynamic_options()
        row = ctk.CTkFrame(self.dynamic_options_box, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(row, text="Qualidade / Bitrate do Áudio:", font=ctk.CTkFont(size=11, weight="bold"), anchor="w").pack(side="left", padx=(0, 10))
        self.mp3_bitrate = ctk.CTkOptionMenu(row, values=["128 kbps (Padrão)", "192 kbps (Alta)", "256 kbps (Muito Alta)", "320 kbps (Máxima)"])
        self.mp3_bitrate.set("192 kbps (Alta)")
        self.mp3_bitrate.pack(side="left", fill="x", expand=True)

    def _on_type_change(self, value: str):
        if "GIF" in value:
            self._build_gif_options()
            self._update_output_extension(".gif")
        elif "MP3" in value:
            self._build_mp3_options()
            self._update_output_extension(".mp3")
        elif "WAV" in value:
            self._clear_dynamic_options()
            ctk.CTkLabel(self.dynamic_options_box, text="Áudio PCM não comprimido a 16-bit estéreo.", text_color="gray").pack(padx=14, pady=12)
            self._update_output_extension(".wav")
        else:
            self._clear_dynamic_options()
            ctk.CTkLabel(self.dynamic_options_box, text="Reempacota o vídeo para container universal MP4 H.264/AAC.", text_color="gray").pack(padx=14, pady=12)
            self._update_output_extension(".mp4")

    def _update_output_extension(self, new_ext: str):
        current_out = self.output_selector.get_path()
        if current_out:
            p = Path(current_out)
            self.output_selector.set_path(str(p.with_suffix(new_ext)))

    def _on_input_file_selected(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            return
        p = Path(filepath)
        conv_type = self.conv_type_menu.get()
        ext = ".gif" if "GIF" in conv_type else (".mp3" if "MP3" in conv_type else (".wav" if "WAV" in conv_type else ".mp4"))
        suggested_out = str(p.parent / f"{p.stem}_convertido{ext}")
        self.output_selector.set_path(suggested_out)

    def _start_conversion(self):
        input_file = self.input_selector.get_path()
        output_file = self.output_selector.get_path()
        conv_type = self.conv_type_menu.get()

        if not input_file or not Path(input_file).exists():
            self.show_error("Arquivo Inválido", "Selecione o arquivo de entrada.")
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

        self.action_btn.configure(state="disabled", text="Convertendo...")
        self.progress_card.reset("Iniciando processo de conversão...")

        def task_target(on_progress=None, cancel_event=None):
            if "GIF" in conv_type:
                fps_val = int(self.gif_fps.get().split()[0])
                width_val = int(self.gif_width.get().split()[0])
                return media_transformer.convert_to_gif(
                    input_path=input_file,
                    output_path=output_file,
                    fps=fps_val,
                    width=width_val,
                    on_progress=on_progress,
                    cancel_event=cancel_event,
                )
            elif "MP3" in conv_type:
                br_val = self.mp3_bitrate.get().split()[0] + "k"
                return media_transformer.extract_audio(
                    input_path=input_file,
                    output_path=output_file,
                    format_type="mp3",
                    bitrate=br_val,
                    on_progress=on_progress,
                    cancel_event=cancel_event,
                )
            elif "WAV" in conv_type:
                return media_transformer.extract_audio(
                    input_path=input_file,
                    output_path=output_file,
                    format_type="wav",
                    on_progress=on_progress,
                    cancel_event=cancel_event,
                )
            else:
                return media_transformer.convert_container(
                    input_path=input_file,
                    output_path=output_file,
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
            name="media_convert",
            target=task_target,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_success(self, filepath: str):
        self.action_btn.configure(state="normal", text="Iniciar Conversão")
        self.show_success("Conversão Concluída!", f"Arquivo gerado com sucesso:\n{Path(filepath).name}")

    def _on_error(self, exc: Exception):
        self.action_btn.configure(state="normal", text="Iniciar Conversão")
        self.progress_card.update_progress(0.0, "Falha na conversão.")
        self.show_error("Erro na Conversão", str(exc))

    def _cancel_conversion(self):
        task_manager.cancel_task("media_convert")
        self.action_btn.configure(state="normal", text="Iniciar Conversão")
