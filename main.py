import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = ZoneInfo("Africa/Lagos")
DB_NAME = "xeno_agent.db"


def connect_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            reminder TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def now():
    return datetime.now(TIMEZONE)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xeno Agent is live 🧠🔥\n\n"
        "Commands:\n"
        "/newtask\n"
        "/tasks\n"
        "/done\n"
        "/note\n"
        "/notes\n"
        "/remind\n"
        "/today\n"
        "/report"
    )


async def newtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = update.message.text.replace("/newtask", "").strip()

    if not task:
        await update.message.reply_text("Use: /newtask your task")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (chat_id, task, created_at) VALUES (?, ?, ?)",
        (update.message.chat_id, task, now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Task added ✅\n{task}")


async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, task FROM tasks WHERE chat_id=? AND status='pending'",
        (update.message.chat_id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("No tasks.")
        return

    msg = "Tasks:\n\n"
    for i, t in rows:
        msg += f"{i}. {t}\n"

    await update.message.reply_text(msg)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /done id")
        return

    task_id = int(context.args[0])

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET status='done' WHERE id=? AND chat_id=?",
        (task_id, update.message.chat_id)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("Done ✅")


async def note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_text = update.message.text.replace("/note", "").strip()

    if not note_text:
        await update.message.reply_text("Use: /note your note")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (chat_id, note, created_at) VALUES (?, ?, ?)",
        (update.message.chat_id, note_text, now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("Note saved 🧠")


async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, note FROM notes WHERE chat_id=? ORDER BY id DESC LIMIT 10",
        (update.message.chat_id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("No notes.")
        return

    msg = "Notes:\n\n"
    for i, n in rows:
        msg += f"{i}. {n}\n\n"

    await update.message.reply_text(msg)


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.message.text.split(" ", 3)

    if len(parts) < 4:
        await update.message.reply_text("Use: /remind YYYY-MM-DD HH:MM text")
        return

    date_part = parts[1]
    time_part = parts[2]
    text = parts[3]

    try:
        remind_dt = datetime.strptime(
            f"{date_part} {time_part}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=TIMEZONE)
    except:
        await update.message.reply_text("Invalid format")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (chat_id, reminder, remind_at, created_at) VALUES (?, ?, ?, ?)",
        (update.message.chat_id, text, remind_dt.isoformat(), now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text("Reminder set ⏰")


def get_due():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, chat_id, reminder FROM reminders WHERE status='pending' AND remind_at <= ?",
        (now().isoformat(),)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def mark_done(i):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE reminders SET status='sent' WHERE id=?", (i,))
    conn.commit()
    conn.close()


async def check(context: ContextTypes.DEFAULT_TYPE):
    for i, chat_id, text in get_due():
        await context.bot.send_message(chat_id, f"⏰ {text}")
        mark_done(i)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Check /tasks and /notes")


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Agent running fine ✅")


def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newtask", newtask))
    app.add_handler(CommandHandler("tasks", tasks))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("note", note))
    app.add_handler(CommandHandler("notes", notes))
    app.add_handler(CommandHandler("remind", remind))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("report", report))

    app.job_queue.run_repeating(check, interval=60)

    print("Xeno Agent running 🔥")
    app.run_polling()


if __name__ == "__main__":
    main()
