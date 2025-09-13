import pandas as pd
import numpy as np

def ema_series(s: pd.Series, period: int):
    return s.ewm(span=period, adjust=False).mean()

def ema(df: pd.DataFrame, period: int, col: str="close"):
    return ema_series(df[col], period)

def volume_ma(df: pd.DataFrame, period: int=21):
    return df["volume"].rolling(period).mean()

def pivots(df: pd.DataFrame, left: int=3, right: int=3):
    highs, lows = [], []
    for i in range(left, len(df)-right):
        window = df.iloc[i-left:i+right+1]
        if df["high"].iloc[i] == window["high"].max():
            highs.append((i, df["high"].iloc[i]))
        if df["low"].iloc[i] == window["low"].min():
            lows.append((i, df["low"].iloc[i]))
    return highs, lows

def support_resistance(df: pd.DataFrame, left: int=3, right: int=3, min_dist: float=0.002):
    highs, lows = pivots(df, left, right)
    levels = sorted({round(price, 6) for _, price in highs + lows})
    merged = []
    for lvl in levels:
        if not merged or abs(lvl - merged[-1])/lvl > min_dist:
            merged.append(lvl)
    close = df["close"].iloc[-1]
    supports = sorted([x for x in merged if x <= close], reverse=True)[:3]
    resistances = sorted([x for x in merged if x > close])[:3]
    return supports, resistances

def trendlines(df: pd.DataFrame):
    highs, lows = pivots(df, left=5, right=5)
    def line(p1, p2):
        (i1, y1), (i2, y2) = p1, p2
        m = (y2 - y1) / (i2 - i1)
        b = y1 - m * i1
        return m, b
    LTA, LTB = None, None
    if len(lows) >= 2:
        LTA = line(lows[-2], lows[-1])
    if len(highs) >= 2:
        LTB = line(highs[-2], highs[-1])
    def value_at(line_tuple, x):
        if line_tuple is None: return None
        m,b = line_tuple
        return m*x + b
    last_idx = len(df)-1
    return {
        "LTA": {"slope": None if LTA is None else LTA[0], "value_now": None if LTA is None else value_at(LTA, last_idx)},
        "LTB": {"slope": None if LTB is None else LTB[0], "value_now": None if LTB is None else value_at(LTB, last_idx)},
    }

def volume_profile_poc(df: pd.DataFrame, bins: int=50):
    prices = df["close"].values
    vols = df["volume"].values
    if len(prices) < 2:
        return float(prices[-1]) if len(prices) else np.nan
    hist, edges = np.histogram(prices, bins=bins, weights=vols)
    idx = int(hist.argmax())
    poc = (edges[idx] + edges[idx+1]) / 2
    return float(poc)

def cvd(df: pd.DataFrame):
    delta = np.where(df["close"].diff().fillna(0) >= 0, df["volume"], -df["volume"])
    return pd.Series(delta).cumsum().iloc[-1]

def fvg(df: pd.DataFrame, max_bars_back: int=200):
    for i in range(len(df)-3, len(df)-max_bars_back-1, -1):
        if i < 2: break
        h1 = df["high"].iloc[i-2]
        l3 = df["low"].iloc[i]
        if l3 > h1:
            return {"type":"bullish", "gap_top": l3, "gap_bottom": h1}
        l1 = df["low"].iloc[i-2]
        h3 = df["high"].iloc[i]
        if h3 < l1:
            return {"type":"bearish", "gap_top": l1, "gap_bottom": h3}
    return None

def ob_zones(df: pd.DataFrame, lookback: int=200):
    rng = df["high"] - df["low"]
    avg = rng.rolling(20).mean()
    zones = []
    for i in range(max(1, len(df)-lookback), len(df)-1):
        if avg.iloc[i-1] == 0 or pd.isna(avg.iloc[i-1]): 
            continue
        if rng.iloc[i] > 1.5*avg.iloc[i-1]:
            j = i-1
            if df["close"].iloc[j] < df["open"].iloc[j]:
                zones.append({"type":"demand","level_low": float(df['low'].iloc[j]), "level_high": float(df['high'].iloc[j])})
            else:
                zones.append({"type":"supply","level_low": float(df['low'].iloc[j]), "level_high": float(df['high'].iloc[j])})
    return zones[-2:] if zones else []

def bos_choch(df: pd.DataFrame, left: int=3, right: int=3):
    highs, lows = pivots(df, left, right)
    last_close = df["close"].iloc[-1]
    last_high = highs[-1][1] if highs else None
    last_low = lows[-1][1] if lows else None
    bos = None
    choch = None
    if last_high and last_close > last_high:
        bos = "Bullish BoS (higher high)"
    if last_low and last_close < last_low:
        choch = "Bearish ChoCH (lower low)"
    return bos, choch

