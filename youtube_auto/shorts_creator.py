"""
YouTube Shorts用の縦型1分動画を自動生成するモジュール
解像度: 1080x1920（縦型）、最大60秒
スライド背景はDALL-E 3で生成したAI画像を使用
"""
import os
import io
import json
import textwrap
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips
from openai import OpenAI
from config import OPENAI_API_KEY, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)

SHORTS_W = 1080
SHORTS_H = 1920
FONT_BOLD = "/home/takah/.local/share/fonts/NotoSansCJKjp-Bold.otf"
FONT_REG  = "/home/takah/.local/share/fonts/NotoSansCJKjp-Regular.otf"
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
  "full_text": "hook + body + outro の全文",
  "image_prompt": "このトピックをイメージした鮮やかでインパクトのある縦型イラストのDALL-E用英語プロンプト（50語以内）"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=1000,
    )
    data = json.loads(response.choices[0].message.content)
    print(f"  Shortsスクリプト生成完了: 「{data['title']}」")
    return data


def generate_bg_image(image_prompt: str, slide_index: int) -> Image.Image | None:
    """DALL-E 3でスライド背景画像を生成する。"""
    try:
        # 縦型・インパクト重視のプロンプトに加工
        full_prompt = (
            f"{image_prompt}. "
            "Vertical portrait orientation 9:16, vivid dramatic colors, "
            "cinematic lighting, highly detailed digital art, no text."
        )
        print(f"  DALL-E 画像生成中（スライド{slide_index + 1}）...")
        resp = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1792",   # 縦型（9:16相当）
            quality="standard",
            n=1,
        )
        url = resp.data[0].url
        img_data = requests.get(url, timeout=30).content
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        # 1080x1920にリサイズ
        img = img.resize((SHORTS_W, SHORTS_H), Image.LANCZOS)
        return img
    except Exception as e:
        print(f"  ⚠️  DALL-E生成スキップ（グラデーション背景を使用）: {e}")
        return None


def create_shorts_slide(text: str, heading: str, slide_num: int, total: int,
                        image_prompt: str = "") -> str:
    """縦型スライド画像を生成する（DALL-E背景 + テキストオーバーレイ）。"""

    # 背景画像を生成（失敗時はグラデーション）
    bg = generate_bg_image(image_prompt or heading, slide_num)
    if bg is None:
        bg = Image.new("RGB", (SHORTS_W, SHORTS_H), (10, 10, 40))
        draw_bg = ImageDraw.Draw(bg)
        for y in range(SHORTS_H):
            ratio = y / SHORTS_H
            r = int(10 + 50 * ratio)
            g = int(10 + 10 * ratio)
            b = int(40 + 40 * ratio)
            draw_bg.line([(0, y), (SHORTS_W, y)], fill=(r, g, b))

    # 画像を少し暗くしてテキストを読みやすくする
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    # ぼかしを軽くかけてドラマチックに
    bg = bg.filter(ImageFilter.GaussianBlur(radius=1.5))

    draw = ImageDraw.Draw(bg, "RGBA")

    # ━━ 上部エリア ━━
    # 半透明の上部バー
    draw.rectangle([0, 0, SHORTS_W, 130], fill=(0, 0, 0, 160))

    # #Shortsロゴ
    f_label = _font(52)
    draw.rectangle([30, 30, 240, 95], fill=(255, 0, 80))
    draw.text((45, 38), "#Shorts", font=f_label, fill=(255, 255, 255))

    # AIバッジ（右上）
    f_ai = _font(44)
    draw.rectangle([SHORTS_W - 270, 30, SHORTS_W - 30, 95], fill=(0, 150, 255))
    draw.text((SHORTS_W - 258, 40), "🤖 AI生成", font=f_ai, fill=(255, 255, 255))

    # ━━ 中央エリア（見出し） ━━
    f_head = _font(88, bold=True)
    wrapped_head = textwrap.wrap(heading, width=9)
    # 見出しエリアに半透明背景
    head_lines = wrapped_head[:2]
    head_h = len(head_lines) * 105 + 20
    draw.rectangle([0, 200, SHORTS_W, 200 + head_h + 20], fill=(0, 0, 0, 120))

    y = 215
    for line in head_lines:
        bbox = draw.textbbox((0, 0), line, font=f_head)
        w = bbox[2] - bbox[0]
        # 文字シャドウ
        draw.text(((SHORTS_W - w) // 2 + 4, y + 4), line, font=f_head, fill=(0, 0, 0, 200))
        draw.text(((SHORTS_W - w) // 2, y), line, font=f_head, fill=(255, 215, 0))
        y += 105

    # ━━ 下部エリア（本文） ━━
    # 下半分に半透明グラデーションバー
    text_area_top = SHORTS_H // 2 + 100
    draw.rectangle([0, text_area_top, SHORTS_W, SHORTS_H - 160], fill=(0, 0, 0, 175))

    f_body = _font(54, bold=False)
    wrapped = []
    for para in text.split("\n"):
        wrapped.extend(textwrap.wrap(para, width=15) or [""])

    y = text_area_top + 30
    line_h = 72
    for line in wrapped:
        if y + line_h > SHORTS_H - 180:
            break
        draw.text((55, y), line, font=f_body, fill=(255, 255, 255))
        y += line_h

    # ━━ 最下部CTA ━━
    draw.rectangle([0, SHORTS_H - 155, SHORTS_W, SHORTS_H], fill=(220, 30, 30, 230))
    f_cta = _font(54, bold=True)
    cta = "👍 チャンネル登録お願いします！"
    bbox = draw.textbbox((0, 0), cta, font=f_cta)
    w = bbox[2] - bbox[0]
    draw.text(((SHORTS_W - w) // 2, SHORTS_H - 120), cta, font=f_cta, fill=(255, 255, 255))

    path = os.path.join(OUTPUT_DIR, f"shorts_slide_{slide_num:02d}.png")
    bg.save(path)
    return path


def build_shorts_video(script_data: dict, audio_path: str, output_path: str) -> str:
    """Shorts動画を生成する（縦型・最大60秒）。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    audio = AudioFileClip(audio_path)
    total_duration = min(audio.duration, 60.0)

    image_prompt = script_data.get("image_prompt", script_data.get("hook", ""))

    sections = [
        {
            "heading": "今日の雑学",
            "content": script_data.get("hook", "") + "\n\n" + script_data.get("body", ""),
            "image_prompt": image_prompt,
        },
        {
            "heading": "まとめ",
            "content": script_data.get("outro", "チャンネル登録してね！"),
            "image_prompt": image_prompt,
        },
    ]

    section_duration = total_duration / len(sections)
    clips = []

    for i, sec in enumerate(sections):
        path = create_shorts_slide(
            sec["content"], sec["heading"], i, len(sections),
            image_prompt=sec["image_prompt"]
        )
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
