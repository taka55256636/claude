import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from config import LOOKBACK_DAYS, STOCK_LIST


def fetch_stock_data(ticker: str) -> pd.DataFrame | None:
    """指定銘柄のOHLCVデータを取得する。"""
    try:
        end = datetime.today()
        start = end - timedelta(days=LOOKBACK_DAYS + 10)
        df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                         end=end.strftime("%Y-%m-%d"), progress=False,
                         auto_adjust=True)
        if df.empty or len(df) < 20:
            return None
        df.dropna(inplace=True)
        return df
    except Exception:
        return None


def fetch_all_stocks() -> dict[str, pd.DataFrame]:
    """全対象銘柄のデータを取得する。"""
    print(f"  {len(STOCK_LIST)}銘柄のデータを取得中...")
    result = {}
    for i, ticker in enumerate(STOCK_LIST, 1):
        data = fetch_stock_data(ticker)
        if data is not None:
            result[ticker] = data
        if i % 10 == 0:
            print(f"  {i}/{len(STOCK_LIST)} 完了...")
    print(f"  データ取得完了: {len(result)}銘柄")
    return result


def get_latest_price(df: pd.DataFrame) -> float:
    """最新の終値を返す。"""
    return float(df["Close"].iloc[-1])


def get_previous_close(df: pd.DataFrame) -> float:
    """前日の終値を返す。"""
    if len(df) >= 2:
        return float(df["Close"].iloc[-2])
    return float(df["Close"].iloc[-1])
