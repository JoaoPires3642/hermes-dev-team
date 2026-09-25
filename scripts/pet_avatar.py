#!/usr/bin/env python3
"""Gera o avatar do bot (assets/avatar.png, 160x160) a partir do sprite do pet.

Uso: pet_avatar.py <profile_dir> <pet_slug>
Pega o 1º quadro da animação "idle" (linha 0) do spritesheet do petdex
(quadros de 192x208), recorta o desenho, centraliza e amplia sem borrar.
"""
import sys
from pathlib import Path

from PIL import Image

FRAME_W, FRAME_H, SIZE, PAD = 192, 208, 160, 8

prof, slug = Path(sys.argv[1]), sys.argv[2]
sheet = Image.open(prof / "pets" / slug / "spritesheet.webp").convert("RGBA")
frame = sheet.crop((0, 0, FRAME_W, FRAME_H))
bbox = frame.getchannel("A").getbbox()
if bbox:
    frame = frame.crop(bbox)

scale = (SIZE - 2 * PAD) / max(frame.size)
new = (max(1, round(frame.width * scale)), max(1, round(frame.height * scale)))
frame = frame.resize(new, Image.NEAREST if scale >= 1 else Image.LANCZOS)

out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
out.paste(frame, ((SIZE - new[0]) // 2, (SIZE - new[1]) // 2), frame)
(prof / "assets").mkdir(exist_ok=True)
out.save(prof / "assets" / "avatar.png")
print(f"{prof.name}: avatar <- {slug}")
