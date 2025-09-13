from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from market_data import get_ohlcv
from smc import smc_analysis
from liquidation import recent_liquidations
from markets_clock import market_states

def fmt_num(x, digits=6):
    try:
        return f"{x:.{digits}f}"
    except Exception:
        return str(x)

DEFAULT_SHOW = {
    "rsi": True, "macd": True, "stochrsi": True, "kdj": True, "psar": True,
    "atr": True, "supertrend": True, "vwap": True
}

def parse_toggles(extra_args):
    show = DEFAULT_SHOW.copy()
    for tok in extra_args:
        t = tok.strip()
        if t.startswith("on="):
            keys = [k.strip().lower() for k in t[3:].split(",")]
            for k in keys:
                if k in ("rsi","macd","stochrsi","kdj","psar","atr","supertrend","vwap"):
                    show[k] = True
        elif t.startswith("off="):
            keys = [k.strip().lower() for k in t[4:].split(",")]
            for k in keys:
                if k in show:
                    show[k] = False
    return show

def build_message(symbol: str, tf: str, source: str, res: dict, liq: list, tz_user: str="America/Campo_Grande", show=None):
    show = show or DEFAULT_SHOW
    s = res["summary"]
    ema = s["ema"]; vol = s["volume_vs_ma21"]
    tlines = s["trendlines"]
    fvg = s["fvg"]
    bos, choch = s["bos"], s["choch"]
    extras = s.get("extras", {})

    supports = ", ".join([f"**{fmt_num(x,6)}**" for x in s["supports"]]) if s["supports"] else "-"
    resistances = ", ".join([f"**{fmt_num(x,6)}**" for x in s["resistances"]]) if s["resistances"] else "-"
    ob_txt = []
    for z in res["ob_zones"]:
        ob_txt.append(f"{'DEMANDA' if z['type']=='demand' else 'OFERTA'} [{fmt_num(z['level_low'])} - {fmt_num(z['level_high'])}]")
    ob_str = ", ".join(ob_txt) if ob_txt else "-"

    fib_r = res["fibonacci"]["retracement"]; fib_e = res["fibonacci"]["extension"]

    markets = market_states(tz_user)
    markets_str = "; ".join([f"{m['name']}: {m['status']} ({m['open']}–{m['close']})" for m in markets])

    liq_str = ", ".join([f"{x['side']} @ {fmt_num(x['price'])} ({fmt_num(x['qty'],2)})" for x in liq]) if liq else "Sem eventos recentes"

    bias = "Alta" if ema["9"] > ema["21"] > ema["80"] else "Baixa" if ema["9"] < ema["21"] < ema["80"] else "Neutro"
    if bias == "Alta" and s["resistances"]:
        entry = s["supports"][0] if s["supports"] else s["poc"]
        tps = s["resistances"][:3]
        sl = s["supports"][1] if len(s["supports"])>1 else s["supports"][0]*0.99 if s["supports"] else s["poc"]*0.98
    elif bias == "Baixa" and s["supports"]:
        entry = s["resistances"][0] if s["resistances"] else s["poc"]
        tps = s["supports"][:3]
        sl = s["resistances"][1] if len(s["resistances"])>1 else s["resistances"][0]*1.01 if s["resistances"] else s["poc"]*1.02
    else:
        entry = s["poc"]
        tps = (s["resistances"][:2] + s["supports"][:1]) if s["resistances"] or s["supports"] else []
        sl = s["poc"]*0.98

    fvg_str = "-" if not fvg else f"{fvg['type']} [{fmt_num(fvg['gap_bottom'])}–{fmt_num(fvg['gap_top'])}]"

    rsi9 = extras.get("rsi9")
    macd = extras.get("macd_6_13_4", {})
    stoch = extras.get("stoch_rsi_8_5_5_3", {})
    kdj = extras.get("kdj_5_3_3", {})
    psar = extras.get("psar")
    atr14 = extras.get("atr14")
    st = extras.get("supertrend_10_3", {})
    vwap_val = extras.get("vwap")

    msg = []
    msg.append(f"🚀 *Análise SMC* — *{symbol}* [{tf}] · fonte: _{source}_")
    msg.append("")
    msg.append(f"*EMAs:* 9={fmt_num(ema['9'])} · 21={fmt_num(ema['21'])} · 80={fmt_num(ema['80'])} · 200={fmt_num(ema['200'])}")
    msg.append(f"*Volume vs MA21:* vol={fmt_num(vol['last'],2)} · ma21={fmt_num(vol['ma21'],2) if vol['ma21'] else '-'}")
    msg.append(f"*Suportes:* {supports}")
    msg.append(f"*Resistências:* {resistances}")
    msg.append(f"*LTA:* {fmt_num(tlines['LTA']['value_now']) if tlines['LTA']['value_now'] else '-'} · *LTB:* {fmt_num(tlines['LTB']['value_now']) if tlines['LTB']['value_now'] else '-'}")
    msg.append(f"*POC:* {fmt_num(s['poc'])} · *CVD:* {fmt_num(s['cvd'],2)}")
    msg.append(f"*FVG:* {fvg_str}")
    msg.append(f"*BoS:* {bos or '-'} · *ChoCH:* {choch or '-'}")
    msg.append(f"*OB:* {ob_str}")
    msg.append("")

    if show.get("rsi"):       msg.append(f"*RSI(9):* {fmt_num(rsi9,2) if rsi9 is not None else '-'}")
    if show.get("macd"):      msg.append(f"*MACD(6,13,4):* macd={fmt_num(macd.get('macd',0),4)} · signal={fmt_num(macd.get('signal',0),4)} · hist={fmt_num(macd.get('hist',0),4)}")
    if show.get("stochrsi"):  msg.append(f"*StochRSI(8,5,5,3):* raw={fmt_num(stoch.get('raw',0),2)} · %K={fmt_num(stoch.get('k',0),2)} · %D={fmt_num(stoch.get('d',0),2)}")
    if show.get("kdj"):       msg.append(f"*KDJ(5,3,3):* K={fmt_num(kdj.get('k',0),2)} · D={fmt_num(kdj.get('d',0),2)} · J={fmt_num(kdj.get('j',0),2)}")
    if show.get("psar"):      msg.append(f"*Parabolic SAR:* {fmt_num(psar)}")
    if show.get("atr"):       msg.append(f"*ATR(14):* {fmt_num(atr14,4) if atr14 is not None else '-'}")
    if show.get("supertrend"):msg.append(f"*SuperTrend(10,3):* linha={fmt_num(st.get('line',0))} · dir={st.get('dir','-')}")
    if show.get("vwap"):      msg.append(f"*VWAP:* {fmt_num(vwap_val)}")

    msg.append("")
    msg.append(f"*Fibonacci (Retrac.):* 0.236={fmt_num(fib_r['0.236'])} · 0.382={fmt_num(fib_r['0.382'])} · 0.5={fmt_num(fib_r['0.5'])} · 0.618={fmt_num(fib_r['0.618'])} · 0.786={fmt_num(fib_r['0.786'])}")
    msg.append(f"*Fibonacci (Expansão):* 1.272={fmt_num(fib_e['1.272'])} · 1.414={fmt_num(fib_e['1.414'])} · 1.618={fmt_num(fib_e['1.618'])} · 2.0={fmt_num(fib_e['2.0'])}")
    msg.append("")
    msg.append(f"🕒 *Mercados Globais:* {markets_str}")
    msg.append(f"💥 *Liquidações Bybit (recentes):* {liq_str}")
    msg.append("")
    direction = "LONG" if bias in ("Alta","Neutro") else "SHORT"
    msg.append("🎯 *Sinal sugerido* (didático, não é recomendação):")
    msg.append(f"*Direção:* {direction}")
    msg.append(f"*Entrada:* {fmt_num(entry)}")
    if tps:
        msg.append("*TPs:* " + " · ".join([fmt_num(x) for x in tps]))
    msg.append(f"*SL:* {fmt_num(sl)}")
    msg.append("")
    msg.append("_Este material é para fins educacionais; não constitui recomendação de investimento._")
    return "\n".join(msg)

async def analyze_command(symbol: str, tf: str, tz_user: str = "America/Campo_Grande", show=None):
    df, source = await get_ohlcv(symbol, tf, limit=500)
    res = smc_analysis(df)
    res["close"] = float(df["close"].iloc[-1])
    try:
        liq = await recent_liquidations(symbol, max_events=6, timeout=2.0)
    except Exception:
        liq = []
    text = build_message(symbol, tf, source, res, liq, tz_user, show=show)
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Envie /analisa BTCUSDT 1h [on=...] [off=...]\n"
        "Ex.: /analisa BTCUSDT 1h on=atr,supertrend off=kdj,psar\n"
        "Indicadores: rsi, macd, stochrsi, kdj, psar, atr, supertrend, vwap"
    )

async def analisa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            return await update.message.reply_text("Uso: /analisa <PAR> <TIMEFRAME> [on=...] [off=...]")
        symbol = args[0].upper()
        tf = args[1].lower()
        show = parse_toggles(args[2:]) if len(args) > 2 else None
        text = await analyze_command(symbol, tf, show=show)
        await update.message.reply_markdown(text, disable_web_page_preview=True)
    except Exception as e:
        await update.message.reply_text(f"Erro na análise: {e}")

def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analisa", analisa))
