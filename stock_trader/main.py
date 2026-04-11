#!/usr/bin/env python3
"""
日本株デイトレード推薦システム
- 前日データをもとに当日の買い推薦銘柄を出力する
- 予算は雪だるま式に増加（利益を次日の予算に加算）
- 実行結果を日付付きテキストファイルに保存する
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import io
from datetime import date
from data_collector import fetch_all_stocks
from analyzer import analyze_all
from portfolio import load_portfolio, save_portfolio, show_summary, record_day
from config import TOP_N_STOCKS, MAX_BUDGET_RATIO

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")

DISCLAIMER = """
⚠️  免責事項: このシステムはあくまで参考情報です。
   株式投資には損失リスクがあります。最終的な投資判断はご自身でお願いします。
"""


def display_recommendations(recommendations: list, budget: int) -> str:
    """推薦銘柄を文字列で返す（表示兼ログ用）。"""
    lines = []
    lines.append("=" * 70)
    lines.append(f"  【本日の買い推薦銘柄】  予算: ¥{budget:,}")
    lines.append(f"  分析日: {date.today()}")
    lines.append("=" * 70)

    if not recommendations:
        lines.append("  本日の推薦銘柄はありません。")
        return "\n".join(lines)

    lines.append(f"  {'順位':^4} {'銘柄コード':^12} {'株価':^10} {'スコア':^8} "
                 f"{'RSI':^6} {'前日比':^8} {'最大購入株数':^12} {'投資額':^10}")
    lines.append("-" * 70)

    for i, rec in enumerate(recommendations[:TOP_N_STOCKS], 1):
        ticker_short = rec["ticker"].replace(".T", "")
        lines.append(f"  {i:^4} {ticker_short:^12} "
                     f"¥{rec['price']:>8,.0f} "
                     f"{rec['score']:>7.1f} "
                     f"{rec['rsi']:>5.1f} "
                     f"{rec['change_pct']:>+7.1f}% "
                     f"{rec['max_shares']:>10}株 "
                     f"¥{rec['max_investment']:>8,}")

    lines.append("\n  【詳細分析】")
    lines.append("-" * 70)
    for i, rec in enumerate(recommendations[:5], 1):
        ticker_short = rec["ticker"].replace(".T", "")
        lines.append(f"\n  #{i} {ticker_short}")
        lines.append(f"     株価: ¥{rec['price']:,.0f} | "
                     f"スコア: {rec['score']:.1f} | "
                     f"RSI: {rec['rsi']:.1f} | "
                     f"出来高比: {rec['vol_ratio']:.1f}倍")
        lines.append(f"     推薦理由: {', '.join(rec['reasons'])}")
        max_invest = int(rec['price'] * rec['max_shares'])
        lines.append(f"     推薦購入: {rec['max_shares']}株 (投資額 ¥{max_invest:,})")

    lines.append("\n  【本日の戦略】")
    lines.append("  ✅ 朝9:00-9:30に上記銘柄を確認し、値動きが安定したら購入")
    lines.append("  ✅ 15:00-15:30の引け前に売却（1日完結のデイトレード）")
    lines.append("  ✅ 損切りライン: -3%で損切りを推薦")

    return "\n".join(lines)


def save_log(content: str, portfolio: dict):
    """実行結果を日付付きテキストファイルに保存する。"""
    os.makedirs(LOG_DIR, exist_ok=True)
    today = date.today()
    log_path = os.path.join(LOG_DIR, f"{today}.txt")

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"実行日時: {today}\n")
        f.write(DISCLAIMER)
        f.write("\n")
        f.write(content)
        f.write("\n\n")
        # ポートフォリオサマリー
        from config import INITIAL_BUDGET
        history = portfolio.get("history", [])
        budget = portfolio.get("budget", INITIAL_BUDGET)
        total_profit = budget - INITIAL_BUDGET
        f.write("=" * 50 + "\n")
        f.write("  【ポートフォリオサマリー】\n")
        f.write("=" * 50 + "\n")
        f.write(f"  初期予算   : ¥{INITIAL_BUDGET:,}\n")
        f.write(f"  現在の予算 : ¥{budget:,}\n")
        f.write(f"  累計損益   : ¥{total_profit:+,}\n")
        f.write(f"  取引日数   : {len(history)}日\n")
        if history:
            f.write(f"  最終取引日 : {history[-1]['date']}\n")
        f.write("=" * 50 + "\n")

    print(f"\n  📄 ログ保存: {log_path}")
    return log_path


def main():
    print(DISCLAIMER)
    print("  株式データを取得しています...")

    portfolio = load_portfolio()
    budget = portfolio["budget"]

    stock_data = fetch_all_stocks()
    if not stock_data:
        print("  データを取得できませんでした。")
        return

    recommendations = analyze_all(stock_data, budget)

    # 推薦結果を生成・表示・保存
    output = display_recommendations(recommendations, budget)
    print(output)
    show_summary(portfolio)
    save_log(output, portfolio)

    # 翌日予算入力（手動実行時のみ対話）
    if sys.stdin.isatty():
        print("\n  本日の取引結果を記録しますか？ (y/n): ", end="")
        try:
            answer = input().strip().lower()
            if answer == "y":
                print("  本日の損益を入力してください（例: 500 または -200）: ", end="")
                profit = int(input().strip())
                new_budget = budget + profit
                record_day(portfolio, str(date.today()), [], [], profit, new_budget)
                print(f"  記録しました。明日の予算: ¥{new_budget:,}")
        except (ValueError, EOFError):
            pass


if __name__ == "__main__":
    main()
