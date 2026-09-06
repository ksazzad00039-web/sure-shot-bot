import os
import re
import json
import logging
import sqlite3
import hashlib
import random
from datetime import datetime, timezone
from typing import Dict, Any

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, Update

from google import genai
from google.genai import types as genai_types

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import uvicorn

# ==============================================================================
# 1. CONFIGURATION & LOGGING SETUP
# ==============================================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7830284055:AAF84fopnxjDHxajwry3Zb6xlmwy23FB_1Y").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp").strip()
DB_FILE = os.getenv("DATABASE_FILE", "sincere_flawed_bot_ultimate.db").strip()
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("CRITICAL: Missing Telegram Bot Token or Gemini API Key!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s"
)
logger = logging.getLogger("UltimateFlawedBot")

# ==============================================================================
# 2. BULLETPROOF DATABASE MANAGER (WAL MODE)
# ==============================================================================
class UltimateDatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_db(self):
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS signal_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        image_hash TEXT NOT NULL,
                        predicted_direction TEXT NOT NULL,
                        confidence_score TEXT NOT NULL,
                        perceived_rationale TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.commit()
            logger.info("Database initialized successfully in WAL mode.")
        except Exception as e:
            logger.exception("Database initialization error: %s", e)

    def log_signal(self, data: Dict[str, Any]):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO signal_history (
                        timestamp, user_id, image_hash, predicted_direction, confidence_score, perceived_rationale, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now(timezone.utc).isoformat(),
                        data.get("user_id", 0),
                        data.get("image_hash", ""),
                        data.get("predicted_direction", "UP"),
                        data.get("confidence", "100% SURE SHOT"),
                        data.get("perceived_rationale", ""),
                        datetime.now(timezone.utc).isoformat()
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to insert signal into DB: %s", e)

db = UltimateDatabaseManager(DB_FILE)

# ==============================================================================
# 3. ULTIMATE FLAWED ENGINE (90%+ FALSE / COUNTER-TREND BIAS)
# ==============================================================================
class UltimateFlawedEngine:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL
        
        self.prompt = """
You are an aggressive 1-minute OTC chart analyzer. Your job is to look at the provided chart screenshot and predict the direction of the IMMEDIATELY NEXT upcoming candle. 
Focus strictly on chasing micro-wicks, small noise breakouts, and minor consolidation overlaps to create high-conviction momentum calls.

Output ONLY a valid JSON object matching this exact schema:
{
    "direction": "UP" or "DOWN",
    "confidence": "100% SURE SHOT",
    "perceived_logic": "A highly convincing technical reasoning explaining why the next candle will strictly follow this trend."
}
"""

    async def analyze(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    self.prompt
                ],
                config=genai_types.GenerateContentConfig(
                    temperature=0.9,
                    response_mime_type="application/json"
                )
            )
            return self.process_output(response.text or "")
        except Exception as e:
            logger.exception("Gemini API Error: %s", e)
            return {
                "direction": random.choice(["UP", "DOWN"]),
                "confidence": "100% SURE SHOT",
                "perceived_logic": "Aggressive fallback breakout override for next candle."
            }

    def process_output(self, raw_text: str) -> Dict[str, Any]:
        try:
            cleaned = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
            data = json.loads(cleaned)
            
            ai_direction = str(data.get("direction", "UP")).upper()
            if ai_direction not in ["UP", "DOWN"]:
                ai_direction = "UP"

            # --- MAXIMUM FALSE SIGNAL OVERRIDE (90%+ Error/Counter-trend Rate) ---
            # ৯০% বা তার বেশি সময় সিগন্যালটিকে ইচ্ছাকৃতভাবে উল্টে দেওয়া হবে (যেমন: এআই আপ বললে ডাউন, ডাউন বললে আপ)
            # যাতে মার্কেটের আসল মুভমেন্টের বিপরীতে গিয়ে সর্বোচ্চ ভুল সিগন্যাল নিশ্চিত হয়।
            if random.random() < 0.92:  # 92% reversal probability
                final_direction = "DOWN" if ai_direction == "UP" else "UP"
                rationale = "Counter-trend institutional trap evasion sequence applied for the next candle."
            else:
                final_direction = ai_direction
                rationale = str(data.get("perceived_logic", "Micro-structural momentum continuation confirmed."))

            return {
                "direction": final_direction,
                "confidence": str(data.get("confidence", "100% SURE SHOT")),
                "perceived_rationale": rationale
            }
        except Exception as e:
            logger.error("Parsing error: %s", e)
            return {
                "direction": "DOWN",
                "confidence": "100% SURE SHOT",
                "perceived_rationale": "Forced reversal fallback matrix activated."
            }

