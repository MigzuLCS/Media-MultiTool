import os
import sys
import shutil
import zipfile
from pathlib import Path

def build():
    root = Path(__file__).resolve().parent
    dist_dir = root / "dist"
    build_dir = root / "build"
    app_name = "Media MultiTool"
    icon_path = root / "assets" / "icon.ico"

    print("==================================================")
    print("      Media MultiTool - Empacotador Portátil      ")
    print("==================================================")
    print(f"[INFO] Raiz do projeto: {root}")

    # 1. Garantir que os ícones existem
    if not icon_path.exists():
        print("[INFO] Gerando ícone oficial...")
        import generate_icon
        generate_icon.generate_media_multitool_icon(root / "assets")

    # 2. Argumentos do PyInstaller
    args = [
        str(root / "run.py"),
        f"--name={app_name}",
        "--noconsole",
        "--onedir",
        f"--icon={icon_path}",
        "--clean",
        "--noconfirm",
        # Coletar dados e temas do CustomTkinter
        "--collect-all=customtkinter",
        # Coletar yt-dlp
        "--collect-submodules=yt_dlp",
        # Incluir pasta de assets
        f"--add-data={root / 'assets'}{os.pathsep}assets",
    ]

    # Se a pasta bin com ffmpeg existir, incluir no pacote
    bin_dir = root / "bin"
    if bin_dir.exists() and any(bin_dir.iterdir()):
        print("[INFO] Pasta bin/ com binários detectada. Incluindo no pacote...")
        args.append(f"--add-data={bin_dir}{os.pathsep}bin")

    print("[INFO] Iniciando compilação com PyInstaller...")
    import PyInstaller.__main__
    PyInstaller.__main__.run(args)

    output_app_dir = dist_dir / app_name
    if not output_app_dir.exists():
        print("[ERRO] Falha: diretório de saída não foi gerado.")
        sys.exit(1)

    # Garantir que a pasta bin/ com ffmpeg fique na raiz do aplicativo distribuído
    if bin_dir.exists() and any(bin_dir.iterdir()):
        dest_bin = output_app_dir / "bin"
        if not dest_bin.exists():
            print("[INFO] Copiando pasta bin/ para dist/Media MultiTool/bin...")
            shutil.copytree(bin_dir, dest_bin)

    # 3. Compactar em arquivo ZIP para distribuição
    zip_filename = f"Media-MultiTool-Windows-x64"
    zip_target = dist_dir / f"{zip_filename}.zip"
    if zip_target.exists():
        zip_target.unlink()

    print(f"[INFO] Criando pacote ZIP portátil: {zip_target.name}...")
    shutil.make_archive(str(dist_dir / zip_filename), "zip", dist_dir, app_name)

    size_mb = zip_target.stat().st_size / (1024 * 1024)
    print("==================================================")
    print(f"[SUCESSO] Pacote gerado com sucesso!")
    print(f"Pasta executável: {output_app_dir}")
    print(f"Arquivo ZIP portátil: {zip_target} ({size_mb:.2f} MB)")
    print("==================================================")

if __name__ == "__main__":
    build()
