import tkinter as tk
import customtkinter as ctk
from typing import Optional, Callable, Tuple


class TimeRangeSlider(ctk.CTkFrame):
    """
    Componente visual interativo para seleção de intervalo de tempo (início e fim)
    em linha do tempo, estilizado em harmonia com CustomTkinter.
    """

    def __init__(
        self,
        master,
        duration: float = 60.0,
        start_time: float = 0.0,
        end_time: float = 30.0,
        min_gap: float = 0.05,
        on_change: Optional[Callable[[float, float], None]] = None,
        height: int = 68,
        **kwargs,
    ):
        super().__init__(master, height=height, fg_color="transparent", **kwargs)

        self.duration = max(1.0, float(duration))
        self.min_gap = min_gap
        self.on_change = on_change
        self._is_updating_externally = False

        # Clamping inicial
        self.start_time = max(0.0, min(float(start_time), self.duration - self.min_gap))
        self.end_time = max(self.start_time + self.min_gap, min(float(end_time), self.duration))

        # Estado de interação
        self._drag_mode: Optional[str] = None  # 'start', 'end', 'range'
        self._drag_start_x = 0
        self._drag_init_start = 0.0
        self._drag_init_end = 0.0

        # Dimensões e paddings da barra
        self.pad_x = 18
        self.track_height = 8
        self.handle_width = 14
        self.handle_height = 32

        # Configurar Canvas do Tkinter
        self.canvas = tk.Canvas(
            self,
            height=height,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.canvas.pack(fill="both", expand=True)

        # Atualizar cor de fundo do Canvas para coincidir com o tema
        self._update_colors()

        # Eventos
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<Leave>", lambda e: self.canvas.config(cursor=""))

    def _update_colors(self):
        """Define paleta de cores de acordo com o modo de aparência do CustomTkinter."""
        mode = ctk.get_appearance_mode().lower()
        if mode == "light":
            self.bg_color = "#E5E7EB"
            self.track_bg = "#D1D5DB"
            self.range_fill = "#3B82F6"
            self.start_handle_color = "#10B981"
            self.end_handle_color = "#EF4444"
            self.handle_border = "#FFFFFF"
            self.grip_color = "#FFFFFF"
            self.text_color = "#374151"
        else:
            self.bg_color = "#1E1E1E"
            self.track_bg = "#333333"
            self.range_fill = "#2563EB"
            self.start_handle_color = "#059669"
            self.end_handle_color = "#DC2626"
            self.handle_border = "#E5E7EB"
            self.grip_color = "#FFFFFF"
            self.text_color = "#9CA3AF"

        self.canvas.config(bg=self.bg_color)

    def _time_to_x(self, t: float, width: int) -> float:
        """Converte um tempo em segundos para coordenada X no canvas."""
        usable_w = max(10, width - 2 * self.pad_x)
        ratio = max(0.0, min(1.0, t / self.duration))
        return self.pad_x + ratio * usable_w

    def _x_to_time(self, x: float, width: int) -> float:
        """Converte uma coordenada X do canvas para tempo em segundos."""
        usable_w = max(10, width - 2 * self.pad_x)
        ratio = max(0.0, min(1.0, (x - self.pad_x) / usable_w))
        return ratio * self.duration

    @staticmethod
    def format_time_str(seconds: float, include_ms: bool = True) -> str:
        """Formata segundos em HH:MM:SS.mmm (ou HH:MM:SS se include_ms=False)."""
        s = max(0.0, float(seconds))
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        sec = int(s % 60)
        ms = int(round((s - int(s)) * 1000))
        if ms >= 1000:
            sec += 1
            ms = 0
            if sec >= 60:
                m += 1
                sec = 0
                if m >= 60:
                    h += 1
                    m = 0
        if include_ms:
            return f"{h:02d}:{m:02d}:{sec:02d}.{ms:03d}"
        return f"{h:02d}:{m:02d}:{sec:02d}"

    def redraw(self):
        """Redesenha a pista, intervalo selecionado, alças e rótulos de tempo."""
        self._update_colors()
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 10 or h <= 10:
            return

        cy = h / 2.0
        x_start = self._time_to_x(self.start_time, w)
        x_end = self._time_to_x(self.end_time, w)

        # 1. Pista de fundo (Timeline total)
        track_y1 = cy - self.track_height / 2
        track_y2 = cy + self.track_height / 2
        r = self.track_height / 2

        # Pista inativa inteira
        self._draw_round_rect(
            self.pad_x, track_y1, w - self.pad_x, track_y2,
            radius=r, fill=self.track_bg, tags="track"
        )

        # 2. Pista de seleção ativa (Range selecionado)
        if x_end > x_start:
            self.canvas.create_rectangle(
                x_start, track_y1, x_end, track_y2,
                fill=self.range_fill, outline="", tags="selected_bar"
            )

        # 3. Marcadores de tempo nos extremos da barra (00:00:00.000 e Duração Total)
        self.canvas.create_text(
            self.pad_x, h - 8,
            text=self.format_time_str(0.0, include_ms=True),
            anchor="sw",
            fill=self.text_color,
            font=("Segoe UI", 8),
            tags="time_labels"
        )
        self.canvas.create_text(
            w - self.pad_x, h - 8,
            text=self.format_time_str(self.duration, include_ms=True),
            anchor="se",
            fill=self.text_color,
            font=("Segoe UI", 8),
            tags="time_labels"
        )

        # 4. Alça Inicial (Start Handle)
        self._draw_handle(
            x_start, cy,
            color=self.start_handle_color,
            label=f"Início: {self.format_time_str(self.start_time, include_ms=True)}",
            tag="handle_start",
            label_anchor="s",
            label_y=cy - self.handle_height / 2 - 4
        )

        # 5. Alça Final (End Handle)
        self._draw_handle(
            x_end, cy,
            color=self.end_handle_color,
            label=f"Fim: {self.format_time_str(self.end_time, include_ms=True)}",
            tag="handle_end",
            label_anchor="s",
            label_y=cy - self.handle_height / 2 - 4
        )

    def _draw_round_rect(self, x1, y1, x2, y2, radius=4, **kwargs):
        """Desenha um retângulo arredondado no canvas."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_handle(self, x: float, cy: float, color: str, label: str, tag: str, label_anchor: str, label_y: float):
        """Desenha uma alça visual com indicador e tooltip de tempo."""
        hw = self.handle_width / 2
        hh = self.handle_height / 2

        # Corpo da alça (Pill arredondado)
        self._draw_round_rect(
            x - hw, cy - hh, x + hw, cy + hh,
            radius=4,
            fill=color,
            outline=self.handle_border,
            width=1.5,
            tags=(tag, "handle")
        )

        # Linhas de aderência central (grip lines)
        self.canvas.create_line(
            x - 2, cy - 6, x - 2, cy + 6,
            fill=self.grip_color, width=1, tags=(tag, "handle")
        )
        self.canvas.create_line(
            x + 2, cy - 6, x + 2, cy + 6,
            fill=self.grip_color, width=1, tags=(tag, "handle")
        )

        # Texto de tempo acima da alça
        w = self.canvas.winfo_width()
        # Ajustar para não sair da tela
        clamped_x = max(self.pad_x + 20, min(x, w - self.pad_x - 20))
        self.canvas.create_text(
            clamped_x, label_y,
            text=label,
            anchor=label_anchor,
            fill=self.handle_border,
            font=("Segoe UI", 8, "bold"),
            tags=(tag, "time_tag")
        )

    def _on_resize(self, event):
        self.redraw()

    def _on_hover(self, event):
        """Muda o cursor do mouse conforme a região sob o ponteiro."""
        if self._drag_mode is not None:
            return

        w = self.canvas.winfo_width()
        x_start = self._time_to_x(self.start_time, w)
        x_end = self._time_to_x(self.end_time, w)
        hw = self.handle_width / 2 + 3

        if abs(event.x - x_start) <= hw:
            self.canvas.config(cursor="sb_h_double_arrow")
        elif abs(event.x - x_end) <= hw:
            self.canvas.config(cursor="sb_h_double_arrow")
        elif x_start < event.x < x_end:
            self.canvas.config(cursor="fleur")
        else:
            self.canvas.config(cursor="hand2")

    def _on_press(self, event):
        """Inicia o arrasto da alça ou da barra de seleção."""
        w = self.canvas.winfo_width()
        x_start = self._time_to_x(self.start_time, w)
        x_end = self._time_to_x(self.end_time, w)
        hw = self.handle_width / 2 + 4

        self._drag_start_x = event.x
        self._drag_init_start = self.start_time
        self._drag_init_end = self.end_time

        if abs(event.x - x_start) <= hw:
            self._drag_mode = "start"
        elif abs(event.x - x_end) <= hw:
            self._drag_mode = "end"
        elif x_start < event.x < x_end:
            self._drag_mode = "range"
        else:
            # Clique fora: move a alça mais próxima até o ponto clicado
            t_click = self._x_to_time(event.x, w)
            dist_start = abs(t_click - self.start_time)
            dist_end = abs(t_click - self.end_time)
            if dist_start <= dist_end:
                self.start_time = max(0.0, min(t_click, self.end_time - self.min_gap))
                self._drag_mode = "start"
            else:
                self.end_time = min(self.duration, max(t_click, self.start_time + self.min_gap))
                self._drag_mode = "end"
            self.redraw()
            self._notify_change()

    def _on_drag(self, event):
        """Processa o movimento do mouse para atualizar os limites de corte."""
        if not self._drag_mode:
            return

        w = self.canvas.winfo_width()
        if self._drag_mode == "start":
            t = self._x_to_time(event.x, w)
            self.start_time = max(0.0, min(t, self.end_time - self.min_gap))
        elif self._drag_mode == "end":
            t = self._x_to_time(event.x, w)
            self.end_time = min(self.duration, max(t, self.start_time + self.min_gap))
        elif self._drag_mode == "range":
            dt = self._x_to_time(event.x, w) - self._x_to_time(self._drag_start_x, w)
            duration_interval = self._drag_init_end - self._drag_init_start
            new_start = self._drag_init_start + dt
            new_end = self._drag_init_end + dt

            if new_start < 0.0:
                new_start = 0.0
                new_end = duration_interval
            elif new_end > self.duration:
                new_end = self.duration
                new_start = self.duration - duration_interval

            self.start_time = new_start
            self.end_time = new_end

        self.redraw()
        self._notify_change()

    def _on_release(self, event):
        """Finaliza a operação de arrasto."""
        self._drag_mode = None
        self._on_hover(event)

    def _notify_change(self):
        """Dispara callback externo caso não seja uma atualização externa."""
        if not self._is_updating_externally and self.on_change:
            self.on_change(self.start_time, self.end_time)

    # === Métodos Públicos ===

    def set_duration(self, duration: float, reset_range: bool = True):
        """Atualiza a duração total do arquivo carregado."""
        self.duration = max(1.0, float(duration))
        if reset_range:
            self.start_time = 0.0
            self.end_time = self.duration
        else:
            self.start_time = max(0.0, min(self.start_time, self.duration - self.min_gap))
            self.end_time = max(self.start_time + self.min_gap, min(self.end_time, self.duration))

        self.redraw()
        self._notify_change()

    def set_range(self, start_sec: float, end_sec: float):
        """Atualiza programmaticamente o intervalo de corte sem disparar loop de eventos."""
        self._is_updating_externally = True
        try:
            st = max(0.0, min(float(start_sec), self.duration - self.min_gap))
            et = max(st + self.min_gap, min(float(end_sec), self.duration))
            self.start_time = st
            self.end_time = et
            self.redraw()
        finally:
            self._is_updating_externally = False

    def get_range(self) -> Tuple[float, float]:
        """Retorna (start_time, end_time) em segundos."""
        return (self.start_time, self.end_time)
