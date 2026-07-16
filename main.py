import telebot
from telebot.apihelper import ApiTelegramException
import sqlite3
import time
import threading

# ⚠️ Yahan apna real bot token paste karein
API_TOKEN = "8702563696:AAHb9hNZ4Q8Y5lnBOrr7AbooyLicmczV1bg"

# ⚠️ Apne Free Group aur Private Channel ki IDs yahan dalein (Must be integers, e.g. -100...)
FREE_GROUP_ID = -4477244119  
PRIVATE_CHANNEL_ID = -3870933647  

bot = telebot.TeleBot(API_TOKEN)


# 🗄️ Database Setup (Taqe purane aur naye sabhi users ka record save rahe aur check hota rahe)
def init_db():
    conn = sqlite3.connect("requests_tracker.db")
    cursor = conn.cursor()
    # Table to keep track of ALL users who requested access
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_requests (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

init_db()


# 🔍 Live check karne ka function ke user abhi free group mein hai ya nahi
def is_user_in_free_group(user_id):
    try:
        member = bot.get_chat_member(FREE_GROUP_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except ApiTelegramException:
        return False


# 📥 Jab bhi koi NAYI request aaye, usay database mein save karein aur instantly check karein
@bot.chat_join_request_handler()
def handle_incoming_request(update):
    if update.chat.id == PRIVATE_CHANNEL_ID:
        user_id = update.from_user.id
        first_name = update.from_user.first_name
        
        # Database mein entry dalein (New/Old ka farq hamesha ke liye khatam)
        conn = sqlite3.connect("requests_tracker.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO pending_requests (user_id, first_name, status) VALUES (?, ?, 'pending')", (user_id, first_name))
        conn.commit()
        conn.close()
        
        print(f"📥 Request Saved to Database: {first_name} ({user_id})")
        
        # Instant Check: Agar abhi free group mein nahi hai to foran approve kar do
        if not is_user_in_free_group(user_id):
            approve_user_access(user_id, first_name)
        else:
            print(f"❌ Kept Pending (Active in Free Group): {first_name}")


# 🔓 User ko approve karne aur DB update karne ka function
def approve_user_access(user_id, first_name):
    try:
        bot.approve_chat_join_request(PRIVATE_CHANNEL_ID, user_id)
        print(f"✅ Approved: {first_name} ({user_id}) is not in Free Group.")
        
        # Database mein update kar dein ke yeh user approve ho chuka hai
        conn = sqlite3.connect("requests_tracker.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        # User ko inbox mein welcome message bhej dein
        bot.send_message(
            user_id,
            f"🎉 **Welcome {first_name} to Gold Expert FX | XAUUSD Signals!**\n\n"
            f"Aapki join request accept kar li gayi hai kyun ki aap hamari free community ke member nahi hain. Enjoy VIP signals! 📈"
        )
    except ApiTelegramException as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            conn = sqlite3.connect("requests_tracker.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
        else:
            print(f"Could not approve {first_name}: {e}")


# 🔄 BACKGROUND SCHEDULER: Har 30 seconds baad ALL pending (old & new) requests ko scan karega
def scan_all_pending_requests():
    while True:
        try:
            conn = sqlite3.connect("requests_tracker.db")
            cursor = conn.cursor()
            # Database se tamam pending users ko nikalein (Purane aur naye sab)
            cursor.execute("SELECT user_id, first_name FROM pending_requests WHERE status = 'pending'")
            all_pending = cursor.fetchall()
            conn.close()
            
            if all_pending:
                print(f"🔄 Scanning {len(all_pending)} pending requests (old & new)...")
                
            for user_id, first_name in all_pending:
                # Agar user ab free group mein nahi hai (ya left kar chuka hai)
                if not is_user_in_free_group(user_id):
                    print(f"⚡ Live Scan Match! {first_name} is no longer in free group. Approving...")
                    approve_user_access(user_id, first_name)
                else:
                    # Agar abhi bhi group mein baitha hua hai to pending hi rahega
                    pass
                    
        except Exception as e:
            print(f"Error in background scanner: {e}")
            
        time.sleep(30)  # Har 30 seconds baad database check karega


# Background thread start karein scheduler chalane ke liye
threading.Thread(target=scan_all_pending_requests, daemon=True).start()


# 🏃 [FEATURE: DELETE NOTIFICATIONS] Free group ke notifications delete karne ka system
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def delete_system_messages(message):
    try:
        # Jaise hi koi join kare ya leave kare, bot uska message instantly delete karega
        bot.delete_message(message.chat.id, message.message_id)
        print("Silent Clean: Deleted a join/leave system message.")
    except Exception as e:
        print(f"Error deleting system message: {e}")


if __name__ == "__main__":
    print("Gold Expert Master Auto-Scan & Cleaner Bot is running...")
    bot.infinity_polling(timeout=10)
                        
