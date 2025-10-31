import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - Use environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID", "0"))
GF_TELEGRAM_ID = int(os.getenv("GF_TELEGRAM_ID", "0"))

# Data structure
USERS = {
    YOUR_TELEGRAM_ID: {
        "name": "You",
        "partner_id": GF_TELEGRAM_ID,
        "tasks": ["Exercise", "Studies", "No Masturbation"],
        "is_admin": True
    },
    GF_TELEGRAM_ID: {
        "name": "Girlfriend",
        "partner_id": YOUR_TELEGRAM_ID,
        "tasks": ["Physics", "Chemistry", "Maths"],
        "is_admin": False
    }
}

DATA_FILE = "data/tracking_data.json"
REPORT_SENT_FILE = "data/report_sent.json"

# Ensure data directory exists
os.makedirs("data", exist_ok=True)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {
            "status": "online",
            "service": "Telegram Task Tracker Bot",
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response).encode())
    
    def log_message(self, format, *args):
        return  # Disable logs

def start_web_server():
    """Start web server for health checks"""
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"🌐 Web server running on port {port}")
    server.serve_forever()

def load_data():
    """Load tracking data from file"""
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return {}

def save_data(data):
    """Save tracking data to file"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving data: {e}")

def load_report_status():
    """Load report sent status"""
    try:
        if os.path.exists(REPORT_SENT_FILE):
            with open(REPORT_SENT_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error loading report status: {e}")
        return {}

def save_report_status(status):
    """Save report sent status"""
    try:
        with open(REPORT_SENT_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving report status: {e}")

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
    """Handle /start command"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    user_name = USERS[user_id]["name"]
    tasks = USERS[user_id]["tasks"]
    
    message = f"Welcome {user_name}! 🎯\n\n"
    message += "Your daily tasks:\n"
    for i, task in enumerate(tasks, 1):
        message += f"{i}. {task}\n"
    message += "\nCommands:\n"
    message += "/track - Mark today's completed tasks\n"
    message += "/status - Check your today's status\n"
    message += "/report - Get monthly report\n"
    
    if USERS[user_id]["is_admin"]:
        message += "/reset - Reset all data (Admin only)\n"
    
    message += "\n💡 Monthly reports are sent automatically on the last day of each month!"
    
    await update.message.reply_text(message)

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show task selection menu"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    data = load_data()
    today = get_today_key()
    user_key = str(user_id)
    
    # Initialize today's data if not exists
    if today not in data:
        data[today] = {}
    if user_key not in data[today]:
        data[today][user_key] = []
    
    completed_tasks = data[today][user_key]
    tasks = USERS[user_id]["tasks"]
    
    # Create inline keyboard
    keyboard = []
    for i, task in enumerate(tasks):
        status = "✅" if i in completed_tasks else "⬜"
        keyboard.append([InlineKeyboardButton(
            f"{status} {task}", 
            callback_data=f"toggle_{i}"
        )])
    
    keyboard.append([InlineKeyboardButton("✉️ Send to Partner", callback_data="send_update")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = f"📊 Track your tasks for {today}\n\n"
    message += "Tap to toggle completion:"
    
    await update.message.reply_text(message, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in USERS:
        await query.answer("Not authorized!")
        return
    
    await query.answer()
    
    data = load_data()
    today = get_today_key()
    user_key = str(user_id)
    
    # Initialize if needed
    if today not in data:
        data[today] = {}
    if user_key not in data[today]:
        data[today][user_key] = []
    
    if query.data.startswith("toggle_"):
        # Toggle task completion
        task_index = int(query.data.split("_")[1])
        
        if task_index in data[today][user_key]:
            data[today][user_key].remove(task_index)
        else:
            data[today][user_key].append(task_index)
        
        save_data(data)
        
        # Update the message
        completed_tasks = data[today][user_key]
        tasks = USERS[user_id]["tasks"]
        
        keyboard = []
        for i, task in enumerate(tasks):
            status = "✅" if i in completed_tasks else "⬜"
            keyboard.append([InlineKeyboardButton(
                f"{status} {task}", 
                callback_data=f"toggle_{i}"
            )])
        
        keyboard.append([InlineKeyboardButton("✉️ Send to Partner", callback_data="send_update")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"📊 Track your tasks for {today}\n\n"
        message += "Tap to toggle completion:"
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    elif query.data == "send_update":
        # Send update to partner
        partner_id = USERS[user_id]["partner_id"]
        user_name = USERS[user_id]["name"]
        tasks = USERS[user_id]["tasks"]
        completed_tasks = data[today][user_key]
        
        message = f"📬 Update from {user_name} ({today}):\n\n"
        for i, task in enumerate(tasks):
            status = "✅" if i in completed_tasks else "❌"
            message += f"{status} {task}\n"
        
        completion_rate = len(completed_tasks) / len(tasks) * 100
        message += f"\n🎯 Completion: {len(completed_tasks)}/{len(tasks)} ({completion_rate:.0f}%)"
        
        try:
            await context.bot.send_message(chat_id=partner_id, text=message)
            await query.edit_message_text(
                f"✅ Update sent to your partner!\n\n{message}"
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Failed to send update: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show today's status"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    data = load_data()
    today = get_today_key()
    user_key = str(user_id)
    
    tasks = USERS[user_id]["tasks"]
    completed_tasks = data.get(today, {}).get(user_key, [])
    
    message = f"📊 Your status for {today}:\n\n"
    for i, task in enumerate(tasks):
        status = "✅" if i in completed_tasks else "❌"
        message += f"{status} {task}\n"
    
    completion_rate = len(completed_tasks) / len(tasks) * 100 if tasks else 0
    message += f"\n🎯 Completion: {len(completed_tasks)}/{len(tasks)} ({completion_rate:.0f}%)"
    
    await update.message.reply_text(message)

def generate_monthly_report(data, month_key):
    """Generate monthly report text"""
    # Calculate stats for both users
    stats = {}
    for uid in USERS.keys():
        user_key = str(uid)
        total_days = 0
        completed_days = 0
        total_tasks_completed = 0
        total_tasks_possible = 0
        
        for date_key, date_data in data.items():
            if date_key.startswith(month_key):
                if user_key in date_data:
                    total_days += 1
                    tasks_count = len(USERS[uid]["tasks"])
                    completed_count = len(date_data[user_key])
                    total_tasks_completed += completed_count
                    total_tasks_possible += tasks_count
                    
                    if completed_count == tasks_count:
                        completed_days += 1
        
        consistency_rate = (completed_days / total_days * 100) if total_days > 0 else 0
        completion_rate = (total_tasks_completed / total_tasks_possible * 100) if total_tasks_possible > 0 else 0
        
        stats[uid] = {
            "name": USERS[uid]["name"],
            "total_days": total_days,
            "completed_days": completed_days,
            "consistency_rate": consistency_rate,
            "completion_rate": completion_rate,
            "total_tasks_completed": total_tasks_completed,
            "total_tasks_possible": total_tasks_possible
        }
    
    # Generate report
    month_name = datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
    message = f"📈 Monthly Report - {month_name}\n"
    message += "=" * 35 + "\n\n"
    
    for uid, stat in stats.items():
        message += f"👤 {stat['name']}:\n"
        message += f"   📅 Days tracked: {stat['total_days']}\n"
        message += f"   ✅ Perfect days: {stat['completed_days']}\n"
        message += f"   🎯 Consistency: {stat['consistency_rate']:.1f}%\n"
        message += f"   📊 Tasks: {stat['total_tasks_completed']}/{stat['total_tasks_possible']} ({stat['completion_rate']:.1f}%)\n\n"
    
    # Determine winner
    user_ids = list(USERS.keys())
    user_consistency = stats[user_ids[0]]["consistency_rate"]
    partner_consistency = stats[user_ids[1]]["consistency_rate"]
    
    message += "🏆 Winner: "
    if user_consistency > partner_consistency:
        message += f"{stats[user_ids[0]]['name']} is more consistent! 🎉"
    elif partner_consistency > user_consistency:
        message += f"{stats[user_ids[1]]['name']} is more consistent! 🎉"
    else:
        message += "It's a tie! Both are equally consistent! 🤝"
    
    return message

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate monthly report comparing both users"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    data = load_data()
    month_key = get_month_key()
    
    message = generate_monthly_report(data, month_key)
    
    # Send to requesting user
    await update.message.reply_text(message)
    
    # Also send to partner
    partner_id = USERS[user_id]["partner_id"]
    try:
        await context.bot.send_message(chat_id=partner_id, text=message)
    except:
        pass

async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all tracking data (Admin only)"""
    user_id = update.effective_user.id
    
    if user_id not in USERS:
        await update.message.reply_text("Sorry, you're not authorized to use this bot.")
        return
    
    if not USERS[user_id]["is_admin"]:
        await update.message.reply_text("❌ Only the admin can reset data!")
        return
    
    # Create confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Reset All", callback_data="confirm_reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_reset")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ Are you sure you want to reset ALL tracking data?\n\n"
        "This will delete all history and cannot be undone!",
        reply_markup=reply_markup
    )

async def reset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reset confirmation"""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not USERS.get(user_id, {}).get("is_admin"):
        await query.answer("Not authorized!")
        return
    
    await query.answer()
    
    if query.data == "confirm_reset":
        # Delete the data file
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
        if os.path.exists(REPORT_SENT_FILE):
            os.remove(REPORT_SENT_FILE)
        
        await query.edit_message_text("✅ All data has been reset! Starting fresh.")
        
        # Notify partner
        partner_id = USERS[user_id]["partner_id"]
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text="🔄 Your partner has reset all tracking data. Starting fresh!"
            )
        except:
            pass
    
    elif query.data == "cancel_reset":
        await query.edit_message_text("❌ Reset cancelled. Data is safe!")

async def check_and_send_monthly_report(context: ContextTypes.DEFAULT_TYPE):
    """Check if it's the last day of month and send report"""
    if not is_last_day_of_month():
        return
    
    month_key = get_month_key()
    report_status = load_report_status()
    
    # Check if report already sent for this month
    if report_status.get(month_key):
        return
    
    data = load_data()
    if not data:
        return
    
    message = "🎉 End of Month Report!\n\n"
    message += generate_monthly_report(data, month_key)
    
    # Send to both users
    for user_id in USERS.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            logger.error(f"Failed to send report to {user_id}: {e}")
    
    # Mark report as sent
    report_status[month_key] = True
    save_report_status(report_status)

def main():
    """Start the bot with web server"""
    # Validate environment variables
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable is missing!")
        return
    
    if not YOUR_TELEGRAM_ID or not GF_TELEGRAM_ID:
        logger.error("❌ User IDs environment variables are missing!")
        return
    
    # Start web server in a separate thread
    web_thread = threading.Thread(target=start_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Create Application
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
    
    # Start the Bot
    logger.info("🤖 Bot is running on Render...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
