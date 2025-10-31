import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from threading import Thread

# Configuration - Use environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID", "0"))
GF_TELEGRAM_ID = int(os.getenv("GF_TELEGRAM_ID", "0"))

# Data structure
USERS = {
    YOUR_TELEGRAM_ID: {
        "name": "Sahith",
        "partner_id": GF_TELEGRAM_ID,
        "tasks": ["Exercise", "Studies", "No Masturbation"],
        "is_admin": True
    },
    GF_TELEGRAM_ID: {
        "name": "Kritika",
        "partner_id": YOUR_TELEGRAM_ID,
        "tasks": ["Physics", "Chemistry", "Maths"],
        "is_admin": False
    }
}

DATA_FILE = "data/tracking_data.json"
REPORT_SENT_FILE = "data/report_sent.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

def load_data():
    """Load tracking data from file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading data: {e}")
        return {}

def save_data(data):
    """Save tracking data to file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_report_status():
    """Load report sent status"""
    try:
        if os.path.exists(REPORT_SENT_FILE):
            with open(REPORT_SENT_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading report status: {e}")
        return {}

def save_report_status(status):
    """Save report sent status"""
    try:
        with open(REPORT_SENT_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"Error saving report status: {e}")

def get_today_key():
    """Get today's date as a string key"""
    return datetime.now().strftime("%Y-%m-%d")

def get_month_key():
    """Get current month as a string key"""
    return datetime.now().strftime("%Y-%m")

def is_last_day_of_month():
    """Check if today is the last day of the month"""
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    return today.month != tomorrow.month

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    user_name = USERS[user_id]["name"]
    welcome_message = f"""
👋 Welcome {user_name}!

This bot helps you and your partner track daily tasks.

📋 Available Commands:
/track - Mark today's tasks as complete
/status - View your completion status
/report - View monthly report
/reset - Reset all data (admin only)

Let's stay accountable together! 💪
"""
    await update.message.reply_text(welcome_message)

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tasks for today with buttons to mark complete"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    user_name = USERS[user_id]["name"]
    tasks = USERS[user_id]["tasks"]
    today = get_today_key()
    
    # Load existing data
    data = load_data()
    user_data = data.get(str(user_id), {})
    today_data = user_data.get(today, {})
    
    # Create inline keyboard
    keyboard = []
    for task in tasks:
        status = "✅" if today_data.get(task, False) else "⬜"
        keyboard.append([InlineKeyboardButton(
            f"{status} {task}", 
            callback_data=f"toggle_{task}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    completed = sum(1 for task in tasks if today_data.get(task, False))
    total = len(tasks)
    
    message = f"""
📅 *{user_name}'s Tasks for Today*
_{today}_

Progress: {completed}/{total} tasks completed

Click on a task to toggle completion:
"""
    
    await update.message.reply_text(
        message, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in USERS:
        await query.answer("❌ Unauthorized")
        return
    
    await query.answer()
    
    # Parse callback data
    if not query.data.startswith("toggle_"):
        return
    
    task_name = query.data.replace("toggle_", "")
    tasks = USERS[user_id]["tasks"]
    
    if task_name not in tasks:
        await query.edit_message_text("❌ Invalid task")
        return
    
    # Toggle task completion
    today = get_today_key()
    data = load_data()
    
    if str(user_id) not in data:
        data[str(user_id)] = {}
    if today not in data[str(user_id)]:
        data[str(user_id)][today] = {}
    
    current_status = data[str(user_id)][today].get(task_name, False)
    data[str(user_id)][today][task_name] = not current_status
    
    save_data(data)
    
    # Update keyboard
    today_data = data[str(user_id)][today]
    keyboard = []
    for task in tasks:
        status = "✅" if today_data.get(task, False) else "⬜"
        keyboard.append([InlineKeyboardButton(
            f"{status} {task}", 
            callback_data=f"toggle_{task}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    completed = sum(1 for task in tasks if today_data.get(task, False))
    total = len(tasks)
    user_name = USERS[user_id]["name"]
    
    message = f"""
📅 *{user_name}'s Tasks for Today*
_{today}_

Progress: {completed}/{total} tasks completed

Click on a task to toggle completion:
"""
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Notify partner if all tasks completed
    if completed == total:
        partner_id = USERS[user_id]["partner_id"]
        notification = f"🎉 {user_name} has completed all tasks for today! Great job! 💪"
        try:
            await context.bot.send_message(chat_id=partner_id, text=notification)
        except Exception as e:
            print(f"Error sending notification: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show completion status for both users"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    data = load_data()
    today = get_today_key()
    
    status_message = f"📊 *Status Report for {today}*\n\n"
    
    for uid, user_info in USERS.items():
        user_name = user_info["name"]
        tasks = user_info["tasks"]
        user_data = data.get(str(uid), {})
        today_data = user_data.get(today, {})
        
        completed = sum(1 for task in tasks if today_data.get(task, False))
        total = len(tasks)
        percentage = (completed / total * 100) if total > 0 else 0
        
        status_message += f"*{user_name}*\n"
        status_message += f"Progress: {completed}/{total} ({percentage:.0f}%)\n"
        
        for task in tasks:
            status = "✅" if today_data.get(task, False) else "❌"
            status_message += f"  {status} {task}\n"
        
        status_message += "\n"
    
    await update.message.reply_text(status_message, parse_mode='Markdown')

def generate_monthly_report(data, month_key):
    """Generate monthly report for both users"""
    report = f"📊 *Monthly Report - {month_key}*\n\n"
    
    for uid, user_info in USERS.items():
        user_name = user_info["name"]
        tasks = user_info["tasks"]
        user_data = data.get(str(uid), {})
        
        # Filter dates for this month
        month_dates = [date for date in user_data.keys() if date.startswith(month_key)]
        
        if not month_dates:
            report += f"*{user_name}*: No data for this month\n\n"
            continue
        
        # Calculate statistics
        total_days = len(month_dates)
        task_completion = {}
        
        for task in tasks:
            completed_days = sum(1 for date in month_dates if user_data[date].get(task, False))
            task_completion[task] = (completed_days / total_days * 100) if total_days > 0 else 0
        
        # Calculate overall completion
        all_completions = [user_data[date].get(task, False) for date in month_dates for task in tasks]
        overall_percentage = (sum(all_completions) / len(all_completions) * 100) if all_completions else 0
        
        report += f"*{user_name}*\n"
        report += f"Days tracked: {total_days}\n"
        report += f"Overall completion: {overall_percentage:.1f}%\n\n"
        
        for task, percentage in task_completion.items():
            report += f"  • {task}: {percentage:.1f}%\n"
        
        report += "\n"
    
    return report

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly report"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    data = load_data()
    month_key = get_month_key()
    
    report_text = generate_monthly_report(data, month_key)
    await update.message.reply_text(report_text, parse_mode='Markdown')

async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all data (admin only)"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
    
    if not USERS[user_id].get("is_admin", False):
        await update.message.reply_text("❌ Only admins can reset data.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Reset All", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ *Warning*\n\nThis will delete ALL tracking data for both users. This action cannot be undone.\n\nAre you sure?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reset confirmation"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in USERS or not USERS[user_id].get("is_admin", False):
        await query.answer("❌ Unauthorized")
        return
    
    await query.answer()
    
    if query.data == "confirm_reset":
        # Reset all data
        save_data({})
        save_report_status({})
        await query.edit_message_text("✅ All data has been reset successfully.")
    else:
        await query.edit_message_text("❌ Reset cancelled.")

async def check_and_send_monthly_report(context: ContextTypes.DEFAULT_TYPE):
    """Check if it's the last day of month and send report"""
    if not is_last_day_of_month():
        return
    
    month_key = get_month_key()
    report_status = load_report_status()
    
    # Check if report already sent for this month
    if report_status.get(month_key, False):
        return
    
    # Generate and send report to both users
    data = load_data()
    report_text = generate_monthly_report(data, month_key)
    report_text = "🎯 *End of Month Report*\n\n" + report_text
    
    for uid in USERS.keys():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=report_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error sending report to {uid}: {e}")
    
    # Mark report as sent
    report_status[month_key] = True
    save_report_status(report_status)

def start_web_server():
    """Start a simple web server for Render health checks"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        
        def log_message(self, format, *args):
            return  # Disable logging
    
    server = HTTPServer(('0.0.0.0', int(os.getenv('PORT', '8080'))), HealthHandler)
    server.serve_forever()

def main():
    """Start the bot with web server"""
    # Validate environment variables
    if not BOT_TOKEN or not YOUR_TELEGRAM_ID or not GF_TELEGRAM_ID:
        print("Error: Missing required environment variables!")
        print(f"BOT_TOKEN: {'Set' if BOT_TOKEN else 'Missing'}")
        print(f"YOUR_TELEGRAM_ID: {'Set' if YOUR_TELEGRAM_ID else 'Missing'}")
        print(f"GF_TELEGRAM_ID: {'Set' if GF_TELEGRAM_ID else 'Missing'}")
        return
    
    # Start web server in a separate thread
    web_thread = Thread(target=start_web_server)
    web_thread.daemon = True
    web_thread.start()
    print(f"Web server started on port {os.getenv('PORT', '8080')}")
    
    # Create Telegram bot application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("track", track))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("reset", reset_data))
    application.add_handler(CallbackQueryHandler(reset_callback, pattern="^(confirm_reset|cancel_reset)$"))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Schedule monthly report check (runs every hour)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(check_and_send_monthly_report, interval=3600, first=10)
        print("Monthly report checker scheduled")
    
    # Start the bot
    print("Bot is running on Render...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == "__main__":
    main()
