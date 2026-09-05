import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

def generate_media_multitool_icon(output_dir: Path):
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    
    # 1. Base Squircle (Fundo com cantos arredondados)
    margin = 80
    corner_radius = 210
    
    # Sombra suave sob o squircle
    shadow_offset = 24
    shadow_mask = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_mask)
    shadow_box = [margin, margin + shadow_offset, size - margin, size - margin + shadow_offset]
    shadow_draw.rounded_rectangle(shadow_box, radius=corner_radius, fill=(0, 0, 0, 140))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(32))
    img.alpha_composite(shadow_mask)
    
    # Squircle com gradiente escuro futurista
    squircle_mask = Image.new("L", (size, size), 0)
    s_draw = ImageDraw.Draw(squircle_mask)
    s_box = [margin, margin, size - margin, size - margin]
    s_draw.rounded_rectangle(s_box, radius=corner_radius, fill=255)
    
    bg_gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_gradient)
    for y in range(margin, size - margin):
        t = (y - margin) / float(size - 2 * margin)
        r = int(18 + t * (30 - 18))
        g = int(24 + t * (27 - 24))
        b = int(48 + t * (85 - 48))
        bg_draw.line([(margin, y), (size - margin, y)], fill=(r, g, b, 255))
    
    bg_gradient.putalpha(squircle_mask)
    img.alpha_composite(bg_gradient)
    
    # Borda sutil neon no contorno
    border_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(border_img)
    b_draw.rounded_rectangle(s_box, radius=corner_radius, outline=(99, 102, 241, 180), width=6)
    img.alpha_composite(border_img)
    
    # 2. Barras de onda sonora à esquerda (3 barras com cantos arredondados)
    bars_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bars_draw = ImageDraw.Draw(bars_img)
    
    bars_draw.rounded_rectangle([250, 410, 290, 614], radius=20, fill=(56, 189, 248, 240))  # Cyan
    bars_draw.rounded_rectangle([320, 310, 360, 714], radius=20, fill=(129, 140, 248, 250)) # Indigo
    bars_draw.rounded_rectangle([390, 370, 430, 654], radius=20, fill=(168, 85, 247, 240))  # Violet
    img.alpha_composite(bars_img)
    
    # Símbolo do PLAY à direita
    play_mask = Image.new("L", (size, size), 0)
    p_mask_draw = ImageDraw.Draw(play_mask)
    play_points = [(490, 320), (490, 704), (790, 512)]
    p_mask_draw.polygon(play_points, fill=255)
    
    play_mask = play_mask.filter(ImageFilter.GaussianBlur(14))
    play_mask = play_mask.point(lambda p: 255 if p > 128 else 0)
    
    play_gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pg_draw = ImageDraw.Draw(play_gradient)
    for x in range(450, 810):
        factor = (x - 450) / 360.0
        r = int(6 + factor * (236 - 6))
        g = int(182 + factor * (72 - 182))
        b = int(212 + factor * (153 - 212))
        pg_draw.line([(x, 280), (x, 740)], fill=(r, g, b, 255))
        
    play_gradient.putalpha(play_mask)
    
    play_glow = play_gradient.filter(ImageFilter.GaussianBlur(26))
    img.alpha_composite(play_glow)
    img.alpha_composite(play_gradient)
    
    # Salvar PNG de alta resolução
    png_path = output_dir / "icon.png"
    img.save(png_path, format="PNG")
    print(f"[OK] PNG: {png_path}")
    
    # Gerar arquivo ICO multi-resolução para Windows
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_path = output_dir / "icon.ico"
    img.save(ico_path, format="ICO", sizes=ico_sizes)
    print(f"[OK] ICO: {ico_path}")

if __name__ == "__main__":
    out = Path("assets").resolve()
    out.mkdir(parents=True, exist_ok=True)
    generate_media_multitool_icon(out)
