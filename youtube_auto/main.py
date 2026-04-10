#!/usr/bin/env python3
"""
YouTube雑学チャンネル自動運営システム
- 動画投稿時間（23:00）以外は情報収集
- 毎日23:00に動画を自動生成・投稿
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
from tts_generator import generate_audio
from video_creator import build_video
from thumbnail_creator import create_thumbnail
from uploader import upload_video, check_credentials_ready


def create_and_upload_video():
    """動画を生成してアップロードする一連の処理。"""
    print("\n" + "=" * 60)
    print(f"  【動画生成開始】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    audio_path = os.path.join(OUTPUT_DIR, f"narration_{date_str}.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"video_{date_str}.mp4")
    thumb_path = os.path.join(OUTPUT_DIR, f"thumbnail_{date_str}.jpg")

    try:
        # 1. スクリプト生成
        print("\n[1/5] スクリプト生成中...")
        script = generate_script()

        # 2. 音声生成
        print("\n[2/5] 音声生成中...")
        generate_audio(script["full_text"], audio_path)

        # 3. サムネイル生成
        print("\n[3/5] サムネイル生成中...")
        subtitle = script["sections"][0]["heading"] if script.get("sections") else "今日の雑学"
        create_thumbnail(script["title"], subtitle, thumb_path)

        # 4. 動画生成
        print("\n[4/5] 動画生成中...")
        build_video(script, audio_path, video_path)

        # 5. YouTube アップロード
        print("\n[5/5] YouTubeにアップロード中...")
        if check_credentials_ready():
            url = upload_video(video_path, thumb_path, script)
            print(f"\n  ✅ 投稿完了: {url}")
        else:
            print("\n  ⚠️  YouTube認証情報が未設定のため、アップロードをスキップしました。")
            print("  動画は以下に保存されています:")
            print(f"    動画: {video_path}")
            print(f"    サムネイル: {thumb_path}")

        # 一時ファイルを削除（動画・サムネイルは残す）
        if os.path.exists(audio_path):
            os.remove(audio_path)

    except Exception as e:
        print(f"\n  ❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


def should_post_now() -> bool:
    """現在が投稿時刻かどうか確認する。"""
    now = datetime.now()
    return now.hour == POST_HOUR and now.minute == POST_MINUTE


def run_scheduler():
    """メインスケジューラー: 投稿時刻以外は情報収集を継続する。"""
    print("=" * 60)
    print("  YouTube雑学チャンネル自動運営システム 起動")
    print(f"  投稿時刻: 毎日 {POST_HOUR:02d}:{POST_MINUTE:02d}")
    print("  情報収集: 投稿時間以外は30分ごとに実行")
    print("=" * 60)

    # 起動時に一度情報収集
    collect_once()

    posted_today = None  # 本日の投稿済みフラグ

    stop_event = threading.Event()
    collect_thread = None

    while True:
        now = datetime.now()
        today = now.date()

        # 投稿時刻かつ本日未投稿なら動画を生成・投稿
        if should_post_now() and posted_today != today:
            # 情報収集を一時停止
            if collect_thread and collect_thread.is_alive():
                stop_event.set()
                collect_thread.join()
                stop_event.clear()

            create_and_upload_video()
            posted_today = today

            # 投稿後に情報収集を再開
            collect_thread = threading.Thread(
                target=collect_continuously,
                args=(30, stop_event),
                daemon=True
            )
            collect_thread.start()

        else:
            # 情報収集スレッドが止まっていれば再起動
            if collect_thread is None or not collect_thread.is_alive():
                collect_thread = threading.Thread(
                    target=collect_continuously,
                    args=(30, stop_event),
                    daemon=True
                )
                collect_thread.start()

        time.sleep(60)  # 1分ごとにチェック


if __name__ == "__main__":
    if "--once" in sys.argv:
        # テスト用: 1回だけ動画を生成して終了
        create_and_upload_video()
    else:
        run_scheduler()
