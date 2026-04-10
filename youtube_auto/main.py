#!/usr/bin/env python3
"""
YouTube雑学チャンネル自動運営システム
- 動画投稿時間（23:00）以外は情報収集
- 毎日23:00に通常動画（10分）を自動生成・投稿
- 毎日22:00にShorts（1分）を自動生成・投稿
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import time
import threading
from datetime import datetime
from config import POST_HOUR, POST_MINUTE, OUTPUT_DIR
from collector import collect_continuously, collect_once
from script_generator import generate_script
from shorts_creator import generate_shorts_script, build_shorts_video
from tts_generator import generate_audio
from video_creator import build_video
from thumbnail_creator import create_thumbnail
from uploader import upload_video, upload_shorts, check_credentials_ready

SHORTS_HOUR = 22   # Shorts投稿時刻
SHORTS_MINUTE = 0


def create_and_upload_video():
    """通常動画（10分）を生成してアップロードする。"""
    print("\n" + "=" * 60)
    print(f"  【通常動画 生成開始】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    audio_path = os.path.join(OUTPUT_DIR, f"narration_{date_str}.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"video_{date_str}.mp4")
    thumb_path = os.path.join(OUTPUT_DIR, f"thumbnail_{date_str}.jpg")

    try:
        print("\n[1/5] スクリプト生成中...")
        script = generate_script()

        print("\n[2/5] 音声生成中...")
        generate_audio(script["full_text"], audio_path)

        print("\n[3/5] サムネイル生成中...")
        subtitle = script["sections"][0]["heading"] if script.get("sections") else "今日の雑学"
        create_thumbnail(script["title"], subtitle, thumb_path)

        print("\n[4/5] 動画生成中...")
        build_video(script, audio_path, video_path)

        print("\n[5/5] YouTubeにアップロード中...")
        if check_credentials_ready():
            url = upload_video(video_path, thumb_path, script)
            print(f"\n  ✅ 通常動画 投稿完了: {url}")
        else:
            print("\n  ⚠️  認証情報未設定のためスキップ")

        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        print(f"\n  ❌ エラー: {e}")
        import traceback
        traceback.print_exc()


def create_and_upload_shorts():
    """Shorts動画（1分）を生成してアップロードする。"""
    print("\n" + "=" * 60)
    print(f"  【Shorts 生成開始】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    audio_path = os.path.join(OUTPUT_DIR, f"shorts_audio_{date_str}.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"shorts_{date_str}.mp4")

    try:
        from collector import load_collected_topics
        import random
        topics = load_collected_topics()
        topic_titles = [t.get("title", "") for t in random.sample(topics, min(3, len(topics)))] if topics else ["雑学"]

        print("\n[1/4] Shortsスクリプト生成中...")
        script = generate_shorts_script(topic_titles)

        print("\n[2/4] 音声生成中...")
        generate_audio(script["full_text"], audio_path)

        print("\n[3/4] Shorts動画生成中...")
        build_shorts_video(script, audio_path, video_path)

        print("\n[4/4] YouTubeにアップロード中...")
        if check_credentials_ready():
            url = upload_shorts(video_path, script)
            print(f"\n  ✅ Shorts 投稿完了: {url}")
        else:
            print("\n  ⚠️  認証情報未設定のためスキップ")

        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        print(f"\n  ❌ Shortsエラー: {e}")
        import traceback
        traceback.print_exc()


def run_scheduler():
    """メインスケジューラー。"""
    print("=" * 60)
    print("  YouTube雑学チャンネル自動運営システム 起動")
    print(f"  通常動画投稿: 毎日 {POST_HOUR:02d}:{POST_MINUTE:02d}")
    print(f"  Shorts投稿  : 毎日 {SHORTS_HOUR:02d}:{SHORTS_MINUTE:02d}")
    print("  情報収集    : 投稿時間以外は30分ごとに実行")
    print("=" * 60)

    collect_once()

    posted_today = None
    shorts_posted_today = None
    stop_event = threading.Event()
    collect_thread = None

    while True:
        now = datetime.now()
        today = now.date()

        # Shorts投稿（22:00）
        if now.hour == SHORTS_HOUR and now.minute == SHORTS_MINUTE and shorts_posted_today != today:
            if collect_thread and collect_thread.is_alive():
                stop_event.set()
                collect_thread.join()
                stop_event.clear()
            create_and_upload_shorts()
            shorts_posted_today = today
            collect_thread = threading.Thread(target=collect_continuously, args=(30, stop_event), daemon=True)
            collect_thread.start()

        # 通常動画投稿（23:00）
        elif now.hour == POST_HOUR and now.minute == POST_MINUTE and posted_today != today:
            if collect_thread and collect_thread.is_alive():
                stop_event.set()
                collect_thread.join()
                stop_event.clear()
            create_and_upload_video()
            posted_today = today
            collect_thread = threading.Thread(target=collect_continuously, args=(30, stop_event), daemon=True)
            collect_thread.start()

        else:
            if collect_thread is None or not collect_thread.is_alive():
                collect_thread = threading.Thread(target=collect_continuously, args=(30, stop_event), daemon=True)
                collect_thread.start()

        time.sleep(60)


if __name__ == "__main__":
    if "--once" in sys.argv:
        create_and_upload_video()
    elif "--shorts" in sys.argv:
        create_and_upload_shorts()
    else:
        run_scheduler()
