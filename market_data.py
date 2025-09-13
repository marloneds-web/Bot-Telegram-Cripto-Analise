import asyncio
import httpx
import pandas as pd
import numpy as np

BASES = {
    "bybit": {
        "kline": "https://api.bybit.com/v5/market/kline",
        "symbol_transform": lambda s: s.replace("/", "")
    },
    "kraken": {
        "kline": "https://api.kraken.com/0/public/OHLC",
        "symbol_transform": lambda s: s.replace("/", "").replace("USDT","USD").lower()
    },
    "mexc": {
        "kline": "https://api.mexc.com/api/v3/klines",
        "symbol_transform": lambda s: s.replace("/", "")
    },
    "bitmex": {
        "kline": "https://www.bitmex.com/api/v1/trade/bucketed",
        "symbol_transform": lambda s: s.replace("/", "")
    },
}

INTERVAL_MAP = {
    "1m":"1", "3m":"3", "5m":"5", "15m":"15", "30m":"30",
    "1h":"60", "2h":"120", "4h":"240", "6h":"360", "12h":"720",
    "1d":"D", "1w":"W"
}

def norm_df(ts, opens, highs, lows, closes, vols):
    df = pd.DataFrame({
        "time": pd.to_datetime(ts, unit="ms", utc=True),
        "open": pd.to_numeric(opens),
        "high": pd.to_numeric(highs),
        "low": pd.to_numeric(lows),
        "close": pd.to_numeric(closes),
        "volume": pd.to_numeric(vols),
    })
    df.sort_values("time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

async def fetch_bybit(symbol: str, interval: str, limit: int = 500):
    sym = BASES["bybit"]["symbol_transform"](symbol)
    iv = INTERVAL_MAP.get(interval, "240")
    params = {"category": "linear", "symbol": sym, "interval": iv, "limit": limit}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASES["bybit"]["kline"], params=params)
        r.raise_for_status()
        data = r.json().get("result", {}).get("list", [])
        if not data:
            raise RuntimeError("Bybit empty")
        data = list(reversed(data))
        ts, opens, highs, lows, closes, vols = [], [], [], [], [], []
        for row in data:
            ts.append(int(row[0]))
            opens.append(float(row[1]))
            highs.append(float(row[2]))
            lows.append(float(row[3]))
            closes.append(float(row[4]))
            vols.append(float(row[5]))
        return norm_df(ts, opens, highs, lows, closes, vols)

async def fetch_kraken(symbol: str, interval: str, limit: int = 500):
    pair = BASES["kraken"]["symbol_transform"](symbol)
    iv = {"1m":1, "5m":5, "15m":15, "1h":60, "4h":240, "1d":1440}.get(interval, 240)
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASES["kraken"]["kline"], params={"pair": pair, "interval": iv})
        r.raise_for_status()
        res = r.json()["result"]
        key = [k for k in res.keys() if k != "last"][0]
        rows = res[key][-limit:]
        ts, opens, highs, lows, closes, vols = zip(*[(int(x[0])*1000,float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[6])) for x in rows])
        return norm_df(ts, opens, highs, lows, closes, vols)

async def fetch_mexc(symbol: str, interval: str, limit: int = 500):
    pair = BASES["mexc"]["symbol_transform"](symbol)
    iv = {"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1d":"1d"}.get(interval, "4h")
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASES["mexc"]["kline"], params={"symbol": pair, "interval": iv, "limit": limit})
        r.raise_for_status()
        rows = r.json()
        ts, opens, highs, lows, closes, vols = zip(*[(int(x[0]),float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5])) for x in rows])
        return norm_df(ts, opens, highs, lows, closes, vols)

async def fetch_bitmex(symbol: str, interval: str, limit: int = 500):
    pair = symbol.replace("/", "")
    if pair.startswith("BTC"): pair = pair.replace("BTC", "XBT", 1)
    bin_iv = {"1m":"1m", "5m":"5m", "1h":"1h", "4h":"4h", "1d":"1d"}.get(interval, "4h")
    params = {"symbol": pair, "binSize": bin_iv, "count": limit, "reverse": "false"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(BASES["bitmex"]["kline"], params=params)
        r.raise_for_status()
        rows = r.json()
        ts, opens, highs, lows, closes, vols = [],[],[],[],[],[]
        import pandas as pd
        for x in rows:
            ts.append(int(pd.Timestamp(x["timestamp"]).value//10**6))
            opens.append(float(x["open"]))
            highs.append(float(x["high"]))
            lows.append(float(x["low"]))
            closes.append(float(x["close"]))
            vols.append(float(x["volume"]))
        return norm_df(ts, opens, highs, lows, closes, vols)

async def get_ohlcv(symbol: str, interval: str, limit: int = 500):
    funcs = [fetch_bybit, fetch_kraken, fetch_mexc, fetch_bitmex]
    for fn in funcs:
        try:
            df = await fn(symbol, interval, limit)
            return df, fn.__name__.replace("fetch_", "")
        except Exception:
            continue
    raise RuntimeError("Nenhuma fonte de dados retornou candles.")