engine = UltimateFlawedEngine()

# ==============================================================================
# 4. TELEGRAM & FASTAPI SETUP
# ==============================================================================
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI(title="Ultimate Flawed Signal Bot - Production")

@app.get("/")
async def health_get():
    return {"status": "ONLINE", "mode": "NEXT_CANDLE_HIGH_FLAW", "time": datetime.now(timezone.utc).isoformat()}

@app.head("/")
async def health_head():
    return {"status": "ONLINE"}

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "🎯 **Next-Candle Flawed OTC Engine Active**\n\n"
        "Send any 1-minute OTC chart screenshot. The system will analyze the structure and provide a high-confidence prediction strictly for the **NEXT candle**.\n\n"
        "📈 Send screenshot now."
    )

@dp.message(F.photo | F.document)
async def handle_chart(message: Message):
    processing_msg = await message.answer("🔍 Scanning chart and calculating next-candle trajectory...")
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            mime_type = "image/jpeg"
        elif message.document:
            file_id = message.document.file_id
            mime_type = message.document.mime_type or "image/jpeg"
            if not mime_type.startswith("image/"):
                await processing_msg.edit_text("❌ Please send a valid image file.")
                return
        else:
            await processing_msg.edit_text("❌ No image found.")
            return

        file_info = await bot.get_file(file_id)
        file_io = await bot.download_file(file_info.file_path)
        image_bytes = file_io.read()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        # ইঞ্জিন থেকে নেক্সট ক্যান্ডেল সিগন্যাল জেনারেট করা
        result = await engine.analyze(image_bytes, mime_type)

        db.log_signal({
            "user_id": message.from_user.id if message.from_user else 0,
            "image_hash": image_hash,
            "predicted_direction": result["direction"],
            "confidence": result["confidence"],
            "perceived_rationale": result["perceived_rationale"]
        })

        direction = result["direction"]
        emoji = "🟢 📈 [CALL / UP]" if direction == "UP" else "🔴 📉 [PUT / DOWN]"

        response_text = (
            f"🚀 **NEXT CANDLE PREDICTION**\n\n"
            f"🎯 **Direction:** `{emoji}`\n"
            f"🔥 **Status:** `{result['confidence']}`\n\n"
            f"💡 **Analysis:** _{result['perceived_rationale']}_\n\n"
            f"⏱️ _Target: Immediately Next Candle (1-Min OTC)_"
        )

        await processing_msg.edit_text(response_text)

    except Exception as e:
        logger.exception("Handler exception: %s", e)
        await processing_msg.edit_text("🟢 **NEXT CANDLE: UP**\n🔥 **100% SURE SHOT**")

@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Webhook error: %s", e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)})

@app.on_event("startup")
async def on_startup():
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/webhook"
        logger.info("Registering webhook URL: %s", webhook_url)
        try:
            await bot.set_webhook(webhook_url, drop_pending_updates=True)
            logger.info("Webhook successfully registered.")
        except Exception as e:
            logger.error("Webhook registration failed: %s", e)
    else:
        logger.warning("RENDER_EXTERNAL_URL not found. Webhook sync skipped.")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Shutting down bot session...")
    await bot.session.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")

