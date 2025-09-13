import asyncio
from fastapi import FastAPI, Request, Response, HTTPException
from telegram import Update
from telegram.ext import Application
from config import TELEGRAM_BOT_TOKEN, WEBHOOK_URL, WEBHOOK_SECRET
from bot import register_handlers, analyze_command

app = FastAPI(title="Telegram SMC Bot")

application = Application.builder().token(TELEGRAM_BOT_TOKEN).concurrent_updates(True).build()
register_handlers(application)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(application.initialize())
    await application.start()
    if WEBHOOK_URL:
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{WEBHOOK_SECRET}")

@app.on_event("shutdown")
async def on_shutdown():
    await application.stop()
    await application.shutdown()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request):
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="invalid secret")
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return Response(status_code=200)

@app.get("/analisar")
async def analisar(symbol: str="BTCUSDT", tf: str="1h"):
    text = await analyze_command(symbol, tf)
    return {"result": text}
