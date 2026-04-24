import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = ZoneInfo("Africa/Lagos")
DB_NAME = "tweets.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            tweet TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_tweet(chat_id, tweet, scheduled_time):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tweets (chat_id, tweet, scheduled_time, created_at)
        VALUES (?, ?, ?, ?)
    """, (chat_id, tweet, scheduled_time, datetime.now(TIMEZONE).isoformat()))
    conn.commit()
    conn.close()


def get_pending_tweets(chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, tweet, scheduled_time
        FROM tweets
        WHERE chat_id = ? AND status = 'pending'
        ORDER BY scheduled_time ASC
    """, (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_tweet(tweet_id, chat_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM tweets
        WHERE id = ? AND chat_id = ?
    """, (tweet_id, chat_id))
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    return deleted


def get_due_tweets():
    now = datetime.now(TIMEZONE).isoformat()
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, chat_id, tweet
        FROM tweets
        WHERE status = 'pending' AND scheduled_time <= ?
    """, (now,))
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_sent(tweet_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE tweets
        SET status = 'sent'
        WHERE id = ?
    """, (tweet_id,))
    conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Yo Xeno 👋\n\n"
        "I’m your X posting assistant.\n\n"
        "Commands:\n"
        "/new - create scheduled tweet\n"
        "/queue - view scheduled tweets\n"
        "/delete ID - delete a tweet\n"
        "/help - show commands"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "How to schedule:\n\n"
        "Use this format:\n"
        "/new 2026-04-24 18:30 Your tweet text here\n\n"
        "Example:\n"
        "/new 2026-04-24 20:00 I’m building my own X scheduler 🔥"
    )


async def new_tweet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    parts = text.split(" ", 3)

    if len(parts) < 4:
        await update.message.reply_text(
            "Wrong format.\n\n"
            "Use:\n"
            "/new YYYY-MM-DD HH:MM Your tweet text\n\n"
            "Example:\n"
            "/new 2026-04-24 20:00 Building in public today 🔥"
        )
        return

    date_part = parts[1]
    time_part = parts[2]
    tweet = parts[3]

    try:
        scheduled_dt = datetime.strptime(
            f"{date_part} {time_part}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=TIMEZONE)
    except ValueError:
        await update.message.reply_text(
            "Invalid date/time format.\n\n"
            "Use this format:\n"
            "2026-04-24 20:00"
        )
        return

    if scheduled_dt <= datetime.now(TIMEZONE):
        await update.message.reply_text("That time has already passed.")
        return

    add_tweet(
        chat_id=update.message.chat_id,
        tweet=tweet,
        scheduled_time=scheduled_dt.isoformat()
    )

    await update.message.reply_text(
        "Tweet scheduled ✅\n\n"
        f"Time: {scheduled_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"Tweet:\n{tweet}"
    )


async def queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rows = get_pending_tweets(update.message.chat_id)

    if not rows:
        await update.message.reply_text("Your queue is empty.")
        return

    message = "Your scheduled tweets:\n\n"

    for row in rows:
        tweet_id, tweet, scheduled_time = row
        dt = datetime.fromisoformat(scheduled_time)
        message += (
            f"ID: {tweet_id}\n"
            f"Time: {dt.strftime('%Y-%m-%d %H:%M')}\n"
            f"Tweet: {tweet}\n\n"
        )

    await update.message.reply_text(message)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /delete ID")
        return

    try:
        tweet_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.")
        return

    deleted = delete_tweet(tweet_id, update.message.chat_id)

    if deleted:
        await update.message.reply_text("Tweet deleted ✅")
    else:
        await update.message.reply_text("Tweet not found.")


async def check_due_tweets(context: ContextTypes.DEFAULT_TYPE):
    rows = get_due_tweets()

    for tweet_id, chat_id, tweet in rows:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "⏰ Time to post on X!\n\n"
                "Copy this tweet:\n\n"
                f"{tweet}\n\n"
                "Open X, paste it, and post."
            )
        )
        mark_sent(tweet_id)


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is missing. Add it in Replit Secrets.")

    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("new", new_tweet))
    app.add_handler(CommandHandler("queue", queue))
    app.add_handler(CommandHandler("delete", delete))

    app.job_queue.run_repeating(check_due_tweets, interval=60, first=10)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
