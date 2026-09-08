import os
import sys
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import Optional, List, Dict, Any

from features.base import BaseFeature
from ui.components.file_selector import FileSelector
from core.disk_scanner import (
    DiskScanner,
    ScanResult,
    FileItem,
    DirItem,
    ExtensionStat,
    format_size,
    get_windows_drives,
    reveal_in_explorer,
    send_to_recycle_bin,
    compute_squarified_treemap,
)
from core.tasks import task_manager, Task


def format_display_name(name: str, max_len: int = 50) -> str:
    """Trunca nomes muito longos preservando o início e o final com reticências no meio."""
    if len(name) <= max_len:
        return name
    half = (max_len - 3) // 2
    return f"{name[:half]}...{name[-half:]}"


class DiskAnalyzerTab(BaseFeature):
    id = "disk_analyzer"
    title = "Analisador de Disco"
    icon = "🗂"
    description = "Analise o armazenamento do computador, maiores pastas e arquivos no estilo WinDirStat."
    category = "Armazenamento"
    requires_ffmpeg = False
    estimated_size_mb = 1.0

    def __init__(self, master: ctk.CTkFrame, main_window):
        super().__init__(master, main_window)
        self.current_task: Optional[Task] = None
        self.last_scan_result: Optional[ScanResult] = None
        self.current_browsed_dir: Optional[DirItem] = None
        self.history_dirs: List[DirItem] = []
        self._treemap_items: List[Dict[str, Any]] = []
        self._treemap_rects = []
        self._hover_rect_id = None
        self._selected_item = None

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Configurar layout vertical flexível
        self.frame.grid_rowconfigure(4, weight=1)
        self.frame.grid_columnconfigure(0, weight=1)

        # 1. Cabeçalho
        header_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text="🗂️ Analisador de Disco & Armazenamento",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x")

        desc_lbl = ctk.CTkLabel(
            header_frame,
            text="Descubra onde seu espaço está sendo consumido com visão de subpastas, maiores arquivos e mapa visual estilo WinDirStat.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(2, 0))

        # 2. Painel de Seleção de Pasta / Unidades
        control_frame = ctk.CTkFrame(self.frame)
        control_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Linha de Unidades Rápidas
        drives_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        drives_row.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            drives_row,
            text="Unidades Detectadas:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        drives = get_windows_drives()
        for drive in drives:
            d_btn = ctk.CTkButton(
                drives_row,
                text=f"💾 {drive}",
                width=75,
                height=28,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda d=drive: self._select_drive(d),
            )
            d_btn.pack(side="left", padx=4)

        # Seletor de Pasta Customizada
        self.folder_selector = FileSelector(
            control_frame,
            label="Ou selecione uma pasta específica para escanear:",
            mode="dir",
            default_path=drives[0] if drives else "",
        )
        self.folder_selector.pack(fill="x", padx=14, pady=(4, 10))

        # Botões de Ação
        actions_row = ctk.CTkFrame(control_frame, fg_color="transparent")
        actions_row.pack(fill="x", padx=14, pady=(0, 12))

        self.btn_scan = ctk.CTkButton(
            actions_row,
            text="▶ Iniciar Varredura",
            height=36,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_scan,
        )
        self.btn_scan.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_cancel = ctk.CTkButton(
            actions_row,
            text="⏹ Cancelar",
            height=36,
            width=120,
            state="disabled",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._cancel_scan,
        )
        self.btn_cancel.pack(side="right")

        # 3. Barra de Progresso e Status em Tempo Real
        self.progress_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.progress_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", pady=(0, 4))
        self.progress_bar.set(0)

        self.lbl_status = ctk.CTkLabel(
            self.progress_frame,
            text="Pronto para analisar. Escolha um drive ou pasta e clique em Iniciar.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.lbl_status.pack(fill="x")

        # 4. Cards de Métricas Gerais (Overview)
        self.metrics_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.metrics_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.metrics_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_size = self._create_metric_card(self.metrics_frame, 0, "Espaço Total", "---", "💾")
        self.card_files = self._create_metric_card(self.metrics_frame, 1, "Arquivos", "---", "📄")
        self.card_dirs = self._create_metric_card(self.metrics_frame, 2, "Pastas", "---", "📁")
        self.card_time = self._create_metric_card(self.metrics_frame, 3, "Tempo", "---", "⏱️")

        # 5. Abas de Conteúdo no Estilo WinDirStat
        self.tabview = ctk.CTkTabview(self.frame)
        self.tabview.grid(row=4, column=0, sticky="nsew")

        self.tab_dirs = self.tabview.add("📁 Subpastas")
        self.tab_files = self.tabview.add("📄 Maiores Arquivos")
        self.tab_exts = self.tabview.add("📊 Tipos de Arquivo")
        self.tab_treemap = self.tabview.add("🗺️ Mapa Treemap")

        self._build_subfolders_tab()
        self._build_top_files_tab()
        self._build_extensions_tab()
        self._build_treemap_tab()

        return self.frame

    def _create_metric_card(self, parent, col: int, title: str, init_val: str, icon: str):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, padx=4, sticky="ew")

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 2))

        ctk.CTkLabel(top_row, text=icon, font=ctk.CTkFont(size=14)).pack(side="left", padx=(0, 6))
        ctk.CTkLabel(
            top_row,
            text=title,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="gray",
        ).pack(side="left")

        val_lbl = ctk.CTkLabel(
            card,
            text=init_val,
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        val_lbl.pack(anchor="w", padx=12, pady=(0, 8))
        return val_lbl

    # -------------------------------------------------------------
    # Construção das Abas
    # -------------------------------------------------------------

    def _build_subfolders_tab(self):
        """Aba 1: Lista de subpastas com barras proporcionais e navegação."""
        # Topo da aba: Navegação (caminho atual + botão voltar)
        nav_frame = ctk.CTkFrame(self.tab_dirs, fg_color="transparent")
        nav_frame.pack(fill="x", padx=8, pady=(8, 6))

        self.btn_dir_back = ctk.CTkButton(
            nav_frame,
            text="⬅ Voltar",
            width=70,
            height=28,
            state="disabled",
            command=self._on_dir_back,
        )
        self.btn_dir_back.pack(side="left", padx=(0, 8))

        self.lbl_current_path = ctk.CTkLabel(
            nav_frame,
            text="Pasta Atual: (nenhuma)",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.lbl_current_path.pack(side="left", fill="x", expand=True)

        # Lista com scroll
        self.subdirs_scroll = ctk.CTkScrollableFrame(self.tab_dirs)
        self.subdirs_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_subdirs_empty = ctk.CTkLabel(
            self.subdirs_scroll,
            text="Nenhuma pasta analisada ainda. Inicie uma varredura para visualizar as subpastas.",
            text_color="gray",
        )
        self.lbl_subdirs_empty.pack(pady=40)

    def _build_top_files_tab(self):
        """Aba 2: Ranking dos maiores arquivos encontrados com ações."""
        top_bar = ctk.CTkFrame(self.tab_files, fg_color="transparent")
        top_bar.pack(fill="x", padx=8, pady=(8, 6))

        ctk.CTkLabel(
            top_bar,
            text="Top maiores arquivos encontrados em todo o escaneamento:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")

        self.files_scroll = ctk.CTkScrollableFrame(self.tab_files)
        self.files_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_files_empty = ctk.CTkLabel(
            self.files_scroll,
            text="Nenhum arquivo listado. Inicie uma varredura.",
            text_color="gray",
        )
        self.lbl_files_empty.pack(pady=40)

    def _build_extensions_tab(self):
        """Aba 3: Distribuição por extensão com cores e percentual."""
        top_bar = ctk.CTkFrame(self.tab_exts, fg_color="transparent")
        top_bar.pack(fill="x", padx=8, pady=(8, 6))

        ctk.CTkLabel(
            top_bar,
            text="Distribuição de armazenamento por extensão de arquivo:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left")

        self.exts_scroll = ctk.CTkScrollableFrame(self.tab_exts)
        self.exts_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_exts_empty = ctk.CTkLabel(
            self.exts_scroll,
            text="Nenhum dado de extensão disponível.",
            text_color="gray",
        )
        self.lbl_exts_empty.pack(pady=40)

    def _build_treemap_tab(self):
        """Aba 4: Mapa de blocos estilo WinDirStat desenhado em Canvas."""
        top_bar = ctk.CTkFrame(self.tab_treemap, fg_color="transparent")
        top_bar.pack(fill="x", padx=8, pady=(6, 4))

        self.lbl_treemap_hover = ctk.CTkLabel(
            top_bar,
            text="Passe o mouse sobre os blocos para inspecionar | Dê duplo clique para abrir no Explorer",
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        self.lbl_treemap_hover.pack(side="left", fill="x", expand=True)

        self.btn_treemap_open = ctk.CTkButton(
            top_bar,
            text="📂 Abrir no Explorer",
            height=28,
            width=130,
            state="disabled",
            command=self._on_open_treemap_selected,
        )
        self.btn_treemap_open.pack(side="right")

        # Container do Canvas
        canvas_frame = ctk.CTkFrame(self.tab_treemap, corner_radius=6)
        canvas_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#181818",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True, padx=2, pady=2)

        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Motion>", self._on_canvas_motion)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Double-Button-1>", self._on_canvas_double_click)

    # -------------------------------------------------------------
    # Execução do Escaneamento (Threading & Background)
    # -------------------------------------------------------------

    def _select_drive(self, drive_path: str):
        self.folder_selector.path_entry.delete(0, "end")
        self.folder_selector.path_entry.insert(0, drive_path)

    def _start_scan(self):
        target_path = self.folder_selector.get_path().strip()
        if not target_path or not os.path.exists(target_path):
            self.show_error("Pasta Inválida", "Selecione uma pasta ou unidade válida existente para analisar.")
            return

        self.btn_scan.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        self.card_size.configure(text="Calculando...")
        self.card_files.configure(text="---")
        self.card_dirs.configure(text="---")
        self.card_time.configure(text="---")
        self.lbl_status.configure(text=f"Iniciando varredura em: {target_path}...")

        def _worker(cancel_event=None, on_progress=None):
            scanner = DiskScanner(max_top_files=100)
            return scanner.scan(
                target_path,
                cancel_event=cancel_event,
                on_progress=lambda f, d, p: on_progress(f, d, p) if on_progress else None,
            )

        def _on_progress_update(files_count, dirs_count, current_p):
            self.dispatch_gui(lambda: self._gui_update_progress(files_count, dirs_count, current_p))

        self.current_task = task_manager.run_task(
            name="disk_analyzer_scan",
            target=_worker,
            on_progress=_on_progress_update,
            on_success=lambda res: self.dispatch_gui(lambda: self._on_scan_success(res)),
            on_error=lambda err: self.dispatch_gui(lambda: self._on_scan_error(err)),
            on_complete=lambda: self.dispatch_gui(self._on_scan_complete),
        )

    def _cancel_scan(self):
        if self.current_task and self.current_task.is_running:
            self.lbl_status.configure(text="Cancelando varredura...")
            self.current_task.cancel()

    def _gui_update_progress(self, files_count: int, dirs_count: int, current_path: str):
        truncated_path = current_path
        if len(truncated_path) > 70:
            truncated_path = "..." + truncated_path[-67:]
        self.lbl_status.configure(
            text=f"Varrendo: {files_count:,} arquivos | {dirs_count:,} pastas | {truncated_path}"
        )

    def _on_scan_success(self, result: ScanResult):
        self.last_scan_result = result
        self.current_browsed_dir = result.root_dir
        self.history_dirs = []

        # Atualizar Métricas
        self.card_size.configure(text=format_size(result.total_size))
        self.card_files.configure(text=f"{result.total_files:,}")
        self.card_dirs.configure(text=f"{result.total_dirs:,}")
        self.card_time.configure(text=f"{result.elapsed_seconds}s")
        self.lbl_status.configure(
            text=f"Concluído com sucesso! {result.total_files:,} arquivos e {result.total_dirs:,} pastas analisados em {result.elapsed_seconds}s."
        )

        # Preencher visualizações
        self._populate_subfolders_view(result.root_dir)
        self._populate_top_files_view(result.top_files)
        self._populate_extensions_view(result.extensions, result.total_size)
        self._prepare_and_draw_treemap(result)

    def _on_scan_error(self, err: Exception):
        self.lbl_status.configure(text=f"Erro na varredura: {err}")
        self.show_error("Erro de Varredura", str(err))

    def _on_scan_complete(self):
        try:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(1.0)
        except Exception:
            pass
        self.btn_scan.configure(state="normal")
        self.btn_cancel.configure(state="disabled")

    # -------------------------------------------------------------
    # Renderização da Aba 1: Subpastas
    # -------------------------------------------------------------

    def _populate_subfolders_view(self, dir_item: Optional[DirItem]):
        for w in self.subdirs_scroll.winfo_children():
            w.destroy()

        if not dir_item:
            ctk.CTkLabel(self.subdirs_scroll, text="Nenhum dado disponível.", text_color="gray").pack(pady=40)
            return

        self.current_browsed_dir = dir_item
        self.btn_dir_back.configure(state="normal" if self.history_dirs else "disabled")
        self.lbl_current_path.configure(text=f"Pasta: {dir_item.path} ({format_size(dir_item.total_size)})")

        subfolders = sorted(dir_item.children, key=lambda d: d.total_size, reverse=True)

        if not subfolders:
            empty_lbl = ctk.CTkLabel(
                self.subdirs_scroll,
                text="Esta pasta não contém outras subpastas (apenas arquivos diretos).",
                text_color="gray",
            )
            empty_lbl.pack(pady=30)
            return

        parent_total = max(1, dir_item.total_size)

        for sub in subfolders:
            pct = (sub.total_size / parent_total) * 100.0
            row = ctk.CTkFrame(self.subdirs_scroll, corner_radius=6)
            row.pack(fill="x", pady=3, padx=2)

            # 1. BOTÕES DE AÇÃO NA DIREITA (FIXADOS PRIMEIRO PARA NUNCA SUMIR)
            btn_box = ctk.CTkFrame(row, fg_color="transparent")
            btn_box.pack(side="right", padx=(4, 10), pady=6)

            open_btn = ctk.CTkButton(
                btn_box,
                text="📂 Explorer",
                width=85,
                height=28,
                fg_color="#3498db",
                hover_color="#2980b9",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p=sub.path: reveal_in_explorer(p),
            )
            open_btn.pack(side="right", padx=2)

            if sub.children:
                enter_btn = ctk.CTkButton(
                    btn_box,
                    text="Entrar ➡",
                    width=70,
                    height=28,
                    fg_color="gray30",
                    hover_color="gray40",
                    font=ctk.CTkFont(size=11),
                    command=lambda target=sub: self._on_enter_subfolder(target),
                )
                enter_btn.pack(side="right", padx=2)

            # 2. BARRA DE PORCENTAGEM NA DIREITA
            bar = ctk.CTkProgressBar(row, width=95, height=10)
            bar.pack(side="right", padx=(6, 10))
            bar.set(min(1.0, max(0.01, pct / 100.0)))

            # 3. TEXTOS NO CENTRO/ESQUERDA (PREENCHEM O RESTANTE)
            left_frame = ctk.CTkFrame(row, fg_color="transparent")
            left_frame.pack(side="left", fill="x", expand=True, padx=(10, 4), pady=6)

            disp_name = format_display_name(sub.name, max_len=48)
            name_lbl = ctk.CTkLabel(
                left_frame,
                text=f"📁 {disp_name}",
                font=ctk.CTkFont(size=13, weight="bold"),
                anchor="w",
            )
            name_lbl.pack(fill="x")

            info_lbl = ctk.CTkLabel(
                left_frame,
                text=f"{format_size(sub.total_size)} • {sub.file_count:,} arquivos • {pct:.1f}% do total",
                font=ctk.CTkFont(size=11),
                text_color="gray",
                anchor="w",
            )
            info_lbl.pack(fill="x")

    def _on_enter_subfolder(self, target: DirItem):
        if self.current_browsed_dir:
            self.history_dirs.append(self.current_browsed_dir)
        self._populate_subfolders_view(target)

    def _on_dir_back(self):
        if self.history_dirs:
            prev = self.history_dirs.pop()
            self._populate_subfolders_view(prev)

    # -------------------------------------------------------------
    # Renderização da Aba 2: Maiores Arquivos
    # -------------------------------------------------------------

    def _populate_top_files_view(self, files: List[FileItem]):
        for w in self.files_scroll.winfo_children():
            w.destroy()

        if not files:
            ctk.CTkLabel(self.files_scroll, text="Nenhum arquivo encontrado.", text_color="gray").pack(pady=40)
            return

        for idx, item in enumerate(files, 1):
            row = ctk.CTkFrame(self.files_scroll, corner_radius=6)
            row.pack(fill="x", pady=3, padx=2)

            # 1. Badge do Ranking na Esquerda
            rank_lbl = ctk.CTkLabel(
                row,
                text=f"#{idx}",
                width=35,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#3498db",
            )
            rank_lbl.pack(side="left", padx=(8, 4))

            # 2. BOTÕES DE AÇÃO NA DIREITA (FIXADOS PRIMEIRO PARA NUNCA SUMIR)
            actions_box = ctk.CTkFrame(row, fg_color="transparent")
            actions_box.pack(side="right", padx=(4, 10), pady=6)

            btn_open = ctk.CTkButton(
                actions_box,
                text="📂 Explorer",
                width=85,
                height=28,
                fg_color="#3498db",
                hover_color="#2980b9",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda p=item.path: reveal_in_explorer(p),
            )
            btn_open.pack(side="right", padx=2)

            btn_copy = ctk.CTkButton(
                actions_box,
                text="📋 Copiar",
                width=65,
                height=28,
                fg_color="gray30",
                hover_color="gray40",
                font=ctk.CTkFont(size=11),
                command=lambda p=item.path: self._copy_path_to_clipboard(p),
            )
            btn_copy.pack(side="right", padx=2)

            # 3. Tamanho Formatado na Direita
            size_lbl = ctk.CTkLabel(
                row,
                text=format_size(item.size),
                width=85,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            )
            size_lbl.pack(side="right", padx=(6, 12))

            # 4. Detalhes do Arquivo no Centro (Preenchem o restante)
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=4, pady=6)

            disp_file_name = format_display_name(item.name, max_len=48)
            file_lbl = ctk.CTkLabel(
                info_frame,
                text=disp_file_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            )
            file_lbl.pack(fill="x")

            disp_dir_path = item.path
            if len(disp_dir_path) > 55:
                disp_dir_path = "..." + disp_dir_path[-52:]
            dir_lbl = ctk.CTkLabel(
                info_frame,
                text=disp_dir_path,
                font=ctk.CTkFont(size=10),
                text_color="gray",
                anchor="w",
            )
            dir_lbl.pack(fill="x")

    def _copy_path_to_clipboard(self, path_str: str):
        try:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(path_str)
            self.show_success("Caminho Copiado", "O caminho do arquivo foi copiado para a área de transferência.")
        except Exception:
            pass

    # -------------------------------------------------------------
    # Renderização da Aba 3: Extensões
    # -------------------------------------------------------------

    def _populate_extensions_view(self, extensions: List[ExtensionStat], total_size: int):
        for w in self.exts_scroll.winfo_children():
            w.destroy()

        if not extensions:
            ctk.CTkLabel(self.exts_scroll, text="Nenhuma extensão catalogada.", text_color="gray").pack(pady=40)
            return

        tot = max(1, total_size)
        for stat in extensions[:50]:
            pct = (stat.total_size / tot) * 100.0

            row = ctk.CTkFrame(self.exts_scroll, corner_radius=6)
            row.pack(fill="x", pady=3, padx=2)

            # Badge colorido da extensão
            badge = ctk.CTkFrame(row, width=70, height=28, fg_color=stat.color, corner_radius=4)
            badge.pack(side="left", padx=8, pady=6)
            badge.pack_propagate(False)

            ext_name = stat.ext if len(stat.ext) <= 8 else stat.ext[:7] + "…"
            ctk.CTkLabel(
                badge,
                text=ext_name,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="white",
            ).pack(expand=True)

            # 1. Tamanho Total Formatado na Direita
            ctk.CTkLabel(
                row,
                text=format_size(stat.total_size),
                width=85,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="e",
            ).pack(side="right", padx=12)

            # 2. Barra visual na Direita
            bar = ctk.CTkProgressBar(row, width=110, height=10, progress_color=stat.color)
            bar.pack(side="right", padx=(6, 12))
            bar.set(min(1.0, max(0.01, pct / 100.0)))

            # 3. Contagem e Informações no Centro
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=8)

            ctk.CTkLabel(
                info_frame,
                text=f"{stat.file_count:,} arquivos",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(fill="x")

            ctk.CTkLabel(
                info_frame,
                text=f"{pct:.1f}% do espaço total analisado",
                font=ctk.CTkFont(size=10),
                text_color="gray",
                anchor="w",
            ).pack(fill="x")

    # -------------------------------------------------------------
    # Renderização da Aba 4: Treemap Visual (Estilo WinDirStat)
    # -------------------------------------------------------------

    def _prepare_and_draw_treemap(self, result: ScanResult):
        # Preparar dados para o treemap baseados nos maiores arquivos e subpastas
        items = []

        # Se houver maiores arquivos, adicioná-los
        for f in result.top_files[:80]:
            items.append({
                "label": f.name,
                "size": f.size,
                "color": self._get_file_color(f.ext),
                "data": f,
            })

        self._treemap_items = items
        self._draw_treemap()

    def _get_file_color(self, ext: str) -> str:
        from core.disk_scanner import get_color_for_ext
        return get_color_for_ext(ext)

    def _on_canvas_resize(self, event):
        self._draw_treemap()

    def _draw_treemap(self):
        if not self._treemap_items:
            self.canvas.delete("all")
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            if w > 10 and h > 10:
                self.canvas.create_text(
                    w / 2,
                    h / 2,
                    text="O mapa de blocos (Treemap) aparecerá aqui após a análise.",
                    fill="gray",
                    font=("Segoe UI", 12),
                )
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        self.canvas.delete("all")
        self._treemap_rects = compute_squarified_treemap(
            self._treemap_items,
            width=float(w),
            height=float(h),
            padding=1.5,
        )

        for rect in self._treemap_rects:
            # Desenhar retângulo preenchido
            tag = f"rect_{id(rect)}"
            self.canvas.create_rectangle(
                rect.x0,
                rect.y0,
                rect.x1,
                rect.y1,
                fill=rect.color,
                outline="#1e1e1e",
                width=1,
                tags=(tag, "treemap_block"),
            )

            # Desenhar texto se o bloco tiver espaço suficiente
            rw = rect.x1 - rect.x0
            rh = rect.y1 - rect.y0
            if rw > 45 and rh > 22:
                display_text = rect.label
                max_chars = max(4, int(rw / 7.5))
                if len(display_text) > max_chars:
                    display_text = display_text[: max_chars - 2] + "…"
                size_str = format_size(rect.size)

                # Texto do Nome
                self.canvas.create_text(
                    rect.x0 + 4,
                    rect.y0 + 10,
                    text=display_text,
                    fill="white",
                    anchor="w",
                    font=("Segoe UI", 9, "bold"),
                    tags=(tag, "treemap_block"),
                )

                # Texto do Tamanho se houver espaço vertical
                if rh > 38:
                    self.canvas.create_text(
                        rect.x0 + 4,
                        rect.y0 + 24,
                        text=size_str,
                        fill="#ecf0f1",
                        anchor="w",
                        font=("Segoe UI", 8),
                        tags=(tag, "treemap_block"),
                    )

    def _on_canvas_motion(self, event):
        x, y = event.x, event.y
        found = None
        for rect in self._treemap_rects:
            if rect.x0 <= x <= rect.x1 and rect.y0 <= y <= rect.y1:
                found = rect
                break

        if found:
            self._selected_item = found.data
            self.btn_treemap_open.configure(state="normal")
            if isinstance(found.data, FileItem):
                self.lbl_treemap_hover.configure(
                    text=f"📄 {found.data.name} • {format_size(found.data.size)} • {found.data.path}"
                )
            else:
                self.lbl_treemap_hover.configure(
                    text=f"{found.label} • {format_size(found.size)}"
                )
        else:
            self.lbl_treemap_hover.configure(
                text="Passe o mouse sobre os blocos para inspecionar | Dê duplo clique para abrir no Explorer"
            )

    def _on_canvas_click(self, event):
        x, y = event.x, event.y
        for rect in self._treemap_rects:
            if rect.x0 <= x <= rect.x1 and rect.y0 <= y <= rect.y1:
                self._selected_item = rect.data
                self.btn_treemap_open.configure(state="normal")
                return

    def _on_canvas_double_click(self, event):
        self._on_canvas_click(event)
        self._on_open_treemap_selected()

    def _on_open_treemap_selected(self):
        if self._selected_item and isinstance(self._selected_item, FileItem):
            reveal_in_explorer(self._selected_item.path)
        elif self._selected_item and isinstance(self._selected_item, DirItem):
            reveal_in_explorer(self._selected_item.path)
