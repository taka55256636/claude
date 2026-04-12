"""
YouTube Shorts用の縦型1分動画を自動生成するモジュール
解像度: 1080x1920（縦型）、最大60秒
"""
import os
import textwrap
from PIL import Image, ImageDraw, ImageFont
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
from openai import OpenAI
from config import OPENAI_API_KEY, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)

SHORTS_W = 1080
SHORTS_H = 1920
FONT_BOLD = "/home/takah/.local/share/fonts/NotoSansCJKjp-Bold.otf"
FONT_REG = "/home/takah/.local/share/fonts/NotoSansCJKjp-Regular.otf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(size: int, bold=True):
    path = FONT_BOLD if bold else FONT_REG
    if not os.path.exists(path):
        path = FONT_FALLBACK
    return ImageFont.truetype(path, size)


def generate_shorts_script(topics: list[str]) -> dict:
    """60秒ショート用スクリプトを生成する。"""
    topic_list = "\n".join(f"- {t}" for t in topics[:3])
    prompt = f"""あなたはYouTube Shortsの雑学クリエイターです。
以下のテーマから1つ選び、約60秒（約300文字）のショート動画台本を作成してください。

参考テーマ:
{topic_list}

要件:
- 冒頭3秒で「知ってた？〇〇が〇〇なんだって！」形式で視聴者の興味を引く
- 1つのトピックを深掘り（詳細・理由・面白ポイント）
- 最後に「チャンネル登録してね！」で締める
- 合計300文字以内

以下のJSON形式で出力:
{{
  "title": "タイトル（20文字以内、#Shorts含む）",
  "hook": "冒頭のつかみ（30文字以内）",
  "body": "本文台本（200文字以内）",
  "outro": "締めの言葉（30文字以内）",
  "full_text": "hook + body + outro の全文"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=1000,
    )
    import json
    data = json.loads(response.choices[0].message.content)
    print(f"  Shortsスクリプト生成完了: 「{data['title']}」")
    return data


def create_shorts_slide(text: str, heading: str, slide_num: int, total: int,
                         bg_color=(10, 10, 40)) -> str:
    """縦型スライド画像を生成する。"""
    img = Image.new("RGB", (SHORTS_W, SHORTS_H), bg_color)
    draw = ImageDraw.Draw(img)

    # グラデーション風背景
    for y in range(SHORTS_H):
        ratio = y / SHORTS_H
        r = int(bg_color[0] + (60 - bg_color[0]) * ratio)
        g = int(bg_color[1] + (20 - bg_color[1]) * ratio)
        b = int(bg_color[2] + (80 - bg_color[2]) * ratio)
        draw.line([(0, y), (SHORTS_W, y)], fill=(r, g, b))

    # 上下バー
    draw.rectangle([0, 0, SHORTS_W, 12], fill=(255, 215, 0))
    draw.rectangle([0, SHORTS_H - 12, SHORTS_W, SHORTS_H], fill=(255, 215, 0))

    # #Shortsロゴ
    f_label = _font(50)
    draw.rectangle([40, 40, 260, 100], fill=(255, 0, 80))
    draw.text((55, 48), "#Shorts", font=f_label, fill=(255, 255, 255))

    # AIバッジ（右上）
    f_ai = _font(44)
    draw.rectangle([SHORTS_W - 280, 40, SHORTS_W - 40, 100], fill=(0, 150, 255))
    draw.text((SHORTS_W - 270, 50), "🤖 AI生成", font=f_ai, fill=(255, 255, 255))

    # 見出し
    f_head = _font(80, bold=True)
    wrapped_head = textwrap.wrap(heading, width=10)
    y = 150
    for line in wrapped_head[:2]:
        bbox = draw.textbbox((0, 0), line, font=f_head)
        w = bbox[2] - bbox[0]
        draw.text(((SHORTS_W - w) // 2 + 3, y + 3), line, font=f_head, fill=(0, 0, 0, 150))
        draw.text(((SHORTS_W - w) // 2, y), line, font=f_head, fill=(255, 215, 0))
        y += 95

    # 区切り線
    draw.rectangle([60, y + 10, SHORTS_W - 60, y + 14], fill=(100, 180, 255))
    y += 40

    # 本文
    f_body = _font(58, bold=False)
    wrapped = []
    for para in text.split("\n"):
        wrapped.extend(textwrap.wrap(para, width=16) or [""])

    line_h = 75
    for line in wrapped:
        if y + line_h > SHORTS_H - 200:
            break
        draw.text((60, y), line, font=f_body, fill=(240, 240, 240))
        y += line_h

    # チャンネル登録CTA（下部）
    f_cta = _font(52, bold=True)
    cta = "👍 チャンネル登録お願いします！"
    bbox = draw.textbbox((0, 0), cta, font=f_cta)
    w = bbox[2] - bbox[0]
    draw.rectangle([0, SHORTS_H - 160, SHORTS_W, SHORTS_H - 20], fill=(255, 50, 50))
    draw.text(((SHORTS_W - w) // 2, SHORTS_H - 130), cta, font=f_cta, fill=(255, 255, 255))

    path = os.path.join(OUTPUT_DIR, f"shorts_slide_{slide_num:02d}.png")
    img.save(path)
    return path


def build_shorts_video(script_data: dict, audio_path: str, output_path: str) -> str:
    """Shorts動画を生成する（縦型・最大60秒）。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    audio = AudioFileClip(audio_path)
    total_duration = min(audio.duration, 60.0)  # Shortsは最大60秒

    sections = [
        {"heading": "今日の雑学", "content": script_data.get("hook", "") + "\n\n" + script_data.get("body", "")},
        {"heading": "まとめ", "content": script_data.get("outro", "チャンネル登録してね！")},
    ]

    section_duration = total_duration / len(sections)
    clips = []

    for i, sec in enumerate(sections):
        path = create_shorts_slide(sec["content"], sec["heading"], i, len(sections))
        clips.append(ImageClip(path).with_duration(section_duration))

    final = concatenate_videoclips(clips, method="compose")
    final = final.with_audio(audio.subclipped(0, total_duration))
    final = final.with_fps(30)

    final.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)

    import glob
    for f in glob.glob(os.path.join(OUTPUT_DIR, "shorts_slide_*.png")):
        os.remove(f)

    print(f"  Shorts動画生成完了: {output_path}")
    return output_path
