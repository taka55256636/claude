"""
サムネイル自動生成モジュール
Pillowを使ってYouTubeサムネイル（1280x720）を生成する
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import OUTPUT_DIR

THUMB_W = 1280
THUMB_H = 720
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_PATH_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font(size: int):
    """フォントを取得する（日本語対応）。"""
    for path in [FONT_PATH, FONT_PATH_FALLBACK]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def create_gradient_bg(width: int, height: int, color1=(10, 10, 40), color2=(40, 10, 80)) -> Image.Image:
    """グラデーション背景を生成する。"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return img


def draw_decorations(draw: ImageDraw.Draw, width: int, height: int):
    """装飾要素を描く（円・ライン等）。"""
    # 右上に大きな円
    draw.ellipse([width - 300, -100, width + 100, 300], fill=(60, 0, 120, 80))
    # 左下に小さな円
    draw.ellipse([-50, height - 200, 200, height + 50], fill=(0, 60, 120, 80))
    # 上部のゴールドライン
    draw.rectangle([60, 60, width - 60, 68], fill=(255, 215, 0))
    # 下部のゴールドライン
    draw.rectangle([60, height - 68, width - 60, height - 60], fill=(255, 215, 0))


def create_thumbnail(title: str, subtitle: str = "知らないと損する！", output_path: str = None) -> str:
    """サムネイルを生成して保存する。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "thumbnail.jpg")

    # 背景
    img = create_gradient_bg(THUMB_W, THUMB_H)
    draw = ImageDraw.Draw(img, "RGBA")
    draw_decorations(draw, THUMB_W, THUMB_H)

    # 上部ラベル
    label_font = get_font(40)
    draw.rectangle([60, 80, 360, 130], fill=(255, 50, 50))
    draw.text((80, 85), "【雑学チャンネル】", font=label_font, fill=(255, 255, 255))

    # タイトル（折り返し対応）
    title_font = get_font(80)
    wrapped = textwrap.wrap(title, width=14)
    y_start = 180
    for line in wrapped[:3]:  # 最大3行
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        x = (THUMB_W - w) // 2
        # シャドウ
        draw.text((x + 3, y_start + 3), line, font=title_font, fill=(0, 0, 0, 180))
        draw.text((x, y_start), line, font=title_font, fill=(255, 215, 0))
        y_start += 95

    # サブタイトル
    sub_font = get_font(52)
    sub_wrapped = textwrap.wrap(subtitle, width=20)
    for line in sub_wrapped[:2]:
        bbox = draw.textbbox((0, 0), line, font=sub_font)
        w = bbox[2] - bbox[0]
        x = (THUMB_W - w) // 2
        draw.text((x, y_start + 10), line, font=sub_font, fill=(200, 230, 255))
        y_start += 65

    # 右下にアイコン的な文字
    icon_font = get_font(100)
    draw.text((THUMB_W - 160, THUMB_H - 150), "✨", font=icon_font, fill=(255, 215, 0))

    img.save(output_path, "JPEG", quality=95)
    print(f"  サムネイル生成完了: {output_path}")
    return output_path
