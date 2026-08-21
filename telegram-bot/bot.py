import logging
import os
import datetime as dt

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("budget-bot")

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_BASE = os.environ.get("API_BASE_URL", "http://budget-api:8000")
API_KEY = os.environ.get("API_KEY", "")
CURRENCY = os.environ.get("DEFAULT_CURRENCY", "SAR")


def _split_ids(raw: str) -> set[int]:
    return {int(p.strip()) for p in (raw or "").split(",") if p.strip()}


ALLOWED_USER_IDS = _split_ids(os.environ.get("ALLOWED_TELEGRAM_USER_IDS", ""))

_headers = {"X-API-Key": API_KEY} if API_KEY else {}
client = httpx.Client(base_url=API_BASE, headers=_headers, timeout=65.0)

# in-memory: last transaction id(s) this telegram user logged, for /undo
_last_txns: dict[int, tuple[list[int], dt.datetime]] = {}
UNDO_WINDOW = dt.timedelta(minutes=15)


def _authorized(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return False
    return user_id in ALLOWED_USER_IDS


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram user ID is: {update.effective_user.id}\n"
        f"Give this to whoever manages ALLOWED_TELEGRAM_USER_IDS to get access."
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update.effective_user.id):
        await update.message.reply_text("This bot is private. Send /whoami and ask the family admin to add your ID.")
        return
    await update.message.reply_text(
        "👋 Hi! Just tell me what you spent, earned, or saved — plain sentences work.\n\n"
        "Examples:\n"
        "• spent 45 on groceries today\n"
        "• paid 1000 rent yesterday, bank transfer\n"
        "• got my salary, 9500\n"
        "• put 500 into emergency fund\n\n"
        "Commands: /categories  /undo  /help"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def list_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update.effective_user.id):
        return
    try:
        resp = client.get("/api/categories")
        resp.raise_for_status()
        cats = resp.json()
    except httpx.HTTPError:
        await update.message.reply_text("Couldn't reach the budget API right now.")
        return
    grouped: dict[str, list[str]] = {}
    for c in cats:
        grouped.setdefault(c["category"], []).append(c["subcategory"])
    lines = [f"*{cat}*: " + ", ".join(subs) for cat, subs in grouped.items()]
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _authorized(user_id):
        return
    entry = _last_txns.get(user_id)
    if not entry:
        await update.message.reply_text("Nothing to undo (or the bot restarted since your last entry).")
        return
    ids, when = entry
    if dt.datetime.now() - when > UNDO_WINDOW:
        await update.message.reply_text("That entry is more than 15 minutes old — please edit it from the web dashboard instead.")
        return
    removed = 0
    for txn_id in ids:
        try:
            r = client.delete(f"/api/transactions/{txn_id}")
            if r.status_code == 200:
                removed += 1
        except httpx.HTTPError:
            pass
    del _last_txns[user_id]
    await update.message.reply_text(f"🗑️ Removed {removed} entr{'y' if removed == 1 else 'ies'}.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _authorized(user_id):
        await update.message.reply_text("This bot is private. Send /whoami and ask the family admin to add your ID.")
        return

    text = update.message.text
    username = update.effective_user.username or str(user_id)

    try:
        resp = client.post("/api/agent/log", json={
            "text": text,
            "source": "telegram",
            "created_by": username,
        })
    except httpx.HTTPError:
        await update.message.reply_text("Couldn't reach the budget API — please try again shortly.")
        return

    if resp.status_code == 422:
        detail = resp.json().get("detail", "Couldn't understand that.")
        await update.message.reply_text(f"❓ {detail}")
        return
    if resp.status_code != 200:
        log.error("API error %s: %s", resp.status_code, resp.text)
        await update.message.reply_text("Something went wrong saving that — please try again.")
        return

    data = resp.json()
    ids = [t["id"] for t in data["transactions"]]
    _last_txns[user_id] = (ids, dt.datetime.now())
    await update.message.reply_text("✅ " + data["reply"] + "\n\n(send /undo within 15 min to remove this)")


def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("categories", list_categories))
    app.add_handler(CommandHandler("undo", undo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Bot starting (polling)… API_BASE=%s", API_BASE)
    if not ALLOWED_USER_IDS:
        log.warning("ALLOWED_TELEGRAM_USER_IDS is empty — nobody can use the bot yet. "
                     "Have each family member DM the bot /whoami and add their IDs.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
