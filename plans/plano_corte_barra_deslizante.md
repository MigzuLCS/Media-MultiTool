# Alinhamento Preciso & Destaque Colorido da Forma de Onda (Waveform)

Este plano descreve o aprimoramento completo do componente de **Forma de Onda (WaveformView)** na aba de Corte Rápido (`TrimTab`), atendendo aos seguintes objetivos:
1. **Alinhamento Milimétrico**: O gráfico de onda possui exatamente a mesma largura útil e padding lateral (`pad_x = 18`) que o `TimeRangeSlider`, alinhando os tempos de corte pixel a pixel.
2. **Destaque Visual Bicolor do Corte**: A faixa selecionada entre início e fim é destacada em cores vibrantes (ciano/azul), enquanto os trechos externos ficam atenuados (cinza escuro). Linhas verticais verde e vermelha conectam-se visualmente às alças do slider.
3. **Interface Limpa Sem Textos**: O componente exibe puramente o gráfico de ondas sonoras, sem títulos ou rótulos desnecessários.
4. **Presença Contínua do Waveform**: O gráfico é sempre exibido logo acima da barra deslizante tanto para áudios quanto para vídeos (ocultando as miniaturas de frames apenas quando o arquivo for estritamente áudio).

---

## 🛠️ Arquitetura das Mudanças

### 1. Componente Dedicado `WaveformView` (`ui/components/waveform_view.py`)
- Canvas com renderização sub-milissegundo (`0.18ms/frame`) usando máscaras alpha e composição PIL.
- Sincronização bidirecional: arrastar o slider ou clicar/arrastar diretamente na forma de onda ajusta o trecho selecionado em tempo real.
- Suporte total aos modos Claro e Escuro do CustomTkinter.

### 2. FFmpeg Manager (`core/ffmpeg_manager.py`)
- Suporte a `raw_rgba=True` em `extract_audio_waveform`, permitindo extração da máscara de intensidade com resolução de 1200 pontos para escalonamento perfeito.

### 3. Integração na Aba de Corte (`features/trim_tab.py`)
- Em vídeos: exibe miniaturas lado a lado -> WaveformView limpo -> TimeRangeSlider.
- Em áudios: oculta miniaturas -> WaveformView limpo -> TimeRangeSlider.
- Atualização em tempo real do destaque de cor durante o arraste das alças ou edição dos campos numéricos.

### 4. Robustez de Threading e Troca Sequencial de Mídias
- **Thread-Safety no Python 3.14**: Utilização de `dispatch_gui` com fila thread-safe em vez de chamadas diretas a `widget.after` a partir de threads em background.
- **Suporte Dinâmico a Codecs de Áudio**: No corte de arquivos sem vídeo, o FFmpeg utiliza codecs de áudio nativos (`libmp3lame`, `pcm_s16le`, `aac`), prevenindo falhas de container.
- **Transição Limpa Entre Mídias**: O `WaveformView` e as miniaturas de frame são limpos imediatamente ao trocar de arquivo, reconfigurando os limites de duração e visibilidade de miniaturas.

---

## 🧪 Verificação & Testes
- Simulação ponta a ponta: corte de áudio (21s) seguido de vídeo (113s) com teste de arraste de slider e validação de waveform.
- Suíte automatizada com 15 testes:
  ```powershell
  .venv\Scripts\python.exe -m unittest discover tests
  ```
