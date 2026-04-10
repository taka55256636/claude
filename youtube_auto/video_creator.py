"""
スクリプト + 音声 から動画を生成するモジュール
moviepy を使ってスライド動画を作成する
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
from config import (OUTPUT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS,
                    BG_COLOR, TITLE_COLOR, TEXT_COLOR, ACCENT_COLOR)

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_PATH_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_PATH_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _get_font_path(bold=True):
    paths = [FONT_PATH if bold else FONT_PATH_REG, FONT_PATH_FALLBACK]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def create_slide_image(heading: str, content: str, slide_num: int,
                       total_slides: int) -> str:
    """1スライドのPNG画像を生成して保存する。"""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    fp_bold = _get_font_path(bold=True)
    fp_reg = _get_font_path(bold=False)
    font_title = ImageFont.truetype(fp_bold, 64) if fp_bold else ImageFont.load_default()
    font_body = ImageFont.truetype(fp_reg or fp_bold, 42) if (fp_reg or fp_bold) else ImageFont.load_default()
    font_small = ImageFont.truetype(fp_reg or fp_bold, 30) if (fp_reg or fp_bold) else ImageFont.load_default()

    # 上部バー
    draw.rectangle([0, 0, VIDEO_WIDTH, 10], fill=TITLE_COLOR)
    # 下部バー
    draw.rectangle([0, VIDEO_HEIGHT - 10, VIDEO_WIDTH, VIDEO_HEIGHT], fill=TITLE_COLOR)

    # スライド番号（右上）
    slide_text = f"{slide_num}/{total_slides}"
    draw.text((VIDEO_WIDTH - 120, 25), slide_text, font=font_small, fill=ACCENT_COLOR)

    # セクション見出し
    y = 60
    draw.text((80, y), f"◆ {heading}", font=font_title, fill=TITLE_COLOR)
    y += 90

    # 区切り線
    draw.rectangle([80, y, VIDEO_WIDTH - 80, y + 3], fill=ACCENT_COLOR)
    y += 30

    # 本文（折り返し）
    wrapped_lines = []
    for paragraph in content.split("\n"):
        wrapped_lines.extend(textwrap.wrap(paragraph, width=36) or [""])

    line_height = 55
    for line in wrapped_lines:
        if y + line_height > VIDEO_HEIGHT - 60:
            break
        draw.text((80, y), line, font=font_body, fill=TEXT_COLOR)
        y += line_height

    path = os.path.join(OUTPUT_DIR, f"slide_{slide_num:02d}.png")
    img.save(path)
    return path


def create_title_slide(title: str) -> str:
    """タイトルスライドを生成する。"""
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (10, 10, 30))
    draw = ImageDraw.Draw(img)

    fp = _get_font_path(bold=True)
    font_big = ImageFont.truetype(fp, 90) if fp else ImageFont.load_default()
    font_med = ImageFont.truetype(fp, 50) if fp else ImageFont.load_default()

    # 装飾ライン
    for i, y in enumerate(range(0, VIDEO_HEIGHT, 60)):
        alpha = max(0, 30 - i * 2)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(30, 30, 80))

    # タイトル中央表示
    wrapped = textwrap.wrap(title, width=18)
    total_h = len(wrapped) * 100
    y = (VIDEO_HEIGHT - total_h) // 2 - 30
    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        w = bbox[2] - bbox[0]
        draw.text(((VIDEO_WIDTH - w) // 2 + 3, y + 3), line, font=font_big, fill=(0, 0, 0, 150))
        draw.text(((VIDEO_WIDTH - w) // 2, y), line, font=font_big, fill=TITLE_COLOR)
        y += 100

    # チャンネル名
    ch_text = "雑学チャンネル"
    bbox = draw.textbbox((0, 0), ch_text, font=font_med)
    w = bbox[2] - bbox[0]
    draw.text(((VIDEO_WIDTH - w) // 2, VIDEO_HEIGHT - 100), ch_text, font=font_med, fill=ACCENT_COLOR)

    path = os.path.join(OUTPUT_DIR, "slide_00.png")
    img.save(path)
    return path


def build_video(script_data: dict, audio_path: str, output_path: str) -> str:
    """スクリプトと音声から動画を生成する。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    sections = script_data.get("sections", [])
    title = script_data.get("title", "雑学まとめ")

    # 音声の長さを取得
    audio = AudioFileClip(audio_path)
    total_duration = audio.duration

    # 各スライドの表示時間を均等割り
    title_duration = 5.0  # タイトルスライド5秒
    section_duration = (total_duration - title_duration) / max(len(sections), 1)

    print(f"  動画生成中: {len(sections)}セクション, 合計{total_duration:.0f}秒")

    clips = []

    # タイトルスライド
    title_path = create_title_slide(title)
    title_clip = ImageClip(title_path).with_duration(title_duration)
    clips.append(title_clip)

    # 各セクションスライド
    for i, section in enumerate(sections, 1):
        slide_path = create_slide_image(
            section.get("heading", ""),
            section.get("content", ""),
            i,
            len(sections)
        )
        slide_clip = ImageClip(slide_path).with_duration(section_duration)
        clips.append(slide_clip)

    # 動画を結合
    final_video = concatenate_videoclips(clips, method="compose")
    final_video = final_video.with_audio(audio)
    final_video = final_video.with_fps(VIDEO_FPS)

    final_video.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        verbose=False,
        logger=None,
    )

    # 一時スライド画像を削除
    import glob
    for f in glob.glob(os.path.join(OUTPUT_DIR, "slide_*.png")):
        os.remove(f)

    print(f"  動画生成完了: {output_path}")
    return output_path
