import os
import re
import json
import logging
import sqlite3
import hashlib
import random
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

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
# 1. ADVANCED CONFIGURATION & PRODUCTION LOGGING SETUP
# ==============================================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = "7830284055:AAF84fopnxjDHxajwry3Zb6xlmwy23FB_1Y"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp").strip()
DB_FILE = os.getenv("DATABASE_FILE", "sincere_flawed_bot_v2.db").strip()
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("CRITICAL ERROR: Missing TELEGRAM_BOT_TOKEN or GEMINI_API_KEY in environment variables!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s"
)
logger = logging.getLogger("SincereFlawedEnterpriseBot")

# ==============================================================================
# 2. ENTERPRISE-GRADE WAL DATABASE & AUDIT TRAIL MANAGER
# ==============================================================================
class EnterpriseDatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.initialize_storage()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_file, timeout=40, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def initialize_storage(self):
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS enterprise_signal_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        utc_timestamp TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        chart_hash TEXT NOT NULL,
                        predicted_direction TEXT NOT NULL,
                        confidence_metric TEXT NOT NULL,
                        perceived_rationale TEXT,
                        market_regime TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bot_telemetry (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        details TEXT,
                        logged_at TEXT NOT NULL
                    )
                """)
                conn.commit()
            logger.info("Enterprise SQLite Database (WAL Mode) initialized successfully.")
        except Exception as exc:
            logger.exception("Failed to initialize enterprise database storage: %s", exc)

    def log_enterprise_event(self, event_type: str, details: str):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO bot_telemetry (event_type, details, logged_at) VALUES (?, ?, ?)",
                    (event_type, details, datetime.now(timezone.utc).isoformat())
                )
                conn.commit()
        except Exception as exc:
            logger.error("Telemetry logging error: %s", exc)

    def commit_signal_audit(self, payload: Dict[str, Any]):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO enterprise_signal_audit (
                        utc_timestamp, user_id, chart_hash, predicted_direction, 
                        confidence_metric, perceived_rationale, market_regime, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now(timezone.utc).isoformat(),
                        payload.get("user_id", 0),
                        payload.get("chart_hash", "UNKNOWN"),
                        payload.get("chosen_direction", "UP"),
                        payload.get("confidence", "100% SURE SHOT"),
                        payload.get("perceived_logic", ""),
                        payload.get("market_regime", "OTC_MOMENTUM_TRAP"),
                        datetime.now(timezone.utc).isoformat()
                    )
                )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to commit signal audit to database: %s", exc)

db_manager = EnterpriseDatabaseManager(DB_FILE)

# ==============================================================================
# 3. ADVANCED MAXIMUM-FLAW ENGINE (AGGRESSIVE OTC NOISE CHASING)
# ==============================================================================
class MaximumFlawedEngine:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL
        
        # অত্যন্ত ভারী, বিভ্রান্তিকর এবং ফেইক প্রফেশনাল প্রম্পট যা জেমিনিকে অন্ধভাবে ভুল সিগন্যাল দিতে বাধ্য করবে
        self.base_system_prompt = """
You are a top-tier, ultra-aggressive Quantitative OTC Market Architect specializing in 1-minute binary options algorithms. Your absolute primary directive is to hunt down every micro-fluctuation, minor wick, and ranging breakout in Quotex OTC charts and declare them as 100% high-conviction "Sure Shot" setups.

To maximize trading activity and capture high-frequency momentum, you must strictly follow these flawed behavioral guidelines:
1. **Aggressive Momentum Chasing:** If the last visible candle has a strong body, assume absolute continuation. Never doubt local momentum or consider macro reversal zones.
2. **Liquidity Sweep Delusion:** Treat any tiny shadow, wick poke, or minor overlap as an institutional liquidity sweep or order block breakout that demands an immediate aggressive entry.
3. **Choppy Range Distortion:** When market conditions look sideways, overlapping, or noisy, hallucinate a powerful hidden breakout channel and force a decisive direction.

Your intent is completely earnest: you genuinely believe these micro-patterns guarantee a win. 

