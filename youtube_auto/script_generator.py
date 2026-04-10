"""
OpenAI APIを使って10分間の雑学動画スクリプトを自動生成する
"""
import json
import random
from openai import OpenAI
from config import OPENAI_API_KEY
from collector import load_collected_topics

client = OpenAI(api_key=OPENAI_API_KEY)

TARGET_WORDS = 2000  # 10分 ≒ 2000字


def pick_topics(n: int = 5) -> list[str]:
    """蓄積トピックからランダムにn件選ぶ。"""
    topics = load_collected_topics()
    if not topics:
        return ["宇宙の不思議", "人体の謎", "歴史の裏側", "動物の秘密", "食べ物の雑学"]
    selected = random.sample(topics, min(n, len(topics)))
    return [t.get("title", t.get("description", "")) for t in selected]


def generate_script(topics: list[str] | None = None) -> dict:
    """
    スクリプトを生成して返す。
    返り値: {title, description, tags, sections: [{heading, content}], full_text}
    """
    if topics is None:
        topics = pick_topics(5)

    topic_list = "\n".join(f"- {t}" for t in topics)

    prompt = f"""あなたはYouTubeの雑学チャンネルのプロのナレーターです。
以下のテーマを参考にして、約10分間（約{TARGET_WORDS}文字）の雑学動画の台本を作成してください。

参考テーマ:
{topic_list}

要件:
- 視聴者を引き込む導入（30秒程度）
- 5〜7個の雑学トピックを紹介（各1〜2分）
- 各トピックは「驚きの事実」→「詳しい説明」→「日常との関連」の構成
- 締めくくりのまとめ（30秒程度）
- 全体的に親しみやすく、テンポよく話すトーン
- 視聴者への問いかけを2〜3回入れる

以下のJSON形式で出力してください：
{{
  "title": "動画タイトル（30文字以内、キャッチー）",
  "description": "YouTube概要欄の文章（200文字程度）",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "sections": [
    {{"heading": "セクション名", "content": "セクションの台本内容"}},
    ...
  ]
}}"""

    print("  スクリプトを生成中...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        max_tokens=4000,
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    # full_text を結合
    full_text = "\n\n".join(
        f"【{s['heading']}】\n{s['content']}"
        for s in data.get("sections", [])
    )
    data["full_text"] = full_text
    data["topics_used"] = topics

    print(f"  スクリプト生成完了: 「{data['title']}」({len(full_text)}文字)")
    return data
