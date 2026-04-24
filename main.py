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
        "Yo Xeno 👋\n\n"
        "I’m your Phase 1 Workforce Agent.\n\n"
        "Commands:\n"
        "/newtask task text\n"
        "/tasks\n"
        "/done task_id\n"
        "/note note text\n"
        "/notes\n"
        "/remind YYYY-MM-DD HH:MM reminder text\n"
        "/today\n"
        "/report\n"
        "/help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Examples:\n\n"
        "/newtask Apply for 3 online jobs\n"
        "/tasks\n"
        "/done 1\n\n"
        "/note Business idea: Telegram workforce agent\n"
        "/notes\n\n"
        "/remind 2026-04-24 21:30 Check my pending tasks\n"
        "/today\n"
        "/report"
    )


async def newtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    task = update.message.text.replace("/newtask", "", 1).strip()

    if not task:
        await update.message.reply_text("Use: /newtask your task here")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (chat_id, task, created_at) VALUES (?, ?, ?)",
        (update.message.chat_id, task, now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Task added ✅\n\n{task}")


async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, task FROM tasks WHERE chat_id=? AND status='pending' ORDER BY id DESC",
        (update.message.chat_id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("You have no pending tasks.")
        return

    msg = "Your pending tasks:\n\n"
    for task_id, task in rows:
        msg += f"{task_id}. {task}\n"

    await update.message.reply_text(msg)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /done task_id")
        return

    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Task ID must be a number.")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE tasks SET status='done' WHERE id=? AND chat_id=?",
        (task_id, update.message.chat_id)
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()

    if updated:
        await update.message.reply_text("Task marked as done ✅")
    else:
        await update.message.reply_text("Task not found.")


async def note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    note_text = update.message.text.replace("/note", "", 1).strip()

    if not note_text:
        await update.message.reply_text("Use: /note your note here")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO notes (chat_id, note, created_at) VALUES (?, ?, ?)",
        (update.message.chat_id, note_text, now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Note saved ✅\n\n{note_text}")


async def notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, note, created_at FROM notes WHERE chat_id=? ORDER BY id DESC LIMIT 10",
        (update.message.chat_id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("You have no saved notes.")
        return

    msg = "Your latest notes:\n\n"
    for note_id, note_text, created_at in rows:
        msg += f"{note_id}. {note_text}\n\n"

    await update.message.reply_text(msg)


async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    parts = text.split(" ", 3)

    if len(parts) < 4:
        await update.message.reply_text(
            "Use:\n/remind YYYY-MM-DD HH:MM reminder text\n\n"
            "Example:\n/remind 2026-04-24 21:30 Check my tasks"
        )
        return

    date_part = parts[1]
    time_part = parts[2]
    reminder_text = parts[3]

    try:
        remind_dt = datetime.strptime(
            f"{date_part} {time_part}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=TIMEZONE)
    except ValueError:
        await update.message.reply_text("Invalid date/time. Use: 2026-04-24 21:30")
        return

    if remind_dt <= now():
        await update.message.reply_text("That reminder time has already passed.")
        return

    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reminders (chat_id, reminder, remind_at, created_at) VALUES (?, ?, ?, ?)",
        (update.message.chat_id, reminder_text, remind_dt.isoformat(), now().isoformat())
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Reminder set ✅\n\n"
        f"Time: {remind_dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"Reminder: {reminder_text}"
    )


def get_due_reminders():
    conn =