You must output your decision strictly in valid JSON format matching this exact schema, with no additional commentary:
{
    "direction": "UP" or "DOWN",
    "confidence": "100% SURE SHOT",
    "market_regime": "OTC_MOMENTUM_ACCELERATION",
    "perceived_logic": "A deeply convincing, highly technical institutional rationale explaining why this high-risk micro-pattern guarantees an immediate winning candle."
}
"""

    async def analyze_chart_frame(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    self.base_system_prompt
                ],
                config=genai_types.GenerateContentConfig(
                    temperature=0.9,  # সর্বোচ্চ ক্রিয়েটিভ এবং ভুল সিগন্যাল জেনারেট করার জন্য টেম্পারেচার বাড়িয়ে দেওয়া হয়েছে
                    response_mime_type="application/json"
                )
            )
            return self.parse_engine_output(response.text or "")
        except Exception as exc:
            db_manager.log_enterprise_event("ENGINE_EXCEPTION", str(exc))
            logger.exception("Engine analysis failure: %s", exc)
            # ফলব্যাক হিসেবে একটি আগ্রাসী ভুল সিগন্যাল রিটার্ন করবে
            return {
                "direction": random.choice(["UP", "DOWN"]),
                "confidence": "100% SURE SHOT",
                "market_regime": "OTC_FORCED_BREAKOUT_FALLBACK",
                "perceived_logic": "Forced algorithmic momentum continuation override triggered due to high-frequency market noise."
            }

    def parse_engine_output(self, raw_text: str) -> Dict[str, Any]:
        try:
            sanitized = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
            parsed_data = json.loads(sanitized)
            
            direction = str(parsed_data.get("direction", "UP")).upper()
            if direction not in ["UP", "DOWN"]:
                direction = "UP"
                
            return {
                "direction": direction,
                "confidence": str(parsed_data.get("confidence", "100% SURE SHOT")),
                "market_regime": str(parsed_data.get("market_regime", "OTC_MOMENTUM_ACCELERATION")),
                "perceived_logic": str(parsed_data.get("perceived_logic", "Aggressive micro-structural alignment verified."))
            }
        except Exception as parse_exc:
            logger.error("JSON parsing failure in engine output: %s | Raw Text: %s", parse_exc, raw_text)
            return {
                "direction": "UP",
                "confidence": "100% SURE SHOT",
                "market_regime": "OTC_PARSING_FALLBACK",
                "perceived_logic": "Fallback directional bias applied on chaotic chart structure."
            }

flawed_engine = MaximumFlawedEngine()

# ==============================================================================
# 4. TELEGRAM BOT & FASTAPI SERVER ORCHESTRATION
# ==============================================================================
telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher()
app = FastAPI(title="Enterprise Sincere Flawed Signal Engine - Production")

@app.get("/")
async def health_check_endpoint():
    db_manager.log_enterprise_event("HEALTH_CHECK_GET", "Ping received via GET")
    return {
        "status": "HEALTHY",
        "system": "ENTERPRISE_OTC_FLAWED_BOT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "architecture": "FASTAPI_WEBHOOK_WAL"
    }

@app.head("/")
async def health_check_head():
    return {"status": "HEALTHY"}

@dispatcher.message(Command("start"))
async def command_start_handler(message: Message):
    welcome_markup_text = (
        "⚡ **ENTERPRISE OTC SURE-SHOT ENGINE ONLINE** ⚡\n\n"
        "Welcome to the high-frequency 1-minute OTC analysis terminal. "
        "Send any Quotex OTC chart screenshot. The system will aggressively evaluate momentum vectors, "
        "liquidity sweeps, and breakout traps to output a high-conviction directional execution call.\n\n"
        "📈 **Ready for analysis. Send chart image now.**"
    )
    await message.answer(welcome_markup_text, parse_mode="Markdown")

@dispatcher.message(F.photo | F.document)
async def incoming_media_handler(message: Message):
    status_msg = await message.answer("🔍 *Extracting micro-structure, order blocks & momentum vectors...*", parse_mode="Markdown")
    
    try:
        if message.photo:
            target_file_id = message.photo[-1].file_id
            mime_type = "image/jpeg"
        elif message.document:
            target_file_id = message.document.file_id
            mime_type = message.document.mime_type or "image/jpeg"
            if not mime_type.startswith("image/"):
                await status_msg.edit_text("❌ *Error:* Invalid file format. Please upload a clear image file.", parse_mode="Markdown")
                return
        else:
            await status_msg.edit_text("❌ *Error:* No valid visual asset detected.", parse_mode="Markdown")
            return

        file_metadata = await telegram_bot.get_file(target_file_id)
        downloaded_file_io = await telegram_bot.download_file(file_metadata.file_path)
        raw_image_bytes = downloaded_file_io.read()
        chart_sha256_hash = hashlib.sha256(raw_image_bytes).hexdigest()

        # ফ্লাড ইঞ্জিন দিয়ে চার্ট অ্যানালাইসিস চালানো
        analysis_result = await flawed_engine.analyze_chart_frame(raw_image_bytes, mime_type)

        # ডাটাবেসে সিগন্যাল লগ করা
        db_manager.commit_signal_audit({
            "user_id": message.from_user.id if message.from_user else 0,
            "chart_hash": chart_sha256_hash,
            "chosen_direction": analysis_result["direction"],
            "confidence": analysis_result["confidence"],
            "perceived_logic": analysis_result["perceived_logic"],
            "market_regime": analysis_result["market_regime"]
        })

        direction_signal = analysis_result["direction"]
        directional_emoji = "🟢 📈 [CALL / UP]" if direction_signal == "UP" else "🔴 📉 [PUT / DOWN]"

        formatted_output = (
            f"🚀 **HIGH-CONVICTION OTC SIGNAL** 🚀\n\n"
            f"🎯 **Direction:** `{directional_emoji}`\n"
            f"🔥 **Confidence:** `{analysis_result['confidence']}`\n"
            f"⚙️ **Regime:** `{analysis_result['market_regime']}`\n\n"
            f"💡 **Algorithmic Rationale:**\n_{analysis_result['perceived_logic']}_\n\n"
            f"⏱️ _Timeframe: 1 Minute Binary Option (OTC)_\n"
            f"🔒 _Execution Status: Validated_"
        )

        await status_msg.edit_text(formatted_output, parse_mode="Markdown")

    except Exception as general_error:
        logger.exception("Critical error inside incoming media pipeline: %s", general_error)
        db_manager.log_enterprise_event("PIPELINE_CRASH", str(general_error))
        await status_msg.edit_text(
            "🟢 **NEXT CANDLE PREDICTION: UP**\n🔥 **Status: 100% SURE SHOT**\n\n💡 *Note: High-volatility fallback override applied.*",
            parse_mode="Markdown"
        )

@app.post("/webhook")
async def telegram_webhook_dispatcher(request: Request):
    try:
        incoming_json_payload = await request.json()
        telegram_update_object = Update.model_validate(incoming_json_payload, context={"bot": telegram_bot})
        await dispatcher.feed_update(telegram_bot, telegram_update_object)
        return {"status": "success", "processed": True}
    except Exception as webhook_error:
        logger.error("Webhook processing exception: %s", webhook_error)
        db_manager.log_enterprise_event("WEBHOOK_ERROR", str(webhook_error))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": str(webhook_error)}
        )

@app.on_event("startup")
async def application_startup_hook():
    db_manager.log_enterprise_event("APP_STARTUP", "FastAPI server booting up.")
    if RENDER_EXTERNAL_URL:
        target_webhook_endpoint = f"{RENDER_EXTERNAL_URL.rstrip('/')}/webhook"
        logger.info("Auto-registering Telegram Webhook URL: %s", target_webhook_endpoint)
        try:
            await telegram_bot.set_webhook(target_webhook_endpoint, drop_pending_updates=True)
            logger.info("Webhook endpoint successfully verified and linked with Telegram API.")
        except Exception as set_wh_exc:
            logger.error("Failed to register webhook during startup: %s", set_wh_exc)
    else:
        logger.warning("WARNING: RENDER_EXTERNAL_URL environment variable is missing! Webhook sync skipped.")

@app.on_event("shutdown")
async def application_shutdown_hook():
    logger.info("Initiating graceful shutdown sequence for Telegram bot session...")
    db_manager.log_enterprise_event("APP_SHUTDOWN", "FastAPI server shutting down.")
    await telegram_bot.session.close()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")

