import pandas as pd
import numpy as np
from config import (RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
                    MA_SHORT, MA_LONG, RSI_OVERSOLD)


def calc_rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    """RSIを計算して最新値を返す。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def calc_macd(close: pd.Series):
    """MACDとシグナルラインを計算して最新値を返す。"""
    ema_fast = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    histogram = macd_line - signal_line
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def calc_moving_averages(close: pd.Series):
    """短期・長期移動平均を返す。"""
    ma_short = float(close.rolling(MA_SHORT).mean().iloc[-1])
    ma_long = float(close.rolling(MA_LONG).mean().iloc[-1])
    return ma_short, ma_long


def calc_volume_ratio(volume: pd.Series) -> float:
    """直近出来高 / 20日平均出来高 の比率を返す（1以上が高出来高）。"""
    avg = float(volume.rolling(20).mean().iloc[-1])
    latest = float(volume.iloc[-1])
    if avg == 0:
        return 1.0
    return latest / avg


def score_stock(df: pd.DataFrame) -> dict:
    """銘柄をスコアリングする。スコアが高いほど買い推薦。"""
    close = df["Close"].squeeze()
    volume = df["Volume"].squeeze()

    rsi = calc_rsi(close)
    macd, signal, histogram = calc_macd(close)
    ma_short, ma_long = calc_moving_averages(close)
    vol_ratio = calc_volume_ratio(volume)
    price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) >= 2 else price
    change_pct = (price - prev_close) / prev_close * 100

    score = 0.0
    reasons = []

    # RSIスコア（30-50の範囲が最高：売られすぎから反発狙い）
    if rsi < 30:
        score += 15
        reasons.append(f"RSI売られすぎ({rsi:.1f})")
    elif rsi < RSI_OVERSOLD:
        score += 25
        reasons.append(f"RSI反発圏({rsi:.1f})")
    elif rsi < 55:
        score += 10
        reasons.append(f"RSI中立({rsi:.1f})")
    elif rsi > 70:
        score -= 15
        reasons.append(f"RSI買われすぎ({rsi:.1f})")

    # MACDスコア（ヒストグラムがプラス転換）
    if histogram > 0 and macd > signal:
        score += 25
        reasons.append("MACDゴールデンクロス")
    elif histogram > 0:
        score += 10
        reasons.append("MACDプラス")
    elif histogram < 0 and macd < signal:
        score -= 20
        reasons.append("MACDデッドクロス")

    # 移動平均スコア（短期>長期でトレンドアップ）
    if ma_short > ma_long:
        score += 20
        reasons.append("上昇トレンド中")
    else:
        score -= 10
        reasons.append("下降トレンド中")

    # 出来高スコア（高出来高は注目度高）
    if vol_ratio >= 1.5:
        score += 15
        reasons.append(f"高出来高({vol_ratio:.1f}倍)")
    elif vol_ratio >= 1.0:
        score += 5

    # 前日比スコア（小幅上昇が理想）
    if 0 < change_pct <= 2.0:
        score += 10
        reasons.append(f"前日比+{change_pct:.1f}%")
    elif change_pct > 3.0:
        score -= 5  # 大幅上昇は高値掴みリスク
    elif -1.5 <= change_pct < 0:
        score += 5  # 小幅下落からの反発狙い

    return {
        "price": price,
        "rsi": rsi,
        "macd": macd,
        "signal": signal,
        "histogram": histogram,
        "ma_short": ma_short,
        "ma_long": ma_long,
        "vol_ratio": vol_ratio,
        "change_pct": change_pct,
        "score": score,
        "reasons": reasons,
    }


def analyze_all(stock_data: dict, budget: int) -> list[dict]:
    """全銘柄を分析して、予算内で買える銘柄をスコア順に返す。"""
    results = []
    for ticker, df in stock_data.items():
        try:
            info = score_stock(df)
            price = info["price"]
            # 予算内で最低1株買えるか確認
            if price > budget:
                continue
            max_shares = int(budget / price)
            info["ticker"] = ticker
            info["max_shares"] = max_shares
            info["max_investment"] = int(price * max_shares)
            results.append(info)
        except Exception:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results
