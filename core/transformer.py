import os
import sys
import threading
from pathlib import Path
from typing import Optional, Callable
from core.ffmpeg_manager import ffmpeg_manager


class MediaTransformer:
    """Implementa as operações de transformação, compressão, corte e conversão de mídias."""

    @staticmethod
    def _parse_time_to_seconds(time_str: str) -> float:
        """Converte strings no formato HH:MM:SS ou MM:SS ou segundos para float."""
        time_str = time_str.strip()
        parts = time_str.split(":")
        try:
            if len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            else:
                return float(time_str)
        except ValueError:
            return 0.0

    def compress_video(
        self,
        input_path: str,
        output_path: str,
        mode: str = "target_size",
        target_size_mb: float = 25.0,
        crf: int = 24,
        codec: str = "libx264",
        preset: str = "medium",
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """Comprime o vídeo por tamanho alvo (MB) ou por fator de qualidade constante (CRF)."""
        info = ffmpeg_manager.get_media_info(input_path)
        duration = info.get("duration", 0.0)

        if duration <= 0.0:
            duration = 100.0  # Fallback se duração não for detectada

        args = ["-i", input_path]

        if mode == "target_size" and target_size_mb > 0:
            # Cálculo de bitrate com margem de segurança de 8% para cabeçalhos e áudio
            audio_bitrate_kbps = 96
            total_target_bits = target_size_mb * 8 * 1024 * 1024 * 0.92
            video_bitrate_kbps = max(64, int((total_target_bits / duration) / 1024) - audio_bitrate_kbps)

            args.extend([
                "-c:v", codec,
                "-b:v", f"{video_bitrate_kbps}k",
                "-maxrate", f"{int(video_bitrate_kbps * 1.5)}k",
                "-bufsize", f"{video_bitrate_kbps * 2}k",
                "-preset", preset,
                "-c:a", "aac",
                "-b:a", f"{audio_bitrate_kbps}k",
                output_path,
            ])
        else:
            # Modo CRF
            args.extend([
                "-c:v", codec,
                "-crf", str(crf),
                "-preset", preset,
                "-c:a", "aac",
                "-b:a", "128k",
                output_path,
            ])

        ffmpeg_manager.run_ffmpeg(args, total_duration=duration, on_progress=on_progress, cancel_event=cancel_event)
        return output_path

    def trim_video(
        self,
        input_path: str,
        output_path: str,
        start_time: str,
        end_time: str,
        lossless: bool = True,
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """Corta um trecho de vídeo. Modo lossless é instantâneo (-c copy)."""
        t_start = self._parse_time_to_seconds(start_time)
        t_end = self._parse_time_to_seconds(end_time)
        trim_duration = max(0.1, t_end - t_start) if t_end > t_start else 1.0

        if lossless:
            # Modo ultra-rápido sem recodificação
            args = [
                "-ss", start_time,
                "-to", end_time,
                "-i", input_path,
                "-c", "copy",
                "-map", "0",
                output_path,
            ]
        else:
            # Modo preciso com recodificação
            args = [
                "-ss", start_time,
                "-to", end_time,
                "-i", input_path,
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "fast",
                "-c:a", "aac",
                output_path,
            ]

        ffmpeg_manager.run_ffmpeg(args, total_duration=trim_duration, on_progress=on_progress, cancel_event=cancel_event)
        return output_path

    def convert_to_gif(
        self,
        input_path: str,
        output_path: str,
        start_time: Optional[str] = None,
        duration_sec: Optional[float] = None,
        fps: int = 15,
        width: int = 480,
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """Gera GIF de alta qualidade usando paleta de cores otimizada em 2 etapas (palettegen + paletteuse)."""
        info = ffmpeg_manager.get_media_info(input_path)
        total_dur = duration_sec or (info.get("duration", 10.0))

        args = []
        if start_time:
            args.extend(["-ss", start_time])
        if duration_sec:
            args.extend(["-t", str(duration_sec)])

        args.extend(["-i", input_path])

        filter_graph = f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse=dither=bayer"
        args.extend([
            "-filter_complex", filter_graph,
            output_path,
        ])

        ffmpeg_manager.run_ffmpeg(args, total_duration=total_dur, on_progress=on_progress, cancel_event=cancel_event)
        return output_path

    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        format_type: str = "mp3",
        bitrate: str = "192k",
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """Extrai a faixa de áudio do arquivo de vídeo para MP3, WAV, etc."""
        info = ffmpeg_manager.get_media_info(input_path)
        total_dur = info.get("duration", 0.0)

        args = ["-i", input_path, "-vn"]
        if format_type.lower() == "mp3":
            args.extend(["-c:a", "libmp3lame", "-b:a", bitrate])
        elif format_type.lower() == "wav":
            args.extend(["-c:a", "pcm_s16le"])
        elif format_type.lower() == "m4a":
            args.extend(["-c:a", "aac", "-b:a", bitrate])

        args.append(output_path)
        ffmpeg_manager.run_ffmpeg(args, total_duration=total_dur, on_progress=on_progress, cancel_event=cancel_event)
        return output_path

    def convert_container(
        self,
        input_path: str,
        output_path: str,
        on_progress: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> str:
        """Converte o container de vídeo (ex: MKV -> MP4, WebM -> MP4)."""
        info = ffmpeg_manager.get_media_info(input_path)
        total_dur = info.get("duration", 0.0)

        args = [
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ]
        ffmpeg_manager.run_ffmpeg(args, total_duration=total_dur, on_progress=on_progress, cancel_event=cancel_event)
        return output_path


media_transformer = MediaTransformer()
