import os
import sys
import time
import heapq
import string
import subprocess
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable, Any


def format_size(size_bytes: int) -> str:
    """Converte tamanho em bytes para formato legível (B, KB, MB, GB, TB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    unit_idx = 0
    while size >= 1024.0 and unit_idx < len(units) - 1:
        size /= 1024.0
        unit_idx += 1
    return f"{size:.2f} {units[unit_idx]}" if unit_idx > 0 else f"{int(size)} B"


def get_windows_drives() -> List[str]:
    """Retorna lista de unidades de disco disponíveis no Windows (ex: ['C:\\', 'D:\\'])."""
    drives = []
    if sys.platform == "win32":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive_str = f"{letter}:\\"
                    if os.path.exists(drive_str):
                        drives.append(drive_str)
                bitmask >>= 1
        except Exception:
            for letter in string.ascii_uppercase:
                drive_str = f"{letter}:\\"
                if os.path.exists(drive_str):
                    drives.append(drive_str)
    else:
        drives.append("/")
    return drives


def reveal_in_explorer(target_path: str):
    """Abre o Windows Explorer com o arquivo ou pasta selecionado."""
    norm_path = os.path.normpath(target_path)
    if not os.path.exists(norm_path):
        return
    if sys.platform == "win32":
        try:
            if os.path.isfile(norm_path):
                subprocess.Popen(["explorer", f"/select,{norm_path}"])
            else:
                os.startfile(norm_path)
        except Exception as e:
            print(f"[Explorer Error] {e}")
    else:
        try:
            subprocess.Popen(["xdg-open", norm_path if os.path.isdir(norm_path) else os.path.dirname(norm_path)])
        except Exception:
            pass


def send_to_recycle_bin(target_path: str) -> bool:
    """Envia o arquivo ou pasta com segurança para a Lixeira do Windows (com confirmação de rollback)."""
    norm_path = os.path.normpath(target_path)
    if not os.path.exists(norm_path):
        return False

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class SHFILEOPSTRUCTW(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("wFunc", wintypes.UINT),
                    ("pFrom", wintypes.LPCWSTR),
                    ("pTo", wintypes.LPCWSTR),
                    ("fFlags", wintypes.WORD),
                    ("fAnyOperationsAborted", wintypes.BOOL),
                    ("hNameMappings", wintypes.LPVOID),
                    ("lpszProgressTitle", wintypes.LPCWSTR),
                ]

            FO_DELETE = 0x0003
            FOF_ALLOWUNDO = 0x0040
            FOF_NOCONFIRMATION = 0x0010
            FOF_SILENT = 0x0004

            fileop = SHFILEOPSTRUCTW()
            fileop.hwnd = 0
            fileop.wFunc = FO_DELETE
            # Caminho precisa terminar com duplo caractere nulo
            fileop.pFrom = norm_path + "\0\0"
            fileop.pTo = None
            fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
            fileop.fAnyOperationsAborted = False
            fileop.hNameMappings = None
            fileop.lpszProgressTitle = None

            res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
            return res == 0 and not fileop.fAnyOperationsAborted
        except Exception as e:
            print(f"[Recycle Bin Error] {e}")
            return False
    else:
        try:
            import send2trash
            send2trash.send2trash(norm_path)
            return True
        except Exception:
            return False


@dataclass
class FileItem:
    path: str
    name: str
    size: int
    ext: str
    dir_path: str


@dataclass
class DirItem:
    path: str
    name: str
    total_size: int = 0
    direct_size: int = 0
    file_count: int = 0
    subdirs_count: int = 0
    children: List["DirItem"] = field(default_factory=list)


@dataclass
class ExtensionStat:
    ext: str
    total_size: int = 0
    file_count: int = 0
    color: str = "#7f8c8d"


@dataclass
class ScanResult:
    root_path: str
    total_size: int = 0
    total_files: int = 0
    total_dirs: int = 0
    elapsed_seconds: float = 0.0
    root_dir: Optional[DirItem] = None
    subfolders: List[DirItem] = field(default_factory=list)
    top_files: List[FileItem] = field(default_factory=list)
    extensions: List[ExtensionStat] = field(default_factory=list)


# Paleta de cores para extensões conhecidas
EXTENSION_COLORS = {
    # Vídeo (Tons Azuis / Cianos)
    ".mp4": "#3498db", ".mkv": "#2980b9", ".avi": "#1abc9c", ".mov": "#16a085",
    ".webm": "#00cec9", ".wmv": "#0984e3", ".flv": "#74b9ff",
    # Áudio (Tons Roxos)
    ".mp3": "#9b59b6", ".wav": "#8e44ad", ".flac": "#6c5ce7", ".aac": "#a29bfe",
    ".ogg": "#be2edd", ".m4a": "#4834d4",
    # Imagem (Tons Verdes)
    ".png": "#2ecc71", ".jpg": "#27ae60", ".jpeg": "#00b894", ".gif": "#55efc4",
    ".webp": "#10ac84", ".svg": "#1dd1a1", ".ico": "#05c46b",
    # Compactados (Tons Laranja / Âmbar)
    ".zip": "#e67e22", ".rar": "#d35400", ".7z": "#f39c12", ".tar": "#e17055",
    ".gz": "#d63031", ".iso": "#ff7675",
    # Executáveis / Binários (Tons Vermelhos / Corais)
    ".exe": "#e74c3c", ".msi": "#c0392b", ".dll": "#eb4d4b", ".sys": "#ff4757",
    # Documentos / Texto (Tons Amarelos / Dourados)
    ".pdf": "#f1c40f", ".docx": "#fdcb6e", ".xlsx": "#f39c12", ".txt": "#ffeaa7",
    # Programação / Dados (Tons Teal / Ardósia)
    ".py": "#3867d6", ".js": "#f7b731", ".json": "#fa8231", ".sqlite": "#20bf6b",
    ".db": "#0fb9b1",
}


def get_color_for_ext(ext: str) -> str:
    """Retorna cor representativa para uma extensão."""
    lower_ext = ext.lower()
    if lower_ext in EXTENSION_COLORS:
        return EXTENSION_COLORS[lower_ext]
    # Gerar cor baseada no hash se for desconhecida
    palette = ["#95a5a6", "#7f8c8d", "#34495e", "#576574", "#8395a7", "#636e72"]
    return palette[abs(hash(lower_ext)) % len(palette)]


class DiskScanner:
    """Motor de análise e varredura de diretórios e unidades de disco."""

    def __init__(self, max_top_files: int = 100):
        self.max_top_files = max_top_files

    def scan(
        self,
        root_path: str,
        cancel_event=None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> ScanResult:
        """
        Executa a varredura completa da pasta raiz e subpastas.
        on_progress recebe: (arquivos_lidos, pastas_lidas, pasta_atual)
        """
        start_time = time.time()
        root_path = os.path.abspath(root_path)

        result = ScanResult(root_path=root_path)
        if not os.path.exists(root_path):
            return result

        total_files = 0
        total_dirs = 0
        last_progress_time = 0.0

        # Min-heap para os maiores arquivos: armazena (size, counter, FileItem)
        top_heap: List[Tuple[int, int, FileItem]] = []
        heap_counter = 0

        # Mapa de extensões: ext -> [total_size, file_count]
        ext_map: Dict[str, List[int]] = {}

        def _scan_dir(current_path: str) -> DirItem:
            nonlocal total_files, total_dirs, last_progress_time, heap_counter

            if cancel_event and cancel_event.is_set():
                return DirItem(path=current_path, name=os.path.basename(current_path) or current_path)

            total_dirs += 1
            dir_name = os.path.basename(current_path) or current_path
            current_dir_item = DirItem(path=current_path, name=dir_name)

            # Notificar progresso em intervalos de 50ms para não sobrecarregar a UI
            now = time.time()
            if now - last_progress_time > 0.05 and on_progress:
                on_progress(total_files, total_dirs, current_path)
                last_progress_time = now

            try:
                with os.scandir(current_path) as entries:
                    for entry in entries:
                        if cancel_event and cancel_event.is_set():
                            break

                        try:
                            # Ignorar junções e links simbólicos que poderiam causar loops infinitos
                            is_symlink = entry.is_symlink()
                            if is_symlink:
                                continue

                            if entry.is_file(follow_symlinks=False):
                                stat = entry.stat(follow_symlinks=False)
                                file_size = stat.st_size
                                ext = os.path.splitext(entry.name)[1].lower() or "(sem ext)"

                                total_files += 1
                                current_dir_item.direct_size += file_size
                                current_dir_item.total_size += file_size
                                current_dir_item.file_count += 1

                                # Extensões
                                if ext not in ext_map:
                                    ext_map[ext] = [0, 0]
                                ext_map[ext][0] += file_size
                                ext_map[ext][1] += 1

                                # Top Maiores Arquivos via Min-Heap
                                file_item = FileItem(
                                    path=entry.path,
                                    name=entry.name,
                                    size=file_size,
                                    ext=ext,
                                    dir_path=current_path,
                                )

                                if len(top_heap) < self.max_top_files:
                                    heap_counter += 1
                                    heapq.heappush(top_heap, (file_size, heap_counter, file_item))
                                elif file_size > top_heap[0][0]:
                                    heap_counter += 1
                                    heapq.heapreplace(top_heap, (file_size, heap_counter, file_item))

                            elif entry.is_dir(follow_symlinks=False):
                                sub_item = _scan_dir(entry.path)
                                current_dir_item.children.append(sub_item)
                                current_dir_item.total_size += sub_item.total_size
                                current_dir_item.file_count += sub_item.file_count
                                current_dir_item.subdirs_count += 1 + sub_item.subdirs_count

                        except (PermissionError, FileNotFoundError, OSError):
                            continue

            except (PermissionError, FileNotFoundError, OSError):
                pass

            return current_dir_item

        root_item = _scan_dir(root_path)

        # Ordenar filhos da raiz por tamanho decrescente
        root_item.children.sort(key=lambda x: x.total_size, reverse=True)

        # Ordenar lista de maiores arquivos (do maior para o menor)
        sorted_top_files = [item[2] for item in sorted(top_heap, key=lambda x: x[0], reverse=True)]

        # Consolidar estatísticas de extensões
        ext_stats = []
        for ext, (size, count) in ext_map.items():
            ext_stats.append(
                ExtensionStat(
                    ext=ext,
                    total_size=size,
                    file_count=count,
                    color=get_color_for_ext(ext),
                )
            )
        ext_stats.sort(key=lambda x: x.total_size, reverse=True)

        result.root_dir = root_item
        result.total_size = root_item.total_size
        result.total_files = total_files
        result.total_dirs = total_dirs
        result.elapsed_seconds = max(0.01, round(time.time() - start_time, 2))
        result.subfolders = root_item.children
        result.top_files = sorted_top_files
        result.extensions = ext_stats

        if on_progress:
            on_progress(total_files, total_dirs, "Concluído")

        return result


@dataclass
class TreemapRect:
    x0: float
    y0: float
    x1: float
    y1: float
    data: Any
    label: str
    size: int
    color: str


def compute_squarified_treemap(
    items: List[Dict[str, Any]],
    width: float,
    height: float,
    x: float = 0.0,
    y: float = 0.0,
    padding: float = 1.5,
) -> List[TreemapRect]:
    """
    Algoritmo de Treemap (Squarified Layout) que divide um retângulo proporcionalmente
    aos valores dos itens preservando proporções aproximadas de retângulos/quadrados.
    items deve ser uma lista de dicionários com 'size', 'label', 'color', 'data'.
    """
    valid_items = [it for it in items if it.get("size", 0) > 0]
    if not valid_items or width <= padding * 2 or height <= padding * 2:
        return []

    valid_items.sort(key=lambda it: it["size"], reverse=True)
    total_val = sum(it["size"] for it in valid_items)
    if total_val <= 0:
        return []

    rectangles: List[TreemapRect] = []

    def _squarify(children: List[Dict[str, Any]], rx: float, ry: float, rw: float, rh: float):
        if not children or rw <= padding * 2 or rh <= padding * 2:
            return

        c_total = sum(c["size"] for c in children)
        if c_total <= 0:
            return

        if len(children) == 1:
            item = children[0]
            rectangles.append(
                TreemapRect(
                    x0=rx + padding,
                    y0=ry + padding,
                    x1=rx + rw - padding,
                    y1=ry + rh - padding,
                    data=item.get("data"),
                    label=item.get("label", ""),
                    size=item.get("size", 0),
                    color=item.get("color", "#3498db"),
                )
            )
            return

        is_horizontal = rw >= rh

        half_total = c_total / 2.0
        acc = 0
        split_idx = 1
        for i, child in enumerate(children):
            acc += child["size"]
            if acc >= half_total:
                split_idx = max(1, i + 1)
                break

        group1 = children[:split_idx]
        group2 = children[split_idx:]

        g1_total = sum(c["size"] for c in group1)
        ratio1 = g1_total / c_total

        if is_horizontal:
            w1 = rw * ratio1
            w2 = rw - w1
            _squarify(group1, rx, ry, w1, rh)
            _squarify(group2, rx + w1, ry, w2, rh)
        else:
            h1 = rh * ratio1
            h2 = rh - h1
            _squarify(group1, rx, ry, rw, h1)
            _squarify(group2, rx, ry + h1, rw, h2)

    _squarify(valid_items, x, y, width, height)
    return rectangles
