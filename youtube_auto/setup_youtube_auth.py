#!/usr/bin/env python3
"""
YouTube OAuth認証のセットアップスクリプト
初回のみ実行が必要
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("""
========================================================
  YouTube OAuth2.0 認証セットアップ
========================================================

以下の手順で認証情報を取得してください：

1. https://console.cloud.google.com/ にアクセス
2. 新しいプロジェクトを作成（または既存のものを使用）
3. 「APIとサービス」→「ライブラリ」から
   「YouTube Data API v3」を有効化
4. 「APIとサービス」→「認証情報」→「認証情報を作成」
   →「OAuth 2.0 クライアント ID」を選択
5. アプリの種類：「デスクトップアプリ」を選択
6. ダウンロードした JSON ファイルを以下に配置:
   /home/takah/claude/youtube_auto/client_secret.json

配置が完了したら、このスクリプトを再実行してください。
========================================================
""")

from config import YOUTUBE_CLIENT_SECRET_FILE

if not os.path.exists(YOUTUBE_CLIENT_SECRET_FILE):
    print(f"⚠️  client_secret.json が見つかりません: {YOUTUBE_CLIENT_SECRET_FILE}")
    sys.exit(1)

print("client_secret.json を検出しました。認証フローを開始します...")

from uploader import get_authenticated_service

try:
    youtube = get_authenticated_service()
    # チャンネル情報を取得して確認
    response = youtube.channels().list(part="snippet", mine=True).execute()
    for ch in response.get("items", []):
        print(f"\n✅ 認証成功！")
        print(f"   チャンネル名: {ch['snippet']['title']}")
        print(f"   チャンネルID: {ch['id']}")
    print("\n token.json が保存されました。次回以降は自動的に認証されます。")
except Exception as e:
    print(f"❌ エラー: {e}")
