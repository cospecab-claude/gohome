# -*- coding: utf-8 -*-
"""트레이/exe 아이콘 (집 모양)을 코드로 그림.

python icon.py 로 실행하면 빌드용 gohome.ico 파일을 만든다.
"""
import os

from PIL import Image, ImageDraw

COLOR = (46, 125, 50, 255)  # 초록


def make(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64.0
    d.polygon([(32 * s, 6 * s), (60 * s, 30 * s), (4 * s, 30 * s)], fill=COLOR)  # 지붕
    d.rectangle([12 * s, 28 * s, 52 * s, 58 * s], fill=COLOR)                   # 몸체
    d.rectangle([27 * s, 40 * s, 37 * s, 58 * s], fill=(255, 255, 255, 255))    # 문
    return img


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gohome.ico")
    make(256).save(out, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
    print("saved:", out)
