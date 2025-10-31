import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
from threading import Thread
import time

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

# ... (Keep all your existing handler functions: start, track, button_callback, status, generate_monthly_report, report, reset_data, reset_callback, check_and_send_monthly_report)

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
        return
    
    # Start web server in a separate thread
    web_thread = Thread(target=start_web_server)
    web_thread.daemon = True
    web_thread.start()
    
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
    
    # Start the bot
    print("Bot is running on Render...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        close_loop=False
    )

if __name__ == "__main__":
    main()