# --------- RSI, MACD, StochRSI, KDJ, PSAR ---------
def rsi(series: pd.Series, period: int = 9) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    gain_ema = pd.Series(gain, index=series.index).ewm(alpha=1/period, adjust=False).mean()
    loss_ema = pd.Series(loss, index=series.index).ewm(alpha=1/period, adjust=False).mean()
    rs = gain_ema / (loss_ema.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def macd(series: pd.Series, fast: int = 6, slow: int = 13, signal: int = 4):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def stoch_rsi(series: pd.Series, rsi_len: int = 8, stoch_len: int = 5, k: int = 5, d: int = 3):
    r = rsi(series, rsi_len)
    min_r = r.rolling(stoch_len).min()
    max_r = r.rolling(stoch_len).max()
    stoch = (r - min_r) / (max_r - min_r)
    k_line = stoch.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return (stoch*100).fillna(50), (k_line*100).fillna(50), (d_line*100).fillna(50)

def kdj(df: pd.DataFrame, length: int = 5, k: int = 3, d: int = 3):
    ll = df["low"].rolling(length).min()
    hh = df["high"].rolling(length).max()
    rsv = (df["close"] - ll) / (hh - ll) * 100
    k_line = rsv.ewm(alpha=1/k, adjust=False).mean()
    d_line = k_line.ewm(alpha=1/d, adjust=False).mean()
    j_line = 3*k_line - 2*d_line
    return k_line.fillna(50), d_line.fillna(50), j_line.fillna(50)

def parabolic_sar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2):
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    length = len(df)
    if length < 2:
        return pd.Series(close, index=df.index)
    bull = True
    af = step
    ep = high[0]
    sar = low[0]
    out = [sar]
    for i in range(1, length):
        prev_sar = sar
        if bull:
            sar = prev_sar + af*(ep - prev_sar)
            sar = min(sar, low[i-1], low[i])
            if high[i] > ep:
                ep = high[i]
                af = min(af + step, max_step)
            if low[i] < sar:
                bull = False
                sar = ep
                ep = low[i]
                af = step
        else:
            sar = prev_sar + af*(ep - prev_sar)
            sar = max(sar, high[i-1], high[i])
            if low[i] < ep:
                ep = low[i]
                af = min(af + step, max_step)
            if high[i] > sar:
                bull = True
                sar = ep
                ep = high[i]
                af = step
        out.append(sar)
    return pd.Series(out, index=df.index)

# --------- ATR, SuperTrend, VWAP ---------
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    hl = (h - l).abs()
    hc = (h - c.shift()).abs()
    lc = (l - c.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    # Based on ATR bands
    atr_val = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2.0
    upper = hl2 + multiplier * atr_val
    lower = hl2 - multiplier * atr_val

    st = pd.Series(index=df.index, dtype=float)
    dir_up = True
    prev_upper = upper.iloc[0]
    prev_lower = lower.iloc[0]
    st.iloc[0] = lower.iloc[0]

    for i in range(1, len(df)):
        cur_upper = min(upper.iloc[i], prev_upper) if df["close"].iloc[i-1] > prev_upper else upper.iloc[i]
        cur_lower = max(lower.iloc[i], prev_lower) if df["close"].iloc[i-1] < prev_lower else lower.iloc[i]

        if st.iloc[i-1] == prev_upper:
            st.iloc[i] = cur_upper if df["close"].iloc[i] <= cur_upper else cur_lower
        else:
            st.iloc[i] = cur_lower if df["close"].iloc[i] >= cur_lower else cur_upper

        prev_upper, prev_lower = cur_upper, cur_lower

    trend_dir = np.where(df["close"] >= st, "UP", "DOWN")
    return st, trend_dir, atr_val

def vwap(df: pd.DataFrame):
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["volume"].cumsum()
    cum_pv = (tp * df["volume"]).cumsum()
    return (cum_pv / cum_vol).fillna(method="ffill")

def pack_summary(df: pd.DataFrame) -> dict:
    ema9 = ema(df, 9)
    ema21 = ema(df, 21)
    ema80 = ema(df, 80)
    ema200 = ema(df, 200)
    vol21 = volume_ma(df, 21)
    supports, resistances = support_resistance(df)
    tl = trendlines(df)
    poc = volume_profile_poc(df)
    cvd_val = cvd(df)
    fvg_last = fvg(df)
    bos, choch = bos_choch(df)

    rsi9 = rsi(df["close"], 9).iloc[-1]
    macd_line, signal_line, macd_hist = macd(df["close"], 6, 13, 4)
    macd_vals = (macd_line.iloc[-1], signal_line.iloc[-1], macd_hist.iloc[-1])
    stoch_raw, stoch_k, stoch_d = stoch_rsi(df["close"], 8, 5, 5, 3)
    kdj_k, kdj_d, kdj_j = kdj(df, 5, 3, 3)
    psar = parabolic_sar(df).iloc[-1]

    atr14 = atr(df, 14).iloc[-1]
    st_line, st_dir, atr_val = supertrend(df, 10, 3.0)
    st_last = float(st_line.iloc[-1]); st_dir_last = str(st_dir[-1])
    vwap_last = float(vwap(df).iloc[-1])

    return {
        "ema": {"9": float(ema9.iloc[-1]), "21": float(ema21.iloc[-1]), "80": float(ema80.iloc[-1]), "200": float(ema200.iloc[-1])},
        "volume_vs_ma21": {"last": float(df["volume"].iloc[-1]), "ma21": float(vol21.iloc[-1]) if not pd.isna(vol21.iloc[-1]) else None},
        "supports": supports, "resistances": resistances,
        "trendlines": tl, "poc": float(poc), "cvd": float(cvd_val),
        "fvg": fvg_last,
        "bos": bos, "choch": choch,
        "extras": {
            "rsi9": float(rsi9),
            "macd_6_13_4": {"macd": float(macd_vals[0]), "signal": float(macd_vals[1]), "hist": float(macd_vals[2])},
            "stoch_rsi_8_5_5_3": {"raw": float(stoch_raw.iloc[-1]), "k": float(stoch_k.iloc[-1]), "d": float(stoch_d.iloc[-1])},
            "kdj_5_3_3": {"k": float(kdj_k.iloc[-1]), "d": float(kdj_d.iloc[-1]), "j": float(kdj_j.iloc[-1])},
            "psar": float(psar),
            "atr14": float(atr14),
            "supertrend_10_3": {"line": st_last, "dir": st_dir_last},
            "vwap": float(vwap_last)
        }
    }
