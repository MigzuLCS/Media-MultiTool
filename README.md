# 🎬 Media MultiTool

> Aplicativo desktop moderno, modular e extensível para manipulação de mídias (download de vídeos/áudios do YouTube, compressão para Discord/WhatsApp, corte ultra-rápido sem perda e conversão de formatos).

Desenvolvido em **Python** com **CustomTkinter**, integrado nativamente ao **yt-dlp** e ao **FFmpeg**.

---

## 🚀 Funcionalidades Principais

| Módulo | Descrição | Destaques Técnicos |
| :--- | :--- | :--- |
| **📥 YouTube Downloader** | Baixe vídeos ou extraia apenas o áudio diretamente do YouTube e plataformas compatíveis. | Qualidades (Melhor, 1080p, 720p, 480p), extração em MP3 a 192kbps, estimativa de tempo e velocidade em tempo real. |
| **📉 Compressor de Vídeo** | Reduza o tamanho de vídeos pesados para caber nos limites de upload. | Presets prontos para **Discord (25 MB)**, **WhatsApp (16 MB)**, **Email (10 MB)**, **Nitro (50 MB)** ou tamanho customizado. Codecs H.264 ou H.265. |
| **✂️ Corte Rápido** | Isole trechos específicos definindo tempo inicial e final. | **Modo Lossless Instantâneo (`-c copy`)**: processa em menos de 1 segundo e mantém 100% da qualidade original sem reencodar. |
| **🔄 Conversor de Formatos** | Transforme vídeos em GIFs de alta fidelidade ou extraia faixas sonoras. | **MP4 $\to$ GIF** com filtro de paleta em 2 passos (`palettegen`/`paletteuse`) sem bordas granuladas; **Vídeo $\to$ MP3** (128 a 320 kbps); **Vídeo $\to$ WAV**; remuxing de containers. |
| **⚙️ Configurações & FFmpeg** | Painel de controle do motor de mídia e preferências visuais. | **Instalação automática do FFmpeg em 1 clique**, seletor de tema (Dark / Light) e escolha da pasta padrão de downloads. |

---

## 🛠️ Como Iniciar o Aplicativo

### Opção 1: Inicialização com 1 Clique (Windows)
Basta dar um duplo-clique no arquivo:
```cmd
start.bat
```

### Opção 2: Pelo Terminal
Certifique-se de usar o ambiente virtual do projeto:
```powershell
# Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1

# Iniciar o aplicativo
python run.py
```

---

## 🧩 Como Adicionar Novas Funcionalidades (Extensibilidade)

O Media MultiTool foi projetado desde o primeiro dia para permitir a adição de novas ferramentas sem precisar modificar as telas existentes:

### Passo 1: Crie sua ferramenta em `features/`
Crie um novo arquivo, por exemplo `features/audio_denoise_tab.py`:

```python
import customtkinter as ctk
from features.base import BaseFeature
from ui.components.file_selector import FileSelector

class AudioDenoiseTab(BaseFeature):
    id = "audio_denoise"            # Identificador único
    title = "Remover Ruído"          # Nome exibido na barra lateral
    icon = "🎙️"                     # Ícone / emoji
    description = "Remove chiados de gravações de áudio."

    def render(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        self.frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            self.frame,
            text="🎙️ Redutor de Ruído de Áudio",
            font=ctk.CTkFont(size=20, weight="bold")
        ).pack(anchor="w", pady=(0, 10))

        # Seus campos, botões e seletores aqui...
        return self.frame
```

### Passo 2: Registre sua ferramenta em `features/__init__.py`
Abra `features/__init__.py` e adicione sua classe à lista `AVAILABLE_FEATURES`:

```python
from features.audio_denoise_tab import AudioDenoiseTab

AVAILABLE_FEATURES = [
    YouTubeTab,
    CompressTab,
    TrimTab,
    ConvertTab,
    AudioDenoiseTab,  # <-- Sua nova ferramenta!
    SettingsTab,
]
```

**Pronto!** O aplicativo cuidará automaticamente de:
* Criar o botão de navegação na barra lateral.
* Gerenciar a alternância de telas.
* Preservar o estado da tela em segundo plano.

---

## 📁 Estrutura do Projeto

```text
mediamultitool/
├── bin/                        # Binários locais opcionais (ffmpeg.exe, ffprobe.exe)
├── core/                       # Motores de processamento e utilitários
│   ├── config.py               # Gerenciador de configurações persistentes (config.json)
│   ├── ffmpeg_manager.py       # Wrapper FFmpeg/ffprobe com progresso e cancelamento
│   ├── downloader.py           # Integração com yt-dlp e hooks de download
│   ├── transformer.py          # Lógicas de compressão, corte e conversão
│   ├── installer.py            # Download automático do FFmpeg oficial
│   └── tasks.py                # Gerenciador de threads assíncronas (UI nunca congela)
├── features/                   # Módulos e abas independentes (Plugins)
│   ├── base.py                 # Contrato BaseFeature
│   ├── youtube_tab.py          # Aba YouTube Downloader
│   ├── compress_tab.py         # Aba Compressor de Vídeos
│   ├── trim_tab.py             # Aba Corte Rápido
│   ├── convert_tab.py          # Aba Conversor de Mídia (GIF / MP3)
│   └── settings_tab.py         # Aba Configurações e Instalação de FFmpeg
├── ui/                         # Interface de usuário (CustomTkinter)
│   ├── components/             # Widgets reutilizáveis (FileSelector, ProgressCard)
│   └── main_window.py          # Janela principal com barra lateral dinâmica
├── tests/                      # Bateria de testes unitários automatizados
├── requirements.txt            # Dependências congeladas
├── run.py                      # Ponto de entrada do sistema
├── start.bat                   # Inicializador rápido para Windows
└── README.md                   # Documentação do projeto
```

---

## ⚡ Tratamento do Motor FFmpeg

O FFmpeg é necessário para as funções de corte, compressão e conversão:
1. O aplicativo busca primeiro em `bin/ffmpeg.exe` dentro do projeto.
2. Em seguida, busca no `PATH` do sistema Windows.
3. Se não encontrar, a barra lateral exibirá um alerta amigável `⚠️ FFmpeg Ausente`.
4. Basta acessar a aba **Configurações** e clicar em **"Baixar FFmpeg Automaticamente (Oficial)"** para que o app baixe e extraia os executáveis oficiais em poucos segundos sem você precisar configurar variáveis de ambiente!
