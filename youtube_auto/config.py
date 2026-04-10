import os

# OpenAI API（.envファイルまたは環境変数から読み込む）
def _load_env():
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# YouTube設定
YOUTUBE_CHANNEL_ID = "UC9OU39CTBi2fPEtXJAQdh8w"
YOUTUBE_API_KEY = ""         # Google Cloud Console で取得（検索用）
YOUTUBE_CLIENT_SECRET_FILE = os.path.join(os.path.dirname(__file__), "client_secret.json")  # OAuth用
YOUTUBE_TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")

# 動画設定
SEARCH_QUERY = "雑学"        # 情報収集の検索キーワード
VIDEO_DURATION_MINUTES = 10  # 目標動画長
POST_HOUR = 23               # 投稿時刻（23時）
POST_MINUTE = 0

# ファイルパス
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# 動画スペック
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 24
FONT_SIZE_TITLE = 72
FONT_SIZE_BODY = 48
FONT_SIZE_SMALL = 36

# 色設定（背景・テキスト）
BG_COLOR = (15, 15, 35)           # 濃い紺
TITLE_COLOR = (255, 215, 0)        # ゴールド
TEXT_COLOR = (240, 240, 240)       # 白
ACCENT_COLOR = (100, 180, 255)     # 水色
SUBTITLE_COLOR = (200, 200, 200)   # グレー
