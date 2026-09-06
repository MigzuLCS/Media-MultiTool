import os
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog

from features.base import BaseFeature
from ui.components.progress_card import ProgressCard
from core.ffmpeg_manager import ffmpeg_manager
from core.installer import ffmpeg_installer
from core.tasks import task_manager
from core.config import config


class SettingsTab(BaseFeature):
    id = "settings"
    title = "Configurações"
    icon = "⚙️"
    description = "Gerencie o motor FFmpeg, temas e pastas padrão."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Cabeçalho
        title_lbl = ctk.CTkLabel(
            self.frame,
            text="⚙️ Configurações do Aplicativo",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        )
        title_lbl.pack(fill="x", pady=(0, 4))

        desc_lbl = ctk.CTkLabel(
            self.frame,
            text="Verifique o status do motor de mídia (FFmpeg) e ajuste suas preferências globais.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            anchor="w",
        )
        desc_lbl.pack(fill="x", pady=(0, 16))

        # Seção FFmpeg
        ff_card = ctk.CTkFrame(self.frame)
        ff_card.pack(fill="x", pady=(0, 16), padx=2)

        ctk.CTkLabel(
            ff_card,
            text="Motor FFmpeg e ffprobe:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 4))

        self.status_lbl = ctk.CTkLabel(
            ff_card,
            text="Verificando...",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self.status_lbl.pack(fill="x", padx=14, pady=(0, 8))

        btn_row = ctk.CTkFrame(ff_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 12))

        self.download_btn = ctk.CTkButton(
            btn_row,
            text="📥 Baixar FFmpeg Automaticamente (Oficial)",
            command=self._start_ffmpeg_download,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1f6aa5",
        )
        self.download_btn.pack(side="left", padx=(0, 8))

        self.select_btn = ctk.CTkButton(
            btn_row,
            text="Localizar Manualmente...",
            command=self._select_ffmpeg_manually,
            font=ctk.CTkFont(size=12),
            fg_color="#3a3a3a",
        )
        self.select_btn.pack(side="left")

        # Progresso de download do FFmpeg
        self.progress_card = ProgressCard(
            self.frame,
            title="Download do FFmpeg",
            on_cancel=self._cancel_installer,
        )
        self.progress_card.pack(fill="x", pady=(0, 16))

        # Seção Preferências Gerais
        pref_card = ctk.CTkFrame(self.frame)
        pref_card.pack(fill="x", pady=(0, 16), padx=2)

        ctk.CTkLabel(
            pref_card,
            text="Aparência e Pastas:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 6))

        # Tema
        theme_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(theme_row, text="Tema da Interface:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 10))

        current_theme = config.get("theme", "dark").capitalize()
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row,
            values=["Dark", "Light", "System"],
            command=self._on_theme_change,
        )
        self.theme_menu.set(current_theme)
        self.theme_menu.pack(side="left")

        # Pasta padrão
        out_row = ctk.CTkFrame(pref_card, fg_color="transparent")
        out_row.pack(fill="x", padx=14, pady=(0, 12))

        ctk.CTkLabel(out_row, text="Pasta Padrão de Saída:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(0, 4))

        input_frame = ctk.CTkFrame(out_row, fg_color="transparent")
        input_frame.pack(fill="x")

        self.dir_entry = ctk.CTkEntry(input_frame)
        self.dir_entry.insert(0, config.get("output_dir", str(Path.home() / "Downloads")))
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            input_frame,
            text="Alterar...",
            width=80,
            command=self._change_default_dir,
        ).pack(side="right")

        # Seção Aviso Legal / Isenção de Responsabilidade
        legal_card = ctk.CTkFrame(self.frame)
        legal_card.pack(fill="x", pady=(0, 16), padx=2)

        ctk.CTkLabel(
            legal_card,
            text="⚖️ Isenção de Responsabilidade e Termos de Uso:",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=14, pady=(12, 6))

        disclaimer_lines = [
            "• Finalidade Educacional e Pessoal: O Media MultiTool é um software livre utilitário para manipulação, conversão e arquivamento pessoal de mídias.",
            "• Sem Hospedagem: O aplicativo não armazena, hospeda, distribui nem retransmite mídias em servidores próprios. Todo processamento ocorre localmente na máquina do usuário.",
            "• Ausência de Vínculo: O projeto não possui qualquer filiação, parceria, patrocínio ou endosso de plataformas de streaming ou redes sociais de terceiros.",
            "• Responsabilidade do Usuário: O usuário é o único responsável por garantir que as mídias processadas sejam de domínio público, de sua autoria ou expressamente autorizadas, observando a legislação de direitos autorais (como a Lei 9.610/98) e os termos de serviço aplicáveis.",
        ]
        for line in disclaimer_lines:
            ctk.CTkLabel(
                legal_card,
                text=line,
                font=ctk.CTkFont(size=11),
                text_color="gray",
                wraplength=650,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=14, pady=(0, 4))

        # Espaçamento inferior no card
        ctk.CTkFrame(legal_card, height=6, fg_color="transparent").pack()

        self._refresh_ffmpeg_status()
        return self.frame

    def _refresh_ffmpeg_status(self):
        ff_path = ffmpeg_manager.get_ffmpeg_path()
        if ff_path:
            self.status_lbl.configure(
                text=f"🟢 FFmpeg Encontrado: {ff_path}",
                text_color="#2ecc71",
            )
            self.download_btn.configure(text="Reinstalar FFmpeg (Oficial)")
        else:
            self.status_lbl.configure(
                text="🔴 FFmpeg NÃO Encontrado! Clique no botão abaixo para baixar.",
                text_color="#e74c3c",
            )
            self.download_btn.configure(text="📥 Baixar FFmpeg Automaticamente (Oficial)")

    def _start_ffmpeg_download(self):
        self.download_btn.configure(state="disabled")
        self.progress_card.reset("Iniciando download do pacote estático...")

        def on_prog(frac, msg):
            self.dispatch_gui(lambda: self.progress_card.update_progress(frac, msg))

        def on_succ(res):
            self.dispatch_gui(lambda: self._on_download_success())

        def on_err(exc):
            self.dispatch_gui(lambda: self._on_download_error(exc))

        task_manager.run_task(
            name="ffmpeg_install",
            target=ffmpeg_installer.download_and_extract,
            on_progress=on_prog,
            on_success=on_succ,
            on_error=on_err,
        )

    def _on_download_success(self):
        self.download_btn.configure(state="normal")
        self._refresh_ffmpeg_status()
        self.show_success("FFmpeg Instalado!", "Os binários foram salvos em 'bin/' e estão prontos para uso.")

    def _on_download_error(self, exc: Exception):
        self.download_btn.configure(state="normal")
        self.progress_card.update_progress(0.0, "Falha no download.")
        self.show_error("Erro de Instalação", str(exc))

    def _cancel_installer(self):
        task_manager.cancel_task("ffmpeg_install")
        self.download_btn.configure(state="normal")

    def _select_ffmpeg_manually(self):
        chosen = filedialog.askopenfilename(
            title="Selecione o executável do ffmpeg",
            filetypes=[("Executável FFmpeg", "ffmpeg.exe;ffmpeg"), ("Todos os Arquivos", "*.*")],
        )
        if chosen and Path(chosen).exists():
            config.set("ffmpeg_path", chosen)
            self._refresh_ffmpeg_status()
            self.show_success("FFmpeg Configurado", f"Caminho definido para:\n{chosen}")

    def _on_theme_change(self, value: str):
        theme_str = value.lower()
        config.set("theme", theme_str)
        ctk.set_appearance_mode(theme_str)

    def _change_default_dir(self):
        chosen = filedialog.askdirectory(title="Selecione a Pasta Padrão")
        if chosen:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, chosen)
            config.set("output_dir", chosen)
            self.show_info("Pasta Atualizada", f"Nova pasta padrão:\n{chosen}")
