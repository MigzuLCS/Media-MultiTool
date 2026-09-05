import tkinter as tk
import customtkinter as ctk
from typing import Optional, Callable
from PIL import Image, ImageTk


class WaveformView(ctk.CTkFrame):
    """
    Componente visual que renderiza a forma de onda do áudio (waveform)
    com largura e alinhamento milimétrico idêntico ao TimeRangeSlider.

    Apresenta coloração destacada (ciano/azul vibrante) no trecho selecionado
    para corte e tonalidade atenuada (cinza) nas partes externas, além de
    linhas verticais indicando exatamente os pontos de corte de início e fim.
    """

    def __init__(
        self,
        master,
        height: int = 68,
        pad_x: int = 18,
        duration: float = 30.0,
        start_time: float = 0.0,
        end_time: float = 30.0,
        on_range_change: Optional[Callable[[float, float], None]] = None,
        **kwargs,
    ):
        super().__init__(master, height=height, fg_color="transparent", **kwargs)

        self.widget_height = height
        self.pad_x = pad_x
        self.duration = max(0.1, float(duration))
        self.start_time = max(0.0, float(start_time))
        self.end_time = max(self.start_time, float(end_time))
        self.on_range_change = on_range_change

        # Cache de imagem e máscaras
        self._raw_mask: Optional[Image.Image] = None
        self._active_wave: Optional[Image.Image] = None
        self._inactive_wave: Optional[Image.Image] = None
        self._cached_usable_w: int = 0
        self._cached_h: int = 0
        self._photo: Optional[ImageTk.PhotoImage] = None

        # Estado de interação direta no waveform
        self._dragging_handle: Optional[str] = None

        # Canvas do Tkinter
        self.canvas = tk.Canvas(
            self,
            height=height,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.canvas.pack(fill="both", expand=True)

        self._update_colors()

        # Eventos do Canvas
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

    def _update_colors(self):
        """Define paleta de cores de acordo com o modo claro ou escuro."""
        mode = ctk.get_appearance_mode().lower()
        if mode == "light":
            self.bg_color = "#E5E7EB"
            self.track_bg = "#E5E7EB"
            self.active_bg = (219, 234, 254)       # #DBEAFE
            self.inactive_bg = (229, 231, 235)     # #E5E7EB
            self.active_wave_color = (2, 132, 199) # #0284C7
            self.inactive_wave_color = (156, 163, 175) # #9CA3AF
            self.start_line_color = "#10B981"
            self.end_line_color = "#EF4444"
            self.baseline_color = "#9CA3AF"
        else:
            self.bg_color = "#18181B"
            self.track_bg = "#18181B"
            self.active_bg = (15, 23, 42)          # #0F172A
            self.inactive_bg = (24, 24, 27)        # #18181B
            self.active_wave_color = (56, 189, 248) # #38BDF8
            self.inactive_wave_color = (82, 82, 91) # #52525B
            self.start_line_color = "#059669"
            self.end_line_color = "#DC2626"
            self.baseline_color = "#3F3F46"

        self.canvas.config(bg=self.bg_color)

    def set_duration(self, duration: float):
        """Atualiza a duração total da mídia."""
        self.duration = max(0.1, float(duration))
        self.redraw()

    def set_range(self, start_time: float, end_time: float):
        """Atualiza o trecho selecionado [início, fim] e redesenha o destaque."""
        self.start_time = max(0.0, min(float(start_time), self.duration))
        self.end_time = max(self.start_time, min(float(end_time), self.duration))
        self.redraw()

    def set_raw_waveform(self, raw_img: Optional[Image.Image]):
        """Define a imagem bruta gerada pelo FFmpeg e extrai a máscara de onda."""
        if raw_img is not None:
            if raw_img.mode == "RGBA":
                self._raw_mask = raw_img.split()[3]
            elif raw_img.mode == "L":
                self._raw_mask = raw_img
            else:
                self._raw_mask = raw_img.convert("L")
        else:
            self._raw_mask = None

        self._cached_usable_w = 0
        self.redraw()

    def clear(self):
        """Limpa o waveform e volta para a linha neutra central."""
        self._raw_mask = None
        self._active_wave = None
        self._inactive_wave = None
        self._cached_usable_w = 0
        self.redraw()

    def _on_resize(self, event):
        self.redraw()

    def _x_to_time(self, x: float, usable_w: int) -> float:
        ratio = max(0.0, min(1.0, (x - self.pad_x) / max(1, usable_w)))
        return ratio * self.duration

    def _on_click(self, event):
        w = self.canvas.winfo_width()
        usable_w = max(10, w - 2 * self.pad_x)
        t = self._x_to_time(event.x, usable_w)

        d_start = abs(t - self.start_time)
        d_end = abs(t - self.end_time)

        if d_start <= d_end:
            self._dragging_handle = "start"
            self.start_time = max(0.0, min(t, self.end_time - 0.05))
        else:
            self._dragging_handle = "end"
            self.end_time = max(self.start_time + 0.05, min(t, self.duration))

        self.redraw()
        if self.on_range_change:
            self.on_range_change(self.start_time, self.end_time)

    def _on_drag(self, event):
        if not self._dragging_handle:
            return

        w = self.canvas.winfo_width()
        usable_w = max(10, w - 2 * self.pad_x)
        t = self._x_to_time(event.x, usable_w)

        if self._dragging_handle == "start":
            self.start_time = max(0.0, min(t, self.end_time - 0.05))
        elif self._dragging_handle == "end":
            self.end_time = max(self.start_time + 0.05, min(t, self.duration))

        self.redraw()
        if self.on_range_change:
            self.on_range_change(self.start_time, self.end_time)

    def _on_release(self, event):
        self._dragging_handle = None

    def redraw(self):
        """Renderiza a forma de onda com alinhamento pixel-a-pixel perfeito ao slider."""
        self._update_colors()
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 10 or h <= 10:
            return

        usable_w = max(10, w - 2 * self.pad_x)
        cy = h / 2.0

        if self._raw_mask is None:
            # Sem áudio ou carregando: linha central suave
            self.canvas.create_line(
                self.pad_x, cy, w - self.pad_x, cy,
                fill=self.baseline_color, width=1, tags="baseline"
            )
            return

        # Reconstrói os mapas caso a largura ou altura tenham mudado
        if self._cached_usable_w != usable_w or self._cached_h != h or self._active_wave is None:
            mask_resized = self._raw_mask.resize((usable_w, h), Image.Resampling.BILINEAR)

            # Versão ativa (fundo azul sutil + onda ciano)
            act_img = Image.new("RGB", (usable_w, h), self.active_bg)
            wave_act = Image.new("RGB", (usable_w, h), self.active_wave_color)
            act_img.paste(wave_act, (0, 0), mask_resized)
            self._active_wave = act_img

            # Versão inativa (fundo neutro + onda cinza atenuada)
            inact_img = Image.new("RGB", (usable_w, h), self.inactive_bg)
            wave_inact = Image.new("RGB", (usable_w, h), self.inactive_wave_color)
            inact_img.paste(wave_inact, (0, 0), mask_resized)
            self._inactive_wave = inact_img

            self._cached_usable_w = usable_w
            self._cached_h = h

        # Mapeamento do intervalo de corte selecionado
        dur = max(0.001, self.duration)
        ratio_s = max(0.0, min(1.0, self.start_time / dur))
        ratio_e = max(0.0, min(1.0, self.end_time / dur))
        xs = int(ratio_s * usable_w)
        xe = int(ratio_e * usable_w)

        # Monta a composição da forma de onda
        composite = self._inactive_wave.copy()
        if xe > xs:
            slice_active = self._active_wave.crop((xs, 0, xe, h))
            composite.paste(slice_active, (xs, 0))

        self._photo = ImageTk.PhotoImage(composite)
        self.canvas.create_image(self.pad_x, 0, anchor="nw", image=self._photo, tags="waveform")

        # Marcadores verticais nos limites do corte (conectando-se visualmente às alças do slider)
        x_start = self.pad_x + xs
        x_end = self.pad_x + xe
        self.canvas.create_line(x_start, 0, x_start, h, fill=self.start_line_color, width=1.5, tags="marker_start")
        self.canvas.create_line(x_end, 0, x_end, h, fill=self.end_line_color, width=1.5, tags="marker_end")
