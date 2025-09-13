from datetime import datetime, time
import pytz

EXCHANGES = {
    "Nova York (NYSE)": ("13:30", "20:00", "America/New_York"),
    "Londres (LSE)": ("08:00", "16:30", "Europe/London"),
    "Tóquio (TSE)": ("00:00", "06:00", "Asia/Tokyo"),
    "Hong Kong (HKEX)": ("01:30", "08:00", "Asia/Hong_Kong"),
    "Brasil (B3)": ("13:00", "20:00", "America/Sao_Paulo"),
}

def parse_hhmm(s: str):
    h, m = map(int, s.split(":"))
    return time(h, m)

def market_states(now_tz: str = "America/Campo_Grande"):
    user_tz = pytz.timezone(now_tz)
    now_local = datetime.now(user_tz)
    results = []
    for name, (open_h, close_h), tz_name in EXCHANGES.items():
        tz = pytz.timezone(tz_name)
        now_mkt = now_local.astimezone(tz)
        op = parse_hhmm(open_h)
        cl = parse_hhmm(close_h)
        is_open = (now_mkt.time() >= op) and (now_mkt.time() <= cl)
        status = "ABERTO" if is_open else "FECHADO"
        results.append({"name": name, "open": open_h, "close": close_h, "status": status, "tz": tz_name})
    return results
