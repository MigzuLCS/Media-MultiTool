# 🎬 Media MultiTool

> Aplicativo desktop moderno, modular e extensível para manipulação de mídias locais e online (compressão de vídeos para Discord/WhatsApp, corte ultra-rápido sem perda, conversão de formatos e download de mídias públicas ou autorizadas).

Desenvolvido em **Python** com **CustomTkinter**, integrado nativamente ao **FFmpeg** e a utilitários de mídia de código aberto como o **yt-dlp**.

---

## 🚀 Funcionalidades Principais

| Módulo | Descrição | Destaques Técnicos |
| :--- | :--- | :--- |
| **📉 Compressor de Vídeo** | Reduza o tamanho de vídeos pesados para caber nos limites de upload. | Presets prontos para **Discord (25 MB)**, **WhatsApp (16 MB)**, **Email (10 MB)**, **Nitro (50 MB)** ou tamanho customizado. Codecs H.264 ou H.265. |
| **✂️ Corte Rápido** | Isole trechos específicos definindo tempo inicial e final. | **Modo Lossless Instantâneo (`-c copy`)**: processa em menos de 1 segundo e mantém 100% da qualidade original sem reencodar. |
| **🔄 Conversor de Formatos** | Transforme vídeos em GIFs de alta fidelidade ou extraia faixas sonoras. | **MP4 $\to$ GIF** com filtro de paleta em 2 passos (`palettegen`/`paletteuse`) sem bordas granuladas; **Vídeo $\to$ MP3** (128 a 320 kbps); **Vídeo $\to$ WAV**; remuxing de containers. |
| **📥 Download de Mídia** | Obtenha cópias locais de vídeos ou extraia áudios de conteúdos online públicos, autorizados ou sob licenças abertas. | Suporte amplo a protocolos web via yt-dlp, auto-tagging de metadados abertos via MusicBrainz + FFmpeg, seleção de resolução e exportação direta para áudio. |
| **⚙️ Configurações & FFmpeg** | Painel de controle do motor de mídia e preferências visuais. | **Instalação automática do FFmpeg em 1 clique**, seletor de tema (Dark / Light) e escolha da pasta padrão de downloads. |

---

## 🛠️ Como Iniciar o Aplicativo

### Opção 1: Pesquisa do Windows ou Área de Trabalho (Mais Rápido)
- Pressione a tecla **Windows** no teclado e digite `Media MultiTool`.
- Ou abra o atalho **Media MultiTool** na sua Área de Trabalho (`Desktop`).

> Se os atalhos ainda não estiverem criados, basta executar `criar_atalho.bat` uma vez.

### Opção 2: Pelo Executável Direto
Dê um duplo clique diretamente no inicializador na raiz da pasta:
```cmd
Media MultiTool.exe
```
*(Inicia o aplicativo instantaneamente e em segundo plano, sem janela preta de terminal).*

### Opção 3: Script de Inicialização
```cmd
start.bat
```

### Opção 4: Pelo Terminal
Certifique-se de usar o ambiente virtual do projeto:
```powershell
# Ativar o ambiente virtual
.\.venv\Scripts\Activate.ps1

# Iniciar o aplicativo
python run.py
```

---

## 📦 Como Distribuir para Outras Pessoas (Sem Python)

Para compartilhar o aplicativo com outras pessoas que **não têm Python instalado**:

### 1. Download Pronto (Releases do GitHub)
Nas [Releases do GitHub](https://github.com/MigzuLCS/Media-MultiTool/releases), os usuários podem baixar diretamente:
- **`Media-MultiTool-Setup.exe`**: Instalador clássico do Windows (instala sem precisar de permissões de administrador, cria atalhos no Menu Iniciar e Desktop, e adiciona desinstalador).
- **`Media-MultiTool-Windows-x64.zip`**: Versão portátil (basta descompactar em qualquer pasta e abrir o `Media MultiTool.exe`).

### 2. Gerar Versão Portátil Localmente
Basta dar dois cliques no arquivo:
```cmd
build.bat
```
Ou executar pelo terminal:
```powershell
python build_portable.py
```
Isso gera a pasta `dist/Media MultiTool` e o arquivo `dist/Media-MultiTool-Windows-x64.zip` prontos para envio.

### 3. Publicar Nova Versão na Nuvem Automaticamente (GitHub Actions)
O repositório já possui uma automação de CI/CD pronta (`.github/workflows/release.yml`). Para lançar uma nova versão para os usuários:
```bash
git tag v1.0.0
git push origin v1.0.0
```
O GitHub compilará o executável e o instalador na nuvem e atualizará a página de download automaticamente!

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
│   ├── youtube_tab.py          # Aba Download de Mídia Online
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

---

## ⚖️ Aviso Legal e Isenção de Responsabilidade (Disclaimer)

1. **Finalidade Educacional e Uso Pessoal**: O **Media MultiTool** é desenvolvido e disponibilizado como software livre de código aberto exclusivamente para fins educacionais, de pesquisa em manipulação de codecs/mídias e para auxílio na realização de cópias de segurança de conteúdos próprios ou de domínio público.
2. **Propriedade Intelectual e Direitos Autorais**: Este projeto respeita integralmente as legislações de direitos autorais (incluindo a Lei Federal Brasileira nº 9.610/98 e leis internacionais). O software não tem por finalidade burlar mecanismos de proteção digital (DRM) ou incentivar a pirataria.
3. **Ausência de Servidores Centrais / Armazenamento**: O software não armazena, hospeda, indexa nem retransmite fluxos ou arquivos de mídia. Todas as operações de download, corte, compressão e conversão são executadas estritamente de forma descentralizada e local no computador do próprio usuário.
4. **Isenção de Vínculo e Marcas**: O Media MultiTool não possui qualquer tipo de filiação, endosso, patrocínio ou conexão formal com Google LLC, YouTube, Spotify AB, Meta Platforms Inc. ou quaisquer outras empresas cujos protocolos públicos sejam compatíveis com utilitários de terceiros (como o `yt-dlp`). Todas as marcas citadas pertencem aos seus respectivos proprietários.
5. **Responsabilidade do Usuário**: É responsabilidade exclusiva do usuário final assegurar que a utilização desta ferramenta esteja em estrita conformidade com as leis do seu país e com os Termos de Serviço de cada plataforma acessada.
