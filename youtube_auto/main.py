#!/usr/bin/env python3
"""
YouTube雑学チャンネル自動運営システム
- 動画投稿時間（23:00）以外は情報収集
- 毎日23:00に通常動画（10分）を自動生成・投稿
- 毎日9:00/13:00/18:00/22:00にShorts（1分）を自動生成・投稿（1日4回）
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

# Shorts投稿スケジュール（1日4回）
SHORTS_SCHEDULE = [
    ( 9, 0),   # 第1回:  9:00
    (13, 0),   # 第2回: 13:00
    (18, 0),   # 第3回: 18:00
    (22, 0),   # 第4回: 22:00
]


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


def create_and_upload_shorts(slot: int = 1):
    """Shorts動画（1分）を生成してアップロードする。slot=1が1本目、2が2本目。"""
    print("\n" + "=" * 60)
    print(f"  【Shorts 生成開始 第{slot}回】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    audio_path = os.path.join(OUTPUT_DIR, f"shorts_audio_{date_str}_{slot}.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"shorts_{date_str}_{slot}.mp4")

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


def _stop_collect(collect_thread, stop_event):
    if collect_thread and collect_thread.is_alive():
        stop_event.set()
        collect_thread.join()
        stop_event.clear()


def _start_collect(stop_event):
    t = threading.Thread(target=collect_continuously, args=(30, stop_event), daemon=True)
    t.start()
    return t


def run_scheduler():
    """メインスケジューラー。"""
    shorts_times = ", ".join(f"{h:02d}:{m:02d}" for h, m in SHORTS_SCHEDULE)
    print("=" * 60)
    print("  YouTube雑学チャンネル自動運営システム 起動")
    print(f"  通常動画投稿: 毎日 {POST_HOUR:02d}:{POST_MINUTE:02d}")
    print(f"  Shorts投稿  : 毎日 {shorts_times}（1日2回）")
    print("  情報収集    : 投稿時間以外は30分ごとに実行")
    print("=" * 60)

    collect_once()

    posted_today = None
    # Shorts投稿済みフラグ: {(date, slot_index): True}
    shorts_posted = {}
    stop_event = threading.Event()
    collect_thread = _start_collect(stop_event)

    while True:
        now = datetime.now()
        today = now.date()
        did_post = False

        # Shorts投稿（1日2回チェック）
        for slot_idx, (sh, sm) in enumerate(SHORTS_SCHEDULE, 1):
            key = (today, slot_idx)
            if now.hour == sh and now.minute == sm and key not in shorts_posted:
                collect_thread = _stop_collect(collect_thread, stop_event) or collect_thread
                create_and_upload_shorts(slot=slot_idx)
                shorts_posted[key] = True
                collect_thread = _start_collect(stop_event)
                did_post = True
                break

        # 通常動画投稿（23:00）
        if not did_post and now.hour == POST_HOUR and now.minute == POST_MINUTE and posted_today != today:
            _stop_collect(collect_thread, stop_event)
            create_and_upload_video()
            posted_today = today
            collect_thread = _start_collect(stop_event)

        elif not collect_thread or not collect_thread.is_alive():
            collect_thread = _start_collect(stop_event)

        time.sleep(60)


if __name__ == "__main__":
    if "--once" in sys.argv:
        create_and_upload_video()
    elif "--shorts" in sys.argv:
        create_and_upload_shorts(slot=1)
    else:
        run_scheduler()
