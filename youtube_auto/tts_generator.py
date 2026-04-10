"""
OpenAI TTS APIを使って台本を音声ファイルに変換する
"""
import os
from pathlib import Path
from openai import OpenAI
from config import OPENAI_API_KEY, OUTPUT_DIR

client = OpenAI(api_key=OPENAI_API_KEY)

MAX_CHARS = 4096  # OpenAI TTS の1リクエスト最大文字数


def split_text(text: str, max_len: int = MAX_CHARS) -> list[str]:
    """テキストを最大文字数で分割する（句読点で区切る）。"""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for sentence in text.replace("。", "。\n").split("\n"):
        if len(current) + len(sentence) > max_len:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current += sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


def generate_audio(text: str, output_path: str) -> str:
    """テキストをTTSで音声ファイルに変換する。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    chunks = split_text(text)

    if len(chunks) == 1:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",          # 日本語に対応した自然な女性の声
            input=text,
            speed=1.0,
        )
        response.stream_to_file(output_path)
        print(f"  音声生成完了: {output_path}")
        return output_path

    # 複数チャンクを結合
    import subprocess
    chunk_files = []
    for i, chunk in enumerate(chunks):
        chunk_path = output_path.replace(".mp3", f"_chunk{i}.mp3")
        resp = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=chunk,
            speed=1.0,
        )
        resp.stream_to_file(chunk_path)
        chunk_files.append(chunk_path)

    # ffmpegで結合
    list_file = output_path.replace(".mp3", "_list.txt")
    with open(list_file, "w") as f:
        for cf in chunk_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")

    subprocess.run(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file,
         "-acodec", "copy", output_path, "-y"],
        check=True, capture_output=True
    )

    for cf in chunk_files:
        os.remove(cf)
    os.remove(list_file)

    print(f"  音声生成完了: {output_path} ({len(chunks)}チャンク結合)")
    return output_path
