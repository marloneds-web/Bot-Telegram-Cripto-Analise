import asyncio, json, websockets
from typing import List, Dict

WS_URL = "wss://stream.bybit.com/v5/public/linear"

async def recent_liquidations(symbol: str, max_events: int = 10, timeout: float = 3.0) -> List[Dict]:
    sym = symbol.replace("/", "")
    out = []
    async with websockets.connect(WS_URL, ping_interval=20, ping_timeout=20) as ws:
        sub = {"op":"subscribe","args":[f"liquidation.{sym}"]}
        await ws.send(json.dumps(sub))
        try:
            while len(out) < max_events:
                msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                data = json.loads(msg)
                if data.get("topic", "").startswith("liquidation."):
                    rows = data.get("data", [])
                    for r in rows:
                        out.append({
                            "side": r.get("side"), "price": float(r.get("price", 0)),
                            "qty": float(r.get("qty", 0)), "time": int(r.get("updatedTime", 0))
                        })
                        if len(out) >= max_events:
                            break
        except asyncio.TimeoutError:
            pass
    return out
