#!/usr/bin/env python3
"""
日本株デイトレード推薦システム
- 前日データをもとに当日の買い推薦銘柄を出力する
- 予算は雪だるま式に増加（利益を次日の予算に加算）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date
from data_collector import fetch_all_stocks
from analyzer import analyze_all
from portfolio import load_portfolio, save_portfolio, show_summary
from config import TOP_N_STOCKS, MAX_BUDGET_RATIO

DISCLAIMER = """
⚠️  免責事項: このシステムはあくまで参考情報です。
   株式投資には損失リスクがあります。最終的な投資判断はご自身でお願いします。
"""


def display_recommendations(recommendations: list, budget: int):
    """推薦銘柄を表示する。"""
    print("\n" + "=" * 70)
    print(f"  【本日の買い推薦銘柄】  予算: ¥{budget:,}")
    print(f"  分析日: {date.today()}")
    print("=" * 70)

    if not recommendations:
        print("  本日の推薦銘柄はありません。")
        return

    print(f"  {'順位':^4} {'銘柄コード':^12} {'株価':^10} {'スコア':^8} "
          f"{'RSI':^6} {'前日比':^8} {'最大購入株数':^12} {'投資額':^10}")
    print("-" * 70)

    for i, rec in enumerate(recommendations[:TOP_N_STOCKS], 1):
        ticker_short = rec["ticker"].replace(".T", "")
        print(f"  {i:^4} {ticker_short:^12} "
              f"¥{rec['price']:>8,.0f} "
              f"{rec['score']:>7.1f} "
              f"{rec['rsi']:>5.1f} "
              f"{rec['change_pct']:>+7.1f}% "
              f"{rec['max_shares']:>10}株 "
              f"¥{rec['max_investment']:>8,}")

    print("\n  【詳細分析】")
    print("-" * 70)
    for i, rec in enumerate(recommendations[:5], 1):
        ticker_short = rec["ticker"].replace(".T", "")
        print(f"\n  #{i} {ticker_short}")
        print(f"     株価: ¥{rec['price']:,.0f} | "
              f"スコア: {rec['score']:.1f} | "
              f"RSI: {rec['rsi']:.1f} | "
              f"出来高比: {rec['vol_ratio']:.1f}倍")
        print(f"     推薦理由: {', '.join(rec['reasons'])}")
        max_invest = int(rec['price'] * rec['max_shares'])
        print(f"     推薦購入: {rec['max_shares']}株 (投資額 ¥{max_invest:,})")

    print("\n  【本日の戦略】")
    print("  ✅ 朝9:00-9:30に上記銘柄を確認し、値動きが安定したら購入")
    print("  ✅ 15:00-15:30の引け前に売却（1日完結のデイトレード）")
    print("  ✅ 損切りライン: -3%で損切りを推薦")


def main():
    print(DISCLAIMER)
    print("  株式データを取得しています...")

    # ポートフォリオ読み込み
    portfolio = load_portfolio()
    budget = portfolio["budget"]

    # データ取得・分析
    stock_data = fetch_all_stocks()
    if not stock_data:
        print("  データを取得できませんでした。")
        return

    recommendations = analyze_all(stock_data, budget)

    # 結果表示
    display_recommendations(recommendations, budget)
    show_summary(portfolio)

    # 翌日予算入力（オプション）
    print("\n  本日の取引結果を記録しますか？ (y/n): ", end="")
    try:
        answer = input().strip().lower()
        if answer == "y":
            print("  本日の損益を入力してください（マイナスも可）例: 500 または -200: ", end="")
            profit = int(input().strip())
            new_budget = budget + profit
            from portfolio import record_day
            record_day(portfolio, str(date.today()), [], [], profit, new_budget)
            print(f"  記録しました。明日の予算: ¥{new_budget:,}")
    except (ValueError, EOFError):
        pass


if __name__ == "__main__":
    main()
