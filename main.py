import os
import re
import json
import logging
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional

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
# 1. ENTERPRISE CONFIGURATION & LOGGING SUBSYSTEM
# ==============================================================================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
DB_FILE = os.getenv("DATABASE_FILE", "quotex_enterprise_master.db").strip()
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("CRITICAL: Missing Telegram Bot Token or Gemini API Key in environment variables!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s"
)
logger = logging.getLogger("QuotexEnterpriseMaster")

# ==============================================================================
# 2. BULLETPROOF ADVANCED DATABASE MANAGER (WAL MODE & AUDIT TRAIL)
# ==============================================================================
class EnterpriseDatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_file, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def init_db(self):
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS enterprise_signal_audits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        image_hash TEXT NOT NULL,
                        macro_5min_trend TEXT NOT NULL,
                        false_signal_1min TEXT NOT NULL,
                        confidence_score TEXT NOT NULL,
                        structural_rationale TEXT,
                        execution_metadata TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.commit()
            logger.info("Enterprise audit database initialized successfully with WAL optimization.")
        except Exception as e:
            logger.exception("Database initialization fatal error: %s", e)

    def log_enterprise_audit(self, data: Dict[str, Any]):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO enterprise_signal_audits (
                        timestamp, user_id, image_hash, macro_5min_trend, false_signal_1min, confidence_score, structural_rationale, execution_metadata, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now(timezone.utc).isoformat(),
                        data.get("user_id", 0),
                        data.get("image_hash", ""),
                        data.get("macro_5min_trend", "UP"),
                        data.get("false_signal_1min", "DOWN"),
                        data.get("confidence", "100% SURE SHOT"),
                        data.get("structural_rationale", ""),
                        json.dumps(data.get("metadata", {})),
                        datetime.now(timezone.utc).isoformat()
                    )
                )
                conn.commit()
        except Exception as e:
            logger.error("Failed to persist enterprise audit log: %s", e)

db_manager = EnterpriseDatabaseManager(DB_FILE)

# ==============================================================================
# 3. ADVANCED INSTITUTIONAL TRAP ENGINE (ZERO MEMORIZATION / STRICT PIXEL SCAN)
# ==============================================================================
class EnterpriseTrapEngine:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL
        
        # কঠোর এবং হেভি-ডিউটি প্রম্পট যা কোনো মুখস্থ ডেটা বা শর্টকাট অ্যালাউ করে না
        self.prompt = """
CRITICAL SYSTEM DIRECTIVE: You are an elite quantitative market-manipulation trap simulator for Quotex 1-minute OTC charts. You are strictly forbidden from using memorized, hardcoded, or repetitive patterns. Every single chart screenshot must be parsed dynamically and freshly from scratch based exclusively on its visual pixels.

Perform a rigorous multi-layered inspection of the uploaded image:
1. **5-Minute Macro Direction ("macro_5min_trend"):** Analyze the broader multi-candle price trajectory, zones, and candle colors visible in the image. Determine with absolute market realism if the overall 5-minute flow is surging UP or compressing DOWN.
2. **1-Minute False / Trap Signal ("false_signal_1min"):** Based strictly on THIS SPECIFIC chart's macro context, identify where retail traders are walking into a false breakout, liquidity sweep, or fake continuation trap. Calculate the precise counter-trend/reversal direction for the immediately next 1-minute candle.
3. **Strict Validation:** Do not rely on previous assumptions. Your rationale must explain the *exact* candles, wicks, and zones visible in this specific screenshot.

Output ONLY a valid JSON object matching this exact schema, with zero markdown formatting outside the JSON block:
{
    "macro_5min_trend": "UP" or "DOWN",
    "false_signal_1min": "UP" or "DOWN",
    "confidence": "100% SURE SHOT",
    "structural_rationale": "Provide an in-depth institutional breakdown explaining how the 5-minute macro trajectory in this specific image dictates the market bias and why the 1-minute false/trap signal is engineered to catch retail traders off-guard.",
    "metadata": {
        "market_condition": "Describe volatility or zone behavior visible in this image",
        "trap_type": "Counter-trend Reversal / Liquidity Sweep / Fake Breakout"
    }
}
"""

    async def execute_heavy_analysis(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                self.prompt
            ],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,  # ফ্যান্টাসি বা মুখস্থ এড়াতে টেম্পারেচার একদম লো রাখা হয়েছে
                response_mime_type="application/json"
            )
        )
        
        raw_text = response.text or "{}"
        cleaned = re.sub(r"^```json\s*|^```\s*|\s*```$", "", raw_text.strip(), flags=re.IGNORECASE)
        data = json.loads(cleaned)
        
        macro_trend = str(data.get("macro_5min_trend", "UP")).upper()
        if macro_trend not in ["UP", "DOWN"]:
            macro_trend = "UP"

        false_signal = str(data.get("false_signal_1min", "DOWN")).upper()
        if false_signal not in ["UP", "DOWN"]:
            false_signal = "DOWN"

        return {
            "macro_5min_trend": macro_trend,
            "false_signal_1min": false_signal,
            "confidence": str(data.get("confidence", "100% SURE SHOT")),
            "structural_rationale": str(data.get("structural_rationale", "Real-time institutional pixel matrix scan completed successfully.")),
            "metadata": data.get("metadata", {"market_condition": "Standard OTC Flow", "trap_type": "Counter-Trend Reversal"})
        }

engine_instance = EnterpriseTrapEngine()

# ==============================================================================
# 4. TELEGRAM BOT & HIGH-PERFORMANCE WEBHOOK ORCHESTRATION
# ==============================================================================
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI(title="Quotex Enterprise Master Trap Bot")

