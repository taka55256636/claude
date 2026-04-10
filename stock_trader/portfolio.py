import json
import os
from datetime import date
from config import PORTFOLIO_FILE, INITIAL_BUDGET


def load_portfolio() -> dict:
    """ポートフォリオを読み込む。存在しない場合は初期化する。"""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "budget": INITIAL_BUDGET,
        "history": [],
        "created_at": str(date.today()),
    }


def save_portfolio(portfolio: dict):
    """ポートフォリオを保存する。"""
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)


def record_day(portfolio: dict, date_str: str, bought: list, sold: list,
               profit: int, new_budget: int):
    """1日の取引結果を記録し、予算を更新する（雪だるま式）。"""
    portfolio["history"].append({
        "date": date_str,
        "bought": bought,
        "sold": sold,
        "profit": profit,
        "budget_after": new_budget,
    })
    portfolio["budget"] = new_budget
    save_portfolio(portfolio)


def show_summary(portfolio: dict):
    """ポートフォリオのサマリーを表示する。"""
    budget = portfolio["budget"]
    history = portfolio["history"]
    total_profit = budget - INITIAL_BUDGET

    print("\n" + "=" * 50)
    print("  【ポートフォリオサマリー】")
    print("=" * 50)
    print(f"  初期予算   : ¥{INITIAL_BUDGET:,}")
    print(f"  現在の予算 : ¥{budget:,}")
    print(f"  累計損益   : ¥{total_profit:+,}")
    print(f"  取引日数   : {len(history)}日")
    if history:
        print(f"  最終取引日 : {history[-1]['date']}")
    print("=" * 50)
