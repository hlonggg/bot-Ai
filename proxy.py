import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# ================== CẤU HÌNH ==================
BOT_TOKEN = "8983631020:AAHitwdCI9SyIeTqR2Ukr50Ng_V84JmcE7U"
GEMINI_API_KEY = "AQ.Ab8RN6KNuFi0fhJuzi3QFZriNmADNgibTyYvUC6qZ6U-1K7lug"
GEMINI_MODEL = "gemini-3.6-flash"

SYSTEM_PROMPT = (
    "Bạn là một trợ lý AI thông minh, thân thiện và hài hước. "
    "Hãy trả lời câu hỏi của người dùng một cách tự nhiên, dễ hiểu, "
    "với giọng điệu vui vẻ, tích cực. Trả lời ngắn gọn nhưng đầy đủ ý, "
    "không lan man. Nếu không biết câu trả lời, hãy thành thật nói không biết."
)

# SỬA LẠI Ở ĐÂY: Dùng default_headers
client = OpenAI(
    api_key="dummy_key",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    default_headers={"x-goog-api-key": GEMINI_API_KEY}
)

user_sessions = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.CRITICAL)    
logging.getLogger("httpcore").setLevel(logging.CRITICAL) 
logging.getLogger("telegram").setLevel(logging.WARNING)  

logger = logging.getLogger(__name__)

MAX_HISTORY = 5 

def get_or_create_session(user_id: int):
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "enabled": False,
            "history": [{"role": "system", "content": SYSTEM_PROMPT}]
        }
    return user_sessions[user_id]

async def get_gemini_response(user_id: int, user_message: str) -> str:
    session = get_or_create_session(user_id)
    history = session["history"]

    history.append({"role": "user", "content": user_message})

    system_msg = history[0]
    other_msgs = history[1:]
    if len(other_msgs) > MAX_HISTORY * 2:
        other_msgs = other_msgs[-MAX_HISTORY * 2:]
    history = [system_msg] + other_msgs
    session["history"] = history

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: client.chat.completions.create(
                model=GEMINI_MODEL,
                messages=history,
                stream=False,
                max_tokens=512,
                temperature=0.7,
            )
        )
        
        assistant_reply = response.choices[0].message.content
        history.append({"role": "assistant", "content": assistant_reply})
        session["history"] = history
        return assistant_reply
    except Exception as e:
        logger.error(f"Lỗi Gemini API: {e}")
        return "⚠️ API gặp sự cố. Vui lòng thử lại sau."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Chào bạn! Bot đã sẵn sàng.\n\n"
        "👉 /dsk - Bật chế độ AI\n"
        "👉 /dskoff - Tắt chế độ AI\n"
        "👉 /reset - Xóa lịch sử chat\n\n"
        "Hãy reply vào tin nhắn của tôi để hỏi nhé!"
    )

async def dsk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_or_create_session(update.effective_user.id)
    session["enabled"] = True
    await update.message.reply_text("✅ Đã bật AI.")

async def dskoff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["enabled"] = False
    await update.message.reply_text("❌ Đã tắt AI.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]["history"] = [{"role": "system", "content": SYSTEM_PROMPT}]
        await update.message.reply_text("🔄 Đã xóa lịch sử hội thoại.")
    else:
        await update.message.reply_text("Bạn chưa có lịch sử nào.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    reply_to = update.message.reply_to_message

    if reply_to is None or reply_to.from_user.id != context.bot.id:
        return

    session = get_or_create_session(user_id)
    if not session["enabled"]:
        await update.message.reply_text("🔇 AI đang tắt. Gõ /dsk để bật.")
        return

    reply = await get_gemini_response(user_id, user_message)
    await update.message.reply_text(reply)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dsk", dsk))
    app.add_handler(CommandHandler("dskoff", dskoff))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
