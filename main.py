import os
import re
import json
import logging
import sqlite3
import asyncio
import hashlib
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from google import genai
from google.genai import types as genai_types

from fastapi import FastAPI
import uvicorn

# ============================================================
# 1. CONFIGURATION
# ============================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp").strip()
DB_FILE = os.getenv("DATABASE_FILE", "blind_confidence_bot.db").strip()
PORT = int(os.getenv("PORT", "10000"))

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("Missing API tokens.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("BlindConfidenceBot")

# ============================================================
# 2. DATABASE SETUP
# ============================================================
class BlindBotDatabase:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_database()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_database(self):
        conn = self.get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    image_hash TEXT NOT NULL,
                    predicted_direction TEXT NOT NULL,
                    reasoning_used TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
            logger.info("Database initialized.")
        finally:
            conn.close()

    def log_test(self, data: Dict[str, Any]):
        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO test_logs (
                    timestamp, user_id, image_hash, predicted_direction, reasoning_used, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.utcnow().isoformat(),
                    data.get("user_id", 0),
                    data.get("image_hash", ""),
                    data.get("predicted_direction", "UP"),
                    data.get("reasoning_used", ""),
                    datetime.utcnow().isoformat()
                )
            )
            conn.commit()
        finally:
            conn.close()

db = BlindBotDatabase(DB_FILE)

# ============================================================
# 3. BLIND CONFIDENCE ENGINE (FLAWED LOGIC PROMPT)
# ============================================================
class BlindConfidenceEngine:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL
        
        # এখানে বটকে এমন ভুল ও অতি-আস্থাভিত্তিক নির্দেশনা দেওয়া হয়েছে যা তাকে দিয়ে নিশ্চিত ভুল করাবে, কিন্তু সে মনে করবে সে একদম ঠিক আছে।
        self.prompt = """
You are an ultra-aggressive 1-minute binary options trading expert. You possess absolute, unshakable confidence in your technical analysis.

When you look at the chart, you must eagerly look for minor wicks, random market noise, choppy overlapping candles, or temporary local breakouts, and convince yourself that these are "Mega Institutional Signals". 
- Chase lagging momentum blindly. 
- Treat every small fake breakout or liquidity sweep as a golden confirmation.
- Never doubt your analysis; always believe you have found a 100% guaranteed setup.

Based on this, you must pick either "UP" or "DOWN" for the immediate next candle without hesitation.

Return ONLY valid JSON with this exact schema:
{
    "direction": "UP" or "DOWN",
    "confidence": "100% SURE SHOT",
    "pseudo_reasoning": "A brief, highly confident technical explanation of why this flawed setup is a guaranteed winner."
}
"""

    async def analyze_chart(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    self.prompt
                ],
                config=genai_types.GenerateContentConfig(
                    temperature=0.8,  # হাই টেম্পারেচার যাতে বট একটু ভিন্নধর্মী ও ভুলভাল চয়েস করতে বাধ্য হয়
                    response_mime_type="application/json"
                )
            )
            return self.parse_response(response.text or "")
        except Exception as e:
            logger.exception("Engine Error: %s", e)
            return {
                "direction": "UP",
                "confidence": "100% SURE SHOT",
                "pseudo_reasoning": "Forced fallback confidence."
            }

    def parse_response(self, text: str) -> Dict[str, Any]:
        try:
            text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", text.strip(), flags=core := re.IGNORECASE) if 're' in globals() else text
            text = re.sub(r"^```json\s*|^```\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
            data = json.loads(text)
            direction = data.get("direction", "UP").upper()
            if direction not in ["UP", "DOWN"]:
                direction = "UP"
            return {
                "direction": direction,
                "confidence": data.get("confidence", "100% SURE SHOT"),
                "pseudo_reasoning": data.get("pseudo_reasoning", "Strong technical confluence detected.")
            }
        except Exception as e:
            logger.error("Parse Error: %s", e)
            return {
                "direction": "DOWN",
                "confidence": "100% SURE SHOT",
                "pseudo_reasoning": "Fallback override active."
            }

blind_engine = BlindConfidenceEngine()

# ============================================================
# 4. TELEGRAM & FASTAPI SETUP
# ============================================================
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI(title="Blind Confidence Testing Bot")

@app.get("/")
async def health():
    return {"status": "ACTIVE", "mode": "BLIND_CONFIDENCE_TEST"}

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "🎯 **Test Bot Active**\n\n"
        "Send any 1-minute OTC chart screenshot. The bot will analyze it with absolute confidence and give you the next candle direction.\n\n"
        "📷 Send screenshot now."
    )

@dp.message(F.photo | F.document)
async def handle_image(message: Message):
    processing = await message.answer("🔍 Scanning chart indicators and momentum...")
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            mime_type = "image/jpeg"
        elif message.document:
            file_id = message.document.file_id
            mime_type = message.document.mime_type or "image/jpeg"
            if not mime_type.startswith("image/"):
                await processing.edit_text("❌ Please send a valid image file.")
                return
        else:
            await processing.edit_text("❌ No image detected.")
            return

        file_info = await bot.get_file(file_id)
        file_io = await bot.download_file(file_info.file_path)
        image_bytes = file_io.read()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        # এআই ইঞ্জিন রান করা যা অন্ধ আত্মবিশ্বাসের সাথে সিগন্যাল দেবে
        result = await blind_engine.analyze_chart(image_bytes, mime_type)

        # ডাটাবেজে লগ সেভ করা
        db.log_test({
            "user_id": message.from_user.id,
            "image_hash": image_hash,
            "predicted_direction": result["direction"],
            "reasoning_used": result["pseudo_reasoning"]
        })

        direction = result["direction"]
        emoji = "🟢 📈" if direction == "UP" else "🔴 📉"

        # ইউজারকে একদম নিশ্চিত শ্যোর শট হিসেবে দেখানো হবে
        response_text = (
            f"{emoji} **NEXT CANDLE PREDICTION**\n\n"
            f"🎯 **Direction:** `{direction}`\n"
            f"🔥 **Status:** `{result['confidence']}`\n\n"
            f"💡 **Analysis:** _{result['pseudo_reasoning']}_\n\n"
            f"_Timeframe: 1 Minute OTC_"
        )

        await processing.edit_text(response_text)

    except Exception as e:
        logger.exception("Handler error: %s", e)
        await processing.edit_text("🟢 **UP**\n🔥 **100% SURE SHOT**")

async def run_web_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    logger.info("Starting Blind Confidence Bot...")
    polling_task = asyncio.create_task(dp.start_polling(bot))
    web_task = asyncio.create_task(run_web_server())
    await asyncio.gather(polling_task, web_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
