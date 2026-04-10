"""
YouTube動画アップロードモジュール
OAuth 2.0 認証を使って動画を投稿する
"""
import os
import json
import pickle
from datetime import datetime
from config import (YOUTUBE_CLIENT_SECRET_FILE, YOUTUBE_TOKEN_FILE,
                    YOUTUBE_CHANNEL_ID)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def get_authenticated_service():
    """YouTube APIの認証済みサービスを返す。"""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    # 保存済みトークンがあれば読み込む
    if os.path.exists(YOUTUBE_TOKEN_FILE):
        with open(YOUTUBE_TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # トークンが無効か期限切れなら再取得
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(YOUTUBE_CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"client_secret.json が見つかりません: {YOUTUBE_CLIENT_SECRET_FILE}\n"
                    "Google Cloud Console から OAuth 2.0 認証情報をダウンロードして配置してください。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # トークンを保存
        with open(YOUTUBE_TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: str, thumbnail_path: str, script_data: dict) -> str:
    """動画をYouTubeにアップロードする。"""
    from googleapiclient.http import MediaFileUpload

    title = script_data.get("title", "雑学まとめ")
    description = script_data.get("description", "")
    tags = script_data.get("tags", ["雑学", "豆知識", "面白い話"])

    # 説明文にフッターを追加
    full_description = f"""{description}

━━━━━━━━━━━━━━━━━━━━━
📌 このチャンネルでは毎日雑学をお届けしています！
チャンネル登録・高評価よろしくお願いします！
━━━━━━━━━━━━━━━━━━━━━

#雑学 #豆知識 #面白い話 #知識 #{' #'.join(tags[:3])}

投稿日時: {datetime.now().strftime('%Y年%m月%d日')}"""

    print(f"  YouTube にアップロード中: 「{title}」")
    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": full_description[:5000],
            "tags": tags + ["雑学", "豆知識", "面白い話", "知識"],
            "categoryId": "27",  # Education カテゴリ
            "defaultLanguage": "ja",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4",
                            resumable=True, chunksize=1024 * 1024 * 10)

    request = youtube.videos().insert(part=",".join(body.keys()),
                                      body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  アップロード進捗: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"  アップロード完了！ Video ID: {video_id}")

    # サムネイルをアップロード
    if os.path.exists(thumbnail_path):
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print("  サムネイルをアップロードしました。")

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  動画URL: {video_url}")
    return video_url


def check_credentials_ready() -> bool:
    """認証情報が準備できているか確認する。"""
    return os.path.exists(YOUTUBE_CLIENT_SECRET_FILE)
