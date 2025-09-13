import pandas as pd
from indicators import pack_summary, ob_zones
from fibo import fib_levels, fib_extension

def smc_analysis(df: pd.DataFrame):
    summary = pack_summary(df)
    last = df.tail(150)
    high = float(last["high"].max())
    low = float(last["low"].min())
    retr = fib_levels(high, low)
    ext = fib_extension(high, low)
    zones = ob_zones(df)
    return {"summary": summary, "fibonacci": {"retracement": retr, "extension": ext}, "ob_zones": zones}
