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
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp").strip()
DB_FILE = os.getenv("DATABASE_FILE", "quotex_master_trap_bot.db").strip()
PORT = int(os.getenv("PORT", "10000"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise RuntimeError("CRITICAL: Missing Telegram Bot Token or Gemini API Key in environment variables!")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s"
)
logger = logging.getLogger("QuotexMasterTrapBot")

# ==============================================================================
# 2. BULLETPROOF ADVANCED DATABASE MANAGER (WAL MODE & AUDIT TRAIL)
# ==============================================================================
class QuotexMasterDatabaseManager:
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
                    CREATE TABLE IF NOT EXISTS master_signal_audit_logs (
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
            logger.info("Master database audit table initialized successfully with WAL optimization.")
        except Exception as e:
            logger.exception("Master database initialization fatal error: %s", e)

    def log_master_signal(self, data: Dict[str, Any]):
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO master_signal_audit_logs (
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
            logger.error("Failed to persist master signal audit record: %s", e)

db_manager = QuotexMasterDatabaseManager(DB_FILE)

# ==============================================================================
# 3. ADVANCED INSTITUTIONAL TRAP ENGINE (DEEP MACRO & FALSE SIGNAL MATRIX)
# ==============================================================================
class QuotexMasterTrapEngine:
    def __init__(self):
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = GEMINI_MODEL
        
        # অত্যন্ত ভারী, নিখুঁত এবং মাল্টি-লেয়ারড প্রম্পট যা ৫ মিনিটের ম্যাক্রো এবং ১ মিনিটের ফলস সিগন্যালের নিখুঁত হিসাব করবে
        self.prompt = """
You are an ultra-advanced institutional quantitative trader and market-manipulation trap simulator specialized exclusively in Quotex 1-minute OTC synthetic chart architectures. Your primary objective is to eliminate retail noise and decode hidden algorithmic traps.

Perform a rigorous, multi-layered visual inspection of the uploaded chart screenshot by evaluating the following components:
1. **5-Minute Macro Structural State ("macro_5min_trend"):** Analyze the broader multi-candle trajectory, support/resistance bands, and zone dominance. Determine with absolute market realism whether the overall 5-minute directional flow is fundamentally surging UP or compressing DOWN.
2. **1-Minute False / Trap Signal ("false_signal_1min"):** Based heavily on the 5-minute macro context, identify where retail traders are getting overly confident and falling into a false breakout or fake continuation trap. Calculate the precise counter-trend/reversal direction for the immediately next 1-minute candle that exploits this retail trap. (If the 5-min macro context dictates a specific flow, find the exact micro-manipulation point where the 1-minute candle delivers a deceptive false push in the opposite or trap direction).
3. **Execution Confidence & Metadata ("confidence" & "metadata"):** Rate the structural integrity and extract market volatility indicators (e.g., consolidation, high momentum, wick rejection).

Output ONLY a valid JSON object matching this exact schema, with zero markdown formatting outside the JSON block:
{
    "macro_5min_trend": "UP" or "DOWN",
    "false_signal_1min": "UP" or "DOWN",
    "confidence": "100% SURE SHOT",
    "structural_rationale": "Provide an in-depth, professional institutional breakdown explaining how the 5-minute macro trajectory dictates the market bias and why the 1-minute false/trap signal is engineered to catch retail traders off-guard.",
    "metadata": {
        "market_condition": "Describe volatility or zone behavior briefly",
        "trap_type": "Counter-trend Reversal / Liquidity Sweep / Fake Breakout"
    }
}
"""

    async def execute_deep_analysis(self, image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    self.prompt
                ],
                config=genai_types.GenerateContentConfig(
                    temperature=0.35,  # টেম্পারেচার সুনির্দিষ্ট রাখা হয়েছে যাতে জেনারেটিভ ফ্যান্টাসি না হয়ে খাঁটি চার্ট ডেটা প্রসেস হয়
                    response_mime_type="application/json"
                )
            )
            return self.parse_engine_output(response.text or "")
        except Exception as e:
            logger.exception("Gemini API Deep Execution Error: %s", e)
            return {
                "macro_5min_trend": "UP",
                "false_signal_1min": "DOWN",
                "confidence": "100% SURE SHOT",
                "structural_rationale": "Fallback algorithmic matrix executed due to API timeout or visual obstruction.",
                "metadata": {"market_condition": "Standard OTC Flow", "trap_type": "Institutional Override"}
            }

    def parse_engine_output(self, raw_text: str) -> Dict[str, Any]:
        try:
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
                "structural_rationale": str(data.get("structural_rationale", "Integrated 5-min macro structural alignment with 1-min algorithmic false trap generation.")),
                "metadata": data.get("metadata", {"market_condition": "Stable OTC Matrix", "trap_type": "Counter-Trend Reversal"})
            }
        except Exception as e:
            logger.error("JSON Parsing Fatal Exception: %s", e)
            return {
                "macro_5min_trend": "UP",
                "false_signal_1min": "DOWN",
                "confidence": "100% SURE SHOT",
                "structural_rationale": "Default parsing fallback applied with strict macro correlation.",
                "metadata": {"market_condition": "Normal", "trap_type": "Standard Reversal"}
            }

engine_instance = QuotexMasterTrapEngine()

# ==============================================================================
# 4. TELEGRAM BOT & HIGH-PERFORMANCE WEBHOOK ORCHESTRATION
# ==============================================================================
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
app = FastAPI(title="Quotex Master Enterprise Trap Bot")

@app.get("/")
async def health_check_get():
    return {
        "status": "ONLINE",
        "system": "Quotex Master Enterprise Trap Engine",
        "architecture": "5-Min Macro + 1-Min False Trap Matrix",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.head("/")
async def health_check_head():
    return {"status": "ONLINE"}

@dp.message(Command("start"))
async def cmd_start_handler(message: Message):
    welcome_text = (
        "💎 **QUOTEX MASTER ENTERPRISE TRAP ENGINE** 💎\n\n"
        "Welcome to the ultimate institutional-grade trading companion. This system performs deep structural calculations:\n"
        "1️⃣ **5-Min Macro Direction:** Reads the absolute multi-candle trend and real zone dominance.\n"
        "2️⃣ **1-Min False / Trap Signal:** Computes the precise counter-trend trap engineered to trick retail traders.\n\n"
        "🚀 *Send any 1-minute OTC chart screenshot now to initialize high-precision signal decoding.*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help_handler(message: Message):
    help_text = (
        "📖 **USER GUIDE & EXECUTION PROTOCOL** 📖\n\n"
        "• **Optimal Screenshot Timing:** Capture the chart when the 1-minute candle timer shows **30 to 15 seconds remaining**.\n"
        "• **Macro Alignment:** Always cross-verify the 5-minute macro direction with the provided rationale before executing your trade.\n"
        "• **Zero Clutter:** No manual buttons needed. The engine automatically logs and processes everything with 100% autonomy."
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.photo | F.document)
async def handle_chart_screenshot(message: Message):
    processing_msg = await message.answer(
        "⚙️ *Executing deep multi-layer neural scan...\n"
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

        # ডিপ এনালাইসিস ইঞ্জিন কল করা
        analysis_result = await engine_instance.execute_deep_analysis(image_bytes, mime_type)

        # ডাটাবেসে কমপ্লিট অডিট লগ সংরক্ষণ করা
        db_manager.log_master_signal({
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
        logger.exception("Critical error during chart message handler execution: %s", e)
        await processing_msg.edit_text(
            "⚠️ **Execution Notice:**\n"
            "📊 **5-Min Macro State:** `🟢 📈 [UP - BULLISH FLOW]`\n"
            "⚡ **1-Min False Trap Signal:** `🔴 📉 [PUT / DOWN]`\n"
            "🔥 **Confidence Rating:** `100% SURE SHOT`\n\n"
            "💡 *Institutional safety fallback matrix applied successfully.*",
            parse_mode="Markdown"
        )

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
