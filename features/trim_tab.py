import os
import threading
from pathlib import Path
from typing import Optional
import customtkinter as ctk
from PIL import Image

from features.base import BaseFeature
from ui.components.file_selector import FileSelector
from ui.components.progress_card import ProgressCard
from ui.components.range_slider import TimeRangeSlider
from ui.components.waveform_view import WaveformView
from core.ffmpeg_manager import ffmpeg_manager
from core.transformer import media_transformer
from core.tasks import task_manager


class TrimTab(BaseFeature):
    id = "trim"
    title = "Corte Rápido"
    icon = "✂"
    description = "Corte trechos de vídeos instantaneamente sem perder qualidade ou com precisão de frame."
    category = "Vídeo"
    requires_ffmpeg = True
    estimated_size_mb = 5.0

    def __init__(self, master: ctk.CTkFrame, main_window):
        super().__init__(master, main_window)
        self._syncing_from_slider = False
        self._syncing_from_entries = False
        self._has_video = False
        self._start_preview_req_id = 0
        self._end_preview_req_id = 0
        self._debounce_timer_start = None
        self._debounce_timer_end = None
        self._start_ctk_img = None
        self._end_ctk_img = None
        self._waveform_req_id = 0
        self._waveform_ctk_img = None

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

        # Card de Seleção e Linha do Tempo de Corte
        self.timeline_card = ctk.CTkFrame(self.frame)
        self.timeline_card.pack(fill="x", pady=(0, 16), padx=2)

        # Cabeçalho da área de corte
        tl_header = ctk.CTkFrame(self.timeline_card, fg_color="transparent")
        tl_header.pack(fill="x", padx=14, pady=(12, 4))

        ctk.CTkLabel(
            tl_header,
            text="Linha do Tempo & Seleção de Corte",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            tl_header,
            text="(Arraste as alças verde/vermelha ou o centro da barra)",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        ).pack(side="left", padx=(8, 0))

        # Miniaturas de Prévia Lado a Lado (Início e Fim) para Vídeos
        self.previews_frame = ctk.CTkFrame(self.timeline_card, fg_color="transparent")
        self.previews_frame.pack(fill="x", padx=14, pady=(4, 10))

        # Card Miniatura Inicial (Verde)
        self.start_preview_card = ctk.CTkFrame(self.previews_frame, corner_radius=8, fg_color=("gray85", "gray17"))
        self.start_preview_card.pack(side="left", fill="both", expand=True, padx=(0, 7))

        self.start_preview_title = ctk.CTkLabel(
            self.start_preview_card,
            text="● Frame de Início (00:00:00)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#059669", "#10b981"),
            anchor="w",
        )
        self.start_preview_title.pack(fill="x", padx=10, pady=(8, 4))

        self.start_preview_lbl = ctk.CTkLabel(
            self.start_preview_card,
            text="Nenhum vídeo selecionado",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            height=135,
            fg_color=("gray80", "gray13"),
            corner_radius=6,
        )
        self.start_preview_lbl.pack(fill="x", padx=10, pady=(0, 10))

        # Card Miniatura Final (Vermelho)
        self.end_preview_card = ctk.CTkFrame(self.previews_frame, corner_radius=8, fg_color=("gray85", "gray17"))
        self.end_preview_card.pack(side="right", fill="both", expand=True, padx=(7, 0))

        self.end_preview_title = ctk.CTkLabel(
            self.end_preview_card,
            text="● Frame de Fim (00:00:30)",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#dc2626", "#ef4444"),
            anchor="w",
        )
        self.end_preview_title.pack(fill="x", padx=10, pady=(8, 4))

        self.end_preview_lbl = ctk.CTkLabel(
            self.end_preview_card,
            text="Nenhum vídeo selecionado",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            height=135,
            fg_color=("gray80", "gray13"),
            corner_radius=6,
        )
        self.end_preview_lbl.pack(fill="x", padx=10, pady=(0, 10))

        # Forma de Onda (Waveform) - sempre visível acima da barra deslizante (sem textos)
        self.waveform_view = WaveformView(
            self.timeline_card,
            height=68,
            pad_x=18,
            duration=30.0,
            start_time=0.0,
            end_time=30.0,
            on_range_change=self._on_waveform_range_changed,
        )
        self.waveform_view.pack(fill="x", padx=14, pady=(2, 2))
        self.waveform_card = self.waveform_view  # Alias de compatibilidade

        # Slider visual de linha do tempo
        self.range_slider = TimeRangeSlider(
            self.timeline_card,
            duration=30.0,
            start_time=0.0,
            end_time=30.0,
            on_change=self._on_slider_range_changed,
            height=68,
        )
        self.range_slider.pack(fill="x", padx=14, pady=(2, 6))

        # Indicador/Resumo em tempo real do trecho selecionado
        self.selection_summary_lbl = ctk.CTkLabel(
            self.timeline_card,
            text="✂️ Trecho Selecionado: 00:00:00 até 00:00:30 • Duração do corte: 00:00:30",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.selection_summary_lbl.pack(fill="x", padx=14, pady=(0, 8))

        # Divisor suave
        sep = ctk.CTkFrame(self.timeline_card, height=1, fg_color=("gray80", "gray30"))
        sep.pack(fill="x", padx=14, pady=(0, 10))

        # Configuração de Pontos de Corte (Início e Fim com ajuste exato e botões rápidos)
        time_frame = ctk.CTkFrame(self.timeline_card, fg_color="transparent")
        time_frame.pack(fill="x", padx=14, pady=(0, 12))

        # Bloco Início
        start_box = ctk.CTkFrame(time_frame, fg_color="transparent")
        start_box.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkLabel(
            start_box,
            text="Tempo Inicial (HH:MM:SS.mmm):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        start_controls = ctk.CTkFrame(start_box, fg_color="transparent")
        start_controls.pack(fill="x")

        self.start_entry = ctk.CTkEntry(start_controls, placeholder_text="00:00:00.000")
        self.start_entry.insert(0, "00:00:00.000")
        self.start_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.start_entry.bind("<KeyRelease>", lambda e: self._on_entry_changed())
        self.start_entry.bind("<FocusOut>", lambda e: self._on_entry_focus_out())
        self.start_entry.bind("<Return>", lambda e: self._on_entry_focus_out())

        ctk.CTkButton(
            start_controls,
            text="0s",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._reset_start_to_zero,
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            start_controls,
            text="-1s",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_start(-1.0),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            start_controls,
            text="-0.1s",
            width=36,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_start(-0.1),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            start_controls,
            text="+0.1s",
            width=36,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_start(0.1),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            start_controls,
            text="+1s",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_start(1.0),
        ).pack(side="left", padx=1)

        # Bloco Fim
        end_box = ctk.CTkFrame(time_frame, fg_color="transparent")
        end_box.pack(side="right", fill="x", expand=True, padx=(10, 0))

        ctk.CTkLabel(
            end_box,
            text="Tempo Final (HH:MM:SS.mmm):",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        end_controls = ctk.CTkFrame(end_box, fg_color="transparent")
        end_controls.pack(fill="x")

        self.end_entry = ctk.CTkEntry(end_controls, placeholder_text="00:00:30.000")
        self.end_entry.insert(0, "00:00:30.000")
        self.end_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.end_entry.bind("<KeyRelease>", lambda e: self._on_entry_changed())
        self.end_entry.bind("<FocusOut>", lambda e: self._on_entry_focus_out())
        self.end_entry.bind("<Return>", lambda e: self._on_entry_focus_out())

        ctk.CTkButton(
            end_controls,
            text="-1s",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_end(-1.0),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            end_controls,
            text="-0.1s",
            width=36,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_end(-0.1),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            end_controls,
            text="+0.1s",
            width=36,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_end(0.1),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            end_controls,
            text="+1s",
            width=28,
            height=28,
            font=ctk.CTkFont(size=11),
            command=lambda: self._adjust_end(1.0),
        ).pack(side="left", padx=1)

        ctk.CTkButton(
            end_controls,
            text="Máx",
            width=32,
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._set_end_to_max,
        ).pack(side="left", padx=1)

        # Modo de Corte
        mode_box = ctk.CTkFrame(self.frame)
        mode_box.pack(fill="x", pady=(0, 16), padx=2)

        ctk.CTkLabel(
            mode_box,
            text="Modo de Operação de Corte:",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 4))

        self.lossless_switch = ctk.CTkSwitch(
            mode_box,
            text="⚡ Modo Rápido por Keyframe (-c copy: instantâneo, mas corta no frame-chave mais próximo)",
            font=ctk.CTkFont(size=12),
        )
        self.lossless_switch.deselect()  # Desmarcado por padrão = Modo Preciso de Frame
        self.lossless_switch.pack(fill="x", padx=14, pady=(4, 4))

        ctk.CTkLabel(
            mode_box,
            text="💡 Recomendado: Mantenha desmarcado para corte exato no milissegundo e frame selecionados. Marque apenas para exportação ultrarrápida sem recodificar.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 10))

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

    def _request_preview(self, is_start: bool, timestamp_sec: float):
        """Agenda atualização assíncrona da miniatura com debounce para máxima fluidez."""
        filepath = self.input_selector.get_path()
        if not filepath or not Path(filepath).exists() or not self._has_video:
            return

        if is_start:
            self._start_preview_req_id += 1
            req_id = self._start_preview_req_id
            if self._debounce_timer_start:
                try:
                    self.frame.after_cancel(self._debounce_timer_start)
                except Exception:
                    pass
            self._debounce_timer_start = self.frame.after(
                80, lambda: self._spawn_preview_worker(filepath, timestamp_sec, is_start=True, req_id=req_id)
            )
        else:
            self._end_preview_req_id += 1
            req_id = self._end_preview_req_id
            if self._debounce_timer_end:
                try:
                    self.frame.after_cancel(self._debounce_timer_end)
                except Exception:
                    pass
            self._debounce_timer_end = self.frame.after(
                80, lambda: self._spawn_preview_worker(filepath, timestamp_sec, is_start=False, req_id=req_id)
            )

    def _spawn_preview_worker(self, filepath: str, timestamp_sec: float, is_start: bool, req_id: int):
        def worker():
            img = ffmpeg_manager.extract_frame(filepath, timestamp_sec, width=240, height=135)
            self.dispatch_gui(lambda: self._apply_preview_image(img, is_start, req_id, timestamp_sec))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_preview_image(self, img: Optional[Image.Image], is_start: bool, req_id: int, timestamp_sec: float):
        current_req = self._start_preview_req_id if is_start else self._end_preview_req_id
        if req_id != current_req:
            return

        time_str = TimeRangeSlider.format_time_str(timestamp_sec)
        if is_start:
            self.start_preview_title.configure(text=f"● Frame de Início ({time_str})")
            if img:
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                self.start_preview_lbl.configure(image=ctk_img, text="")
                self._start_ctk_img = ctk_img
            else:
                self.start_preview_lbl.configure(image="", text="Sem sinal de vídeo")
        else:
            self.end_preview_title.configure(text=f"● Frame de Fim ({time_str})")
            if img:
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                self.end_preview_lbl.configure(image=ctk_img, text="")
                self._end_ctk_img = ctk_img
            else:
                self.end_preview_lbl.configure(image="", text="Sem sinal de vídeo")

    def _request_waveform(self, filepath: str):
        """Requisita de forma assíncrona a geração da forma de onda para o WaveformView."""
        self._waveform_req_id += 1
        req_id = self._waveform_req_id

        def worker():
            img = ffmpeg_manager.extract_audio_waveform(
                filepath, width=1200, height=68, color="#FFFFFF", raw_rgba=True
            )
            self.dispatch_gui(lambda: self._apply_waveform_image(img, req_id))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_waveform_image(self, img: Optional[Image.Image], req_id: int):
        if req_id != self._waveform_req_id:
            return

        if img:
            self.waveform_view.set_raw_waveform(img)
        else:
            self.waveform_view.clear()

    def _on_waveform_range_changed(self, start_sec: float, end_sec: float):
        """Sincroniza o slider e campos quando o usuário clica ou arrasta diretamente no waveform."""
        if self._syncing_from_entries or self._syncing_from_slider:
            return
        self.range_slider.set_range(start_sec, end_sec)
        self._on_slider_range_changed(start_sec, end_sec)

    def _on_slider_range_changed(self, start_sec: float, end_sec: float):
        """Atualiza os campos de texto, resumo e waveform quando o usuário move o slider visual."""
        if self._syncing_from_entries:
            return

        self._syncing_from_slider = True
        try:
            start_str = TimeRangeSlider.format_time_str(start_sec, include_ms=True)
            end_str = TimeRangeSlider.format_time_str(end_sec, include_ms=True)

            self.start_entry.delete(0, "end")
            self.start_entry.insert(0, start_str)

            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, end_str)

            self._update_summary_label(start_sec, end_sec)
            self.waveform_view.set_range(start_sec, end_sec)
            self._request_preview(is_start=True, timestamp_sec=start_sec)
            self._request_preview(is_start=False, timestamp_sec=end_sec)
        finally:
            self._syncing_from_slider = False

    def _on_entry_changed(self):
        """Sincroniza o slider e waveform quando o usuário digita nos campos de texto."""
        if self._syncing_from_slider:
            return

        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()

        start_sec = media_transformer._parse_time_to_seconds(start_text)
        end_sec = media_transformer._parse_time_to_seconds(end_text)

        if end_sec > start_sec and end_sec <= self.range_slider.duration:
            self._syncing_from_entries = True
            try:
                self.range_slider.set_range(start_sec, end_sec)
                self.waveform_view.set_range(start_sec, end_sec)
                self._update_summary_label(start_sec, end_sec)
                self._request_preview(is_start=True, timestamp_sec=start_sec)
                self._request_preview(is_start=False, timestamp_sec=end_sec)
            finally:
                self._syncing_from_entries = False

    def _on_entry_focus_out(self):
        """Ao sair do campo ou pressionar Enter, formata e valida os tempos."""
        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()

        start_sec = media_transformer._parse_time_to_seconds(start_text)
        end_sec = media_transformer._parse_time_to_seconds(end_text)

        max_dur = self.range_slider.duration
        start_sec = max(0.0, min(start_sec, max_dur - self.range_slider.min_gap))
        end_sec = max(start_sec + self.range_slider.min_gap, min(end_sec, max_dur))

        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, TimeRangeSlider.format_time_str(start_sec, include_ms=True))

        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, TimeRangeSlider.format_time_str(end_sec, include_ms=True))

        self.range_slider.set_range(start_sec, end_sec)
        self.waveform_view.set_range(start_sec, end_sec)
        self._update_summary_label(start_sec, end_sec)
        self._request_preview(is_start=True, timestamp_sec=start_sec)
        self._request_preview(is_start=False, timestamp_sec=end_sec)

    def _update_summary_label(self, start_sec: float, end_sec: float):
        """Atualiza a mensagem descritiva de duração selecionada com milissegundos."""
        cut_duration = max(0.0, end_sec - start_sec)
        start_str = TimeRangeSlider.format_time_str(start_sec, include_ms=True)
        end_str = TimeRangeSlider.format_time_str(end_sec, include_ms=True)
        dur_str = TimeRangeSlider.format_time_str(cut_duration, include_ms=True)
        tot_str = TimeRangeSlider.format_time_str(self.range_slider.duration, include_ms=True)

        summary = f"✂️ Trecho Selecionado: {start_str} até {end_str} • Duração do corte: {dur_str} (de {tot_str} total)"
        self.selection_summary_lbl.configure(text=summary)

    def _adjust_start(self, delta: float):
        start_sec = media_transformer._parse_time_to_seconds(self.start_entry.get())
        end_sec = media_transformer._parse_time_to_seconds(self.end_entry.get())
        new_start = max(0.0, min(start_sec + delta, end_sec - self.range_slider.min_gap))
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, TimeRangeSlider.format_time_str(new_start, include_ms=True))
        self._on_entry_focus_out()

    def _adjust_end(self, delta: float):
        start_sec = media_transformer._parse_time_to_seconds(self.start_entry.get())
        end_sec = media_transformer._parse_time_to_seconds(self.end_entry.get())
        new_end = max(start_sec + self.range_slider.min_gap, min(end_sec + delta, self.range_slider.duration))
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, TimeRangeSlider.format_time_str(new_end, include_ms=True))
        self._on_entry_focus_out()

    def _reset_start_to_zero(self):
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, "00:00:00.000")
        self._on_entry_focus_out()

    def _set_end_to_max(self):
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, TimeRangeSlider.format_time_str(self.range_slider.duration, include_ms=True))
        self._on_entry_focus_out()

    def _on_input_file_selected(self, filepath: str):
        if not filepath or not Path(filepath).exists():
            return

        p = Path(filepath)
        suggested_out = str(p.parent / f"{p.stem}_cortado{p.suffix}")
        self.output_selector.set_path(suggested_out)

        info = ffmpeg_manager.get_media_info(filepath)
        dur = info.get("duration_str", "00:00:00")
        dur_sec = info.get("duration", 0.0)
        size = info.get("size_mb", 0.0)
        res = info.get("resolution", "N/A")
        self._has_video = info.get("has_video", False)

        btn_text = "Cortar Vídeo Agora" if self._has_video else "Cortar Áudio Agora"
        self.action_btn.configure(text=btn_text)

        # Limpar imediatamente o estado visual anterior para garantir transição limpa
        self.waveform_view.clear()
        self.start_preview_lbl.configure(image="", text="Carregando frame...")
        self.end_preview_lbl.configure(image="", text="Carregando frame...")
        self.start_preview_title.configure(text="● Frame de Início (00:00:00)")
        self.end_preview_title.configure(text="● Frame de Fim (00:00:00)")

        if dur_sec > 0.0:
            dur_formatted = TimeRangeSlider.format_time_str(dur_sec, include_ms=True)
            self.end_preview_title.configure(text=f"● Frame de Fim ({TimeRangeSlider.format_time_str(dur_sec)})")
            self.range_slider.set_duration(dur_sec, reset_range=True)
            self.waveform_view.set_duration(dur_sec)
            self.waveform_view.set_range(0.0, dur_sec)
            self.start_entry.delete(0, "end")
            self.start_entry.insert(0, "00:00:00.000")
            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, dur_formatted)
            self._update_summary_label(0.0, dur_sec)

        if self._has_video:
            try:
                self.previews_frame.pack(fill="x", padx=14, pady=(4, 8), before=self.waveform_view)
            except Exception:
                self.previews_frame.pack(fill="x", padx=14, pady=(4, 8))
            if dur_sec > 0.0:
                self._request_preview(is_start=True, timestamp_sec=0.0)
                self._request_preview(is_start=False, timestamp_sec=dur_sec)
        else:
            self.previews_frame.pack_forget()

        # O waveform é sempre exibido acima da barra deslizante (para áudio e vídeo)
        if dur_sec > 0.0 and (info.get("has_audio", False) or not self._has_video):
            self._request_waveform(filepath)
        else:
            self.waveform_view.clear()

        info_text = f"⏱️ Mídia Detectada: Duração Total: {dur} | Tamanho: {size:.1f} MB | Resolução: {res}"
        self.info_lbl.configure(text=info_text, text_color=("black", "white"))

    def _start_trim(self):
        input_file = self.input_selector.get_path()
        output_file = self.output_selector.get_path()
        start_t = self.start_entry.get().strip() or "00:00:00.000"
        end_t = self.end_entry.get().strip() or "00:00:10.000"

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
            self.dispatch_gui(lambda: self.progress_card.update_progress(frac, msg))

        def on_succ(res):
            self.dispatch_gui(lambda: self._on_success(res))

        def on_err(exc):
            self.dispatch_gui(lambda: self._on_error(exc))

        task_manager.run_task(
            name="video_trim",
            target=task_target,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_success(self, filepath: str):
        btn_text = "Cortar Vídeo Agora" if self._has_video else "Cortar Áudio Agora"
        self.action_btn.configure(state="normal", text=btn_text)
        self.show_success("Corte Concluído!", f"Trecho salvo com sucesso em:\n{Path(filepath).name}")

    def _on_error(self, exc: Exception):
        btn_text = "Cortar Vídeo Agora" if self._has_video else "Cortar Áudio Agora"
        self.action_btn.configure(state="normal", text=btn_text)
        self.progress_card.update_progress(0.0, "Falha ao cortar mídia.")
        self.show_error("Erro no Corte", str(exc))

    def _cancel_trim(self):
        task_manager.cancel_task("video_trim")
        btn_text = "Cortar Vídeo Agora" if self._has_video else "Cortar Áudio Agora"
        self.action_btn.configure(state="normal", text=btn_text)