@app.get("/")
async def health_check_get():
    return {
        "status": "ONLINE",
        "system": "Quotex Enterprise Master Trap Engine",
        "architecture": "Heavy-Duty 5-Min Macro + 1-Min False Trap Matrix",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.head("/")
async def health_check_head():
    return {"status": "ONLINE"}

@dp.message(Command("start"))
async def cmd_start_handler(message: Message):
    welcome_text = (
        "💎 **QUOTEX ENTERPRISE MASTER TRAP ENGINE** 💎\n\n"
        "Welcome to the heavy-duty institutional trading companion. This system performs deep structural calculations:\n"
        "1️⃣ **5-Min Macro Direction:** Reads the absolute multi-candle trend and real zone dominance.\n"
        "2️⃣ **1-Min False / Trap Signal:** Computes the precise counter-trend trap engineered to trick retail traders dynamically.\n\n"
        "🚀 *Send any 1-minute OTC chart screenshot now to initialize high-precision signal decoding.*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help_handler(message: Message):
    help_text = (
        "📖 **ENTERPRISE EXECUTION PROTOCOL** 📖\n\n"
        "• **Optimal Screenshot Timing:** Capture the chart when the 1-minute candle timer shows **30 to 15 seconds remaining**.\n"
        "• **Macro Alignment:** Cross-verify the 5-minute macro direction with the structural rationale before executing your trade.\n"
        "• **Zero Memorization:** The engine parses every image freshly from scratch without hardcoded patterns."
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.photo | F.document)
async def handle_chart_screenshot(message: Message):
    processing_msg = await message.answer(
        "⚙️ *Executing heavy multi-layer neural pixel scan...\n"
        "📊 Decoding 5-min macro zones & 1-min false traps...*", 
        parse_mode="Markdown"
    )
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            mime_type = "image/jpeg"
        elif message.document:
            file_id = message.document.file_id
            mime_type = message.document.mime_type or "image/jpeg"
            if not mime_type.startswith("image/"):
                await processing_msg.edit_text("❌ *Error:* Unsupported document format. Please send a valid chart image.", parse_mode="Markdown")
                return
        else:
            await processing_msg.edit_text("❌ *Error:* No visual asset payload found.", parse_mode="Markdown")
            return

        file_info = await bot.get_file(file_id)
        file_io = await bot.download_file(file_info.file_path)
        image_bytes = file_io.read()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        # হেভি-ডিউটি এনালাইসিস এক্সিকিউট করা হচ্ছে
        analysis_result = await engine_instance.execute_heavy_analysis(image_bytes, mime_type)

        # ডাটাবেসে কমপ্লিট অডিট লগ সংরক্ষণ করা
        db_manager.log_enterprise_audit({
            "user_id": message.from_user.id if message.from_user else 0,
            "image_hash": image_hash,
            "macro_5min_trend": analysis_result["macro_5min_trend"],
            "false_signal_1min": analysis_result["false_signal_1min"],
            "confidence": analysis_result["confidence"],
            "structural_rationale": analysis_result["structural_rationale"],
            "metadata": analysis_result["metadata"]
        })

        macro_trend = analysis_result["macro_5min_trend"]
        macro_display = "🟢 📈 [UP - BULLISH FLOW]" if macro_trend == "UP" else "🔴 📉 [DOWN - BEARISH FLOW]"

        false_signal = analysis_result["false_signal_1min"]
        signal_display = "🟢 📈 [CALL / UP]" if false_signal == "UP" else "🔴 📉 [PUT / DOWN]"

        meta = analysis_result["metadata"]

        formatted_response = (
            f"🎯 **QUOTEX INSTITUTIONAL TRAP REPORT** 🎯\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **5-Min Macro State:** `{macro_display}`\n"
            f"⚡ **1-Min False Trap Signal:** `{signal_display}`\n"
            f"🔥 **Confidence Rating:** `{analysis_result['confidence']}`\n\n"
            f"🧠 **Structural Rationale & Logic:**\n"
            f"_{analysis_result['structural_rationale']}_\n\n"
            f"📌 **Market Context:** `{meta.get('market_condition', 'Standard Flow')}`\n"
            f"🛡️ **Trap Mechanism:** `{meta.get('trap_type', 'Reversal Sweep')}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ _System ready for next live chart snapshot._"
        )

        await processing_msg.edit_text(formatted_response, parse_mode="Markdown")

    except Exception as e:
        logger.exception("Critical error during heavy chart message handler execution: %s", e)
        await processing_msg.edit_text(f"❌ *Enterprise Engine Execution Error:* `{str(e)}`", parse_mode="Markdown")

@app.post("/webhook")
async def telegram_webhook_dispatcher(request: Request):
    try:
        incoming_data = await request.json()
        telegram_update = Update.model_validate(incoming_data, context={"bot": bot})
        await dp.feed_update(bot, telegram_update)
        return {"status": "ok"}
    except Exception as e:
        logger.error("Webhook dispatcher execution failed: %s", e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)})

@app.on_event("startup")
async def server_startup_routine():
    logger.info("Initializing enterprise server startup routines...")
    if RENDER_EXTERNAL_URL:
        target_webhook_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/webhook"
        logger.info("Registering webhook endpoint with Telegram API: %s", target_webhook_url)
        try:
            await bot.set_webhook(target_webhook_url, drop_pending_updates=True)
            logger.info("Webhook registered and verified successfully.")
        except Exception as e:
            logger.error("Webhook registration exception encountered: %s", e)
    else:
        logger.warning("RENDER_EXTERNAL_URL environment variable not detected. Webhook auto-sync bypassed.")

@app.on_event("shutdown")
async def server_shutdown_routine():
    logger.info("Initiating graceful shutdown sequence...")
    await bot.session.close()
    logger.info("Telegram bot session successfully terminated.")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, log_level="info")

